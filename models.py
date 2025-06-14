from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

class AffiliateLink(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='affiliate_links')
    original_link = models.URLField()
    converted_link = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    click_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    def __str__(self):
        return f"Link by {self.user.username} - {self.created_at.strftime('%Y-%m-%d')}"

class Transaction(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    affiliate_link = models.ForeignKey(AffiliateLink, on_delete=models.SET_NULL, null=True, related_name='transactions')
    product_name = models.CharField(max_length=255, blank=True, null=True)
    product_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    estimated_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    cashback_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Calculate cashback as 5% of estimated commission if not already set
        if self.estimated_commission and self.cashback_amount == 0:
            self.cashback_amount = self.estimated_commission * Decimal('0.05')
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Transaction {self.id} - {self.user.username} - ₱{self.cashback_amount}"

class Withdrawal(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('gcash', 'GCash'),
        ('paymaya', 'PayMaya'),
        ('bank', 'Bank Transfer'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdrawals')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES)
    payment_details = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Withdrawal {self.id} - {self.user.username} - ₱{self.amount}"
        
    def approve(self):
        self.status = 'approved'
        self.processed_at = timezone.now()
        self.save()
        
        # Deduct the amount from user's balance
        profile = self.user.profile
        profile.balance -= self.amount
        profile.save()
