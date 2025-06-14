from django import forms
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile, AffiliateLink, Transaction, Withdrawal

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'})
    )
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'})
    )
    
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create a password'})
    )
    
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm your password'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone_number']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your phone number'})
        }

class AffiliateLinkForm(forms.ModelForm):
    class Meta:
        model = AffiliateLink
        fields = ['original_link']
        widgets = {
            'original_link': forms.URLInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Paste your Shopee product link here'
            })
        }
        labels = {
            'original_link': 'Shopee Product Link'
        }

class ProductInfoForm(forms.Form):
    product_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter product name'
        })
    )
    product_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter product price',
            'min': '0.01',
            'step': '0.01'
        })
    )

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['product_name', 'product_price']
        widgets = {
            'product_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product name'
            }),
            'product_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product price',
                'min': '0.01',
                'step': '0.01'
            })
        }

class WithdrawalForm(forms.ModelForm):
    class Meta:
        model = Withdrawal
        fields = ['amount', 'payment_method', 'payment_details']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '100',
                'step': '0.01'
            }),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'payment_details': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your payment details (e.g., GCash number, PayMaya account, bank account)'
            })
        }
        help_texts = {
            'payment_details': 'For GCash/PayMaya: Enter your registered mobile number. For bank transfers: Enter bank name, account name, and account number.'
        }
        
    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount < 100:
            raise forms.ValidationError('Minimum withdrawal amount is ₱100.')
        return amount 