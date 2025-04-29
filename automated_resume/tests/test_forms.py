from django.test import TestCase
from automated_resume.forms import *
from automated_resume.models import CustomUser, Profile
from django.core.files.uploadedfile import SimpleUploadedFile
from faker import Faker

faker = Faker()

class CustomUserCreationFormTest(TestCase):
    def test_valid_form(self):
        """Test CustomUserCreationForm with valid data"""
        fake_resume = SimpleUploadedFile("resume.pdf", b"Dummy Content")
        form_data = {
            "username": faker.user_name(),
            "email": faker.email(),
            "phone": "1234567890",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        form_files = {"resume": fake_resume}
        form = CustomUserCreationForm(data=form_data, files=form_files)
        self.assertTrue(form.is_valid())
        
    def test_invalid_phone(self):
        """Test form with invalid phone number"""
        form_data = {
            "username": faker.user_name(),
            "email": faker.email(),
            "phone": "abc123",  # Invalid phone
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)
    
    def test_mismatched_passwords(self):
        """Test form with mismatched passwords"""
        form_data = {
            "username": faker.user_name(),
            "email": faker.email(),
            "phone": "1234567890",
            "password1": "StrongPass123!",
            "password2": "WrongPass456!",
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)
        
class AdminLoginFormTest(TestCase):
    def test_valid_form(self):
        """Test AdminLoginForm with valid data"""
        form_data = {
            "email": faker.email(),
            "password": "StrongPass123!",
        }
        form = AdminLoginForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_email(self):
        """Test AdminLoginForm with invalid email"""
        form_data = {
            "email": "invalid-email",  # Invalid email format
            "password": "StrongPass123!",
        }
        form = AdminLoginForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_missing_password(self):
        """Test AdminLoginForm with missing password"""
        form_data = {
            "email": faker.email(),
            "password": "",
        }
        form = AdminLoginForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)


class CustomSetPasswordFormTest(TestCase):
    def setUp(self):
        """Create a test user for password reset"""
        self.user = CustomUser.objects.create_user(
            username=faker.user_name(),
            email=faker.email(),
            password="OldPassword123!"
        )

    def test_valid_passwords(self):
        """Test CustomSetPasswordForm with matching passwords"""
        form_data = {
            "new_password1": "StrongPass123!",
            "new_password2": "StrongPass123!",
        }
        form = CustomSetPasswordForm(user=self.user, data=form_data)
        self.assertTrue(form.is_valid())

    def test_mismatched_passwords(self):
        """Test CustomSetPasswordForm with mismatched passwords"""
        form_data = {
            "new_password1": "StrongPass123!",
            "new_password2": "WrongPass456!",
        }
        form = CustomSetPasswordForm(user=self.user, data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("new_password2", form.errors)
        
        
class EmailVerificationTest(TestCase):
    def test_valid_email(self):
        """Test EmailVerification form with valid email"""
        form_data = {
            "email": faker.email(),
            "otp": "123456",
        }
        form = EmailVerification(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_email(self):
        """Test EmailVerification form with invalid email format"""
        form_data = {
            "email": "invalid-email",
            "otp": "123456",
        }
        form = EmailVerification(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_empty_otp(self):
        """Test EmailVerification form with empty OTP (allowed)"""
        form_data = {
            "email": faker.email(),
            "otp": "",
        }
        form = EmailVerification(data=form_data)
        self.assertTrue(form.is_valid())  # OTP is optional