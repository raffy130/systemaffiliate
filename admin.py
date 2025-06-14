from django.contrib import admin
from .models import UserProfile, AffiliateLink, Transaction, Withdrawal

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'balance')
    search_fields = ('user__username', 'user__email', 'phone_number')

@admin.register(AffiliateLink)
class AffiliateLinkAdmin(admin.ModelAdmin):
    list_display = ('user', 'original_link', 'converted_link', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'original_link', 'converted_link')
    date_hierarchy = 'created_at'

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'product_name', 'product_price', 'estimated_commission', 
                   'cashback_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'product_name')
    date_hierarchy = 'created_at'
    
    actions = ['approve_transactions', 'reject_transactions']
    
    def approve_transactions(self, request, queryset):
        for transaction in queryset.filter(status='pending'):
            # Update transaction status
            transaction.status = 'approved'
            transaction.save()
            
            # Add cashback to user's balance
            profile = transaction.user.profile
            profile.balance += transaction.cashback_amount
            profile.save()
        
        self.message_user(request, f"{queryset.filter(status='pending').count()} transactions have been approved.")
    approve_transactions.short_description = "Approve selected transactions"
    
    def reject_transactions(self, request, queryset):
        queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f"{queryset.filter(status='pending').count()} transactions have been rejected.")
    reject_transactions.short_description = "Reject selected transactions"

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'payment_method', 'payment_details', 'status', 
                   'requested_at', 'processed_at')
    list_filter = ('status', 'payment_method', 'requested_at')
    search_fields = ('user__username', 'payment_details')
    date_hierarchy = 'requested_at'
    
    actions = ['approve_withdrawals', 'reject_withdrawals']
    
    def approve_withdrawals(self, request, queryset):
        for withdrawal in queryset.filter(status='pending'):
            withdrawal.approve()
        
        self.message_user(request, f"{queryset.filter(status='pending').count()} withdrawals have been approved.")
    approve_withdrawals.short_description = "Approve selected withdrawals"
    
    def reject_withdrawals(self, request, queryset):
        queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f"{queryset.filter(status='pending').count()} withdrawals have been rejected.")
    reject_withdrawals.short_description = "Reject selected withdrawals"
