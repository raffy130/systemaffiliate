from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
import re
import uuid
from django.urls import reverse
from django.contrib.admin.views.decorators import staff_member_required

from .models import UserProfile, AffiliateLink, Transaction, Withdrawal
from .forms import (
    CustomUserCreationForm,
    UserProfileForm, 
    AffiliateLinkForm, 
    TransactionForm, 
    WithdrawalForm,
    ProductInfoForm
)

def home(request):
    """Home page view"""
    return render(request, 'shoppelink/home.html')

def register(request):
    """User registration view"""
    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST)
        profile_form = UserProfileForm(request.POST)
        
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            
            # Log the user in
            username = user_form.cleaned_data.get('username')
            raw_password = user_form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            
            if user:
                login(request, user)
                messages.success(request, f"Account created for {username}! You are now logged in.")
                return redirect('dashboard')
            else:
                # This should rarely happen, but handle the case if authentication fails
                messages.error(request, "Account created but login failed. Please log in manually.")
                return redirect('login')
        else:
            # Form validation failed, errors will be displayed in the template
            for field, errors in user_form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            
            for field, errors in profile_form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        user_form = CustomUserCreationForm()
        profile_form = UserProfileForm()
    
    return render(request, 'shoppelink/register.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

@login_required
def dashboard(request):
    """User dashboard view"""
    user = request.user
    
    # Get user's balance
    profile = UserProfile.objects.get(user=user)
    
    # Get recent transactions
    recent_transactions = Transaction.objects.filter(user=user).order_by('-created_at')[:5]
    
    # Get pending withdrawals
    pending_withdrawals = Withdrawal.objects.filter(user=user, status='pending').order_by('-requested_at')
    
    # Get transaction stats
    approved_transactions = Transaction.objects.filter(user=user, status='approved')
    pending_transactions = Transaction.objects.filter(user=user, status='pending')
    total_cashback = approved_transactions.aggregate(Sum('cashback_amount'))['cashback_amount__sum'] or 0
    
    # Get link count
    link_count = AffiliateLink.objects.filter(user=user).count()
    
    # Get top products (based on cashback amount)
    top_products = Transaction.objects.filter(user=user, status='approved').order_by('-cashback_amount')[:5]
    
    context = {
        'profile': profile,
        'recent_transactions': recent_transactions,
        'pending_withdrawals': pending_withdrawals,
        'total_cashback': total_cashback,
        'transaction_count': approved_transactions.count(),
        'pending_count': pending_transactions.count(),
        'total_orders': Transaction.objects.filter(user=user).count(),
        'link_count': link_count,
        'top_products': top_products,
        'available_balance': profile.balance,
    }
    
    return render(request, 'shoppelink/dashboard.html', context)

@login_required
def link_converter(request):
    """Link converter view"""
    if request.method == 'POST':
        form = AffiliateLinkForm(request.POST)
        
        if form.is_valid():
            original_link = form.cleaned_data['original_link']
            
            # Check if it's a valid Shopee link
            if not ('shopee.ph' in original_link or 'shopee.com.ph' in original_link):
                messages.error(request, "Please enter a valid Shopee link.")
                return render(request, 'shoppelink/link_converter.html', {'form': form})
            
            # Save the affiliate link object to get an ID
            affiliate_link = AffiliateLink(
                user=request.user,
                original_link=original_link,
                converted_link=''  # Will be updated shortly
            )
            affiliate_link.save()

            # Generate the tracking link, which will be the converted_link
            # The domain should be your actual domain
            tracking_link = request.build_absolute_uri(
                reverse('track_link_click', args=[affiliate_link.id])
            )
            
            # Update the affiliate link with the tracking link
            affiliate_link.converted_link = tracking_link
            affiliate_link.save()
            
            # Get product info for cashback estimation
            product_info_form = ProductInfoForm()
            
            context = {
                'form': form,
                'affiliate_link': affiliate_link,
                'product_info_form': product_info_form
            }
            
            return render(request, 'shoppelink/link_converter.html', context)
    else:
        form = AffiliateLinkForm()
    
    return render(request, 'shoppelink/link_converter.html', {'form': form})

@login_required
def submit_transaction(request, link_id):
    """Submit a transaction after checkout"""
    affiliate_link = get_object_or_404(AffiliateLink, id=link_id, user=request.user)
    
    if request.method == 'POST':
        form = ProductInfoForm(request.POST)
        
        if form.is_valid():
            product_name = form.cleaned_data['product_name']
            product_price = form.cleaned_data['product_price']
            
            # Calculate estimated commission (placeholder - you'll need your actual commission rate)
            estimated_commission = calculate_estimated_commission(product_price)
            
            # Calculate cashback (5% of commission)
            cashback_amount = estimated_commission * Decimal('0.05')
            
            # Create transaction
            transaction = Transaction(
                user=request.user,
                affiliate_link=affiliate_link,
                product_name=product_name,
                product_price=product_price,
                estimated_commission=estimated_commission,
                cashback_amount=cashback_amount,
                status='pending'
            )
            transaction.save()
            
            messages.success(request, "Transaction submitted successfully! It will be reviewed shortly.")
            return redirect('transaction_detail', transaction_id=transaction.id)
    else:
        form = ProductInfoForm()
    
    return render(request, 'shoppelink/submit_transaction.html', {
        'form': form,
        'affiliate_link': affiliate_link
    })

@login_required
def transaction_detail(request, transaction_id):
    """View transaction details"""
    transaction = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    
    return render(request, 'shoppelink/transaction_detail.html', {
        'transaction': transaction
    })

@login_required
def transactions(request):
    """View all user transactions"""
    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'shoppelink/transactions.html', {
        'transactions': transactions
    })

@login_required
def request_withdrawal(request):
    """Request a withdrawal"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    # Check if user has enough balance
    if user_profile.balance < 100:
        messages.error(request, "You need at least ₱100 to request a withdrawal.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = WithdrawalForm(request.POST)
        
        if form.is_valid():
            amount = form.cleaned_data['amount']
            
            # Check if withdrawal amount is valid
            if amount > user_profile.balance:
                messages.error(request, "You cannot withdraw more than your available balance.")
                return render(request, 'shoppelink/request_withdrawal.html', {'form': form})
            
            if amount < 100:
                messages.error(request, "Minimum withdrawal amount is ₱100.")
                return render(request, 'shoppelink/request_withdrawal.html', {'form': form})
            
            # Create withdrawal request
            withdrawal = Withdrawal(
                user=request.user,
                amount=amount,
                payment_method=form.cleaned_data['payment_method'],
                payment_details=form.cleaned_data['payment_details'],
                status='pending'
            )
            withdrawal.save()
            
            messages.success(request, "Withdrawal request submitted successfully!")
            return redirect('dashboard')
    else:
        form = WithdrawalForm(initial={'amount': user_profile.balance})
    
    return render(request, 'shoppelink/request_withdrawal.html', {
        'form': form,
        'balance': user_profile.balance
    })

@login_required
def withdrawals(request):
    """View all user withdrawals"""
    withdrawals = Withdrawal.objects.filter(user=request.user).order_by('-requested_at')
    
    # Calculate total withdrawn amount
    total_withdrawn = Withdrawal.objects.filter(
        user=request.user, 
        status='approved'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    return render(request, 'shoppelink/withdrawals.html', {
        'withdrawals': withdrawals,
        'total_withdrawn': total_withdrawn
    })

@staff_member_required
def admin_dashboard(request):
    """Admin dashboard with overall stats."""
    
    # Import User model at the function level to avoid circular imports
    from django.contrib.auth.models import User
    
    # Overall stats
    total_users = User.objects.count()
    total_links = AffiliateLink.objects.count()
    total_transactions = Transaction.objects.count()
    total_cashback = Transaction.objects.filter(status='approved').aggregate(Sum('cashback_amount'))['cashback_amount__sum'] or 0
    
    # Recent activity
    recent_transactions = Transaction.objects.order_by('-created_at')[:10]
    recent_users = User.objects.order_by('-date_joined')[:5]
    
    # Pending withdrawals
    pending_withdrawals = Withdrawal.objects.filter(status='pending').order_by('-requested_at')

    context = {
        'total_users': total_users,
        'total_links': total_links,
        'total_transactions': total_transactions,
        'total_cashback': total_cashback,
        'recent_transactions': recent_transactions,
        'recent_users': recent_users,
        'pending_withdrawals': pending_withdrawals,
    }
    
    return render(request, 'shoppelink/admin_dashboard.html', context)

@login_required
def delete_transaction(request, transaction_id):
    """Deletes a transaction."""
    transaction = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    
    if request.method == 'POST':
        # If the transaction was approved, deduct the cashback from the user's balance
        if transaction.status == 'approved':
            profile = request.user.profile
            profile.balance -= transaction.cashback_amount
            profile.save()
            messages.success(request, f"Transaction #{transaction.id} deleted and ₱{transaction.cashback_amount} deducted from your balance.")
        else:
            messages.success(request, f"Transaction #{transaction.id} deleted.")
        
        transaction.delete()
    
    return redirect('transactions')

@login_required
def affiliate_links(request):
    """Displays all affiliate links generated by the user."""
    links = AffiliateLink.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'links': links
    }
    return render(request, 'shoppelink/affiliate_links.html', context)

# Helper functions
def convert_to_affiliate_link(original_link, username):
    """Convert a Shopee link to an affiliate link"""
    # This is a placeholder - you'll need to implement your actual affiliate link generation logic
    # For example, you might add your affiliate ID and a tracking parameter for the user
    
    # Remove any existing affiliate parameters
    clean_link = re.sub(r'(\?|&)affiliate=.*?(&|$)', r'\1', original_link)
    
    # Add your affiliate ID and user tracking
    if '?' in clean_link:
        affiliate_link = f"{clean_link}&affiliate=YOUR_AFFILIATE_ID&subid={username}"
    else:
        affiliate_link = f"{clean_link}?affiliate=YOUR_AFFILIATE_ID&subid={username}"
    
    return affiliate_link

def calculate_estimated_commission(product_price):
    """Calculate estimated commission based on product price (placeholder)."""
    # Replace with your actual commission calculation logic
    # For example, a flat 10% commission rate
    commission_rate = Decimal('0.10')
    return product_price * commission_rate

def track_link_click(request, link_id):
    """Tracks a click on an affiliate link and redirects to the original URL."""
    affiliate_link = get_object_or_404(AffiliateLink, id=link_id)
    
    # Increment the click count
    affiliate_link.click_count += 1
    affiliate_link.save(update_fields=['click_count'])
    
    # Redirect to the original Shopee link
    return redirect(affiliate_link.original_link)
