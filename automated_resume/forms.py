# forms.py
from django import forms
from django.forms import ModelForm
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.forms import UserCreationForm
from django.apps import apps
from .models import *


def validate_phone(value):
    if not value.isdigit():
        raise ValidationError('Phone number must contain only digits.')
    if len(value) != 10:
        raise ValidationError('Phone number must be exactly 10 digits.')

class CustomUserCreationForm(UserCreationForm):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('N', 'Prefer not to say')
    ]
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    gender = forms.ChoiceField(choices=GENDER_CHOICES, required=True)
    email = forms.EmailField(required=True)
    phone = forms.CharField(
        max_length=10,
        validators=[validate_phone],
        error_messages={'required': 'Phone number is required.'}
    )
    resume = forms.FileField()

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'gender', 'email', 'phone', 'resume', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)  # Save user without committing yet
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.gender = self.cleaned_data['gender']
        if commit:
            user.save()  # Save user instance first
            Profile.objects.create(user=user, phone=self.cleaned_data['phone'], resume=self.cleaned_data['resume'])  # Create Profile
        return user


class AdminDashboardForm(forms.ModelForm):
    class Meta:
        model = AdminDashboardConfig
        fields = ['name', 'selected_model', 'selected_fields', 'chart_type']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get all model names dynamically
        all_models = apps.get_models()
        model_choices = [(model.__name__, model.__name__) for model in all_models]
        self.fields['selected_model'].widget = forms.Select(choices=model_choices)

        # Fields will be populated dynamically based on the selected model
        self.fields['selected_fields'].widget = forms.SelectMultiple()
        
    
class AdminLoginForm(forms.Form):
    email = forms.EmailField(label='Email', max_length=100, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'class': 'form-control'}))


class ResetPasswordDone(forms.Form):
    pass


class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="Enter new password",
        widget=forms.PasswordInput,
        strip=False,
        help_text="Enter your new password",
    )
    new_password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput,
        strip=False,
        help_text="Enter the same password as before, for verification",
    )


class EmailVerification(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'}))
    otp = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter OTP'}))