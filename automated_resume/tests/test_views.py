from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from automated_resume.models import Profile, ResultData, QuesModel
from django.core.files.uploadedfile import SimpleUploadedFile
import json

User = get_user_model()

class ViewsTestCase(TestCase):
    def setUp(self):
        """Setup test client, user, and necessary data"""
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.profile = Profile.objects.create(user=self.user, phone="1234567890", ats_score=75, ats_remarks="Good")

    def test_landing_page(self):
        """Test landing page loads correctly"""
        response = self.client.get(reverse("landing_page"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "automated_resume/landing_page.html")

    def test_logout_view(self):
        """Test logout functionality"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("logout"))
        self.assertRedirects(response, reverse("landing_page"))

    def test_sign_up_valid(self):
        """Test user signup with valid data"""
        resume = SimpleUploadedFile("resume.pdf", b"Test Resume Content", content_type="application/pdf")
        response = self.client.post(reverse("sign_up"), {
            "username": "newuser",
            "email": "newuser@example.com",
            "password1": "Testpass@123",
            "password2": "Testpass@123",
            "phone": "9876543210",
            "resume": resume,
        })
        self.assertEqual(response.status_code, 302)  # Redirect on success
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_sign_up_existing_email(self):
        """Test signup failure for existing email"""
        response = self.client.post(reverse("sign_up"), {
            "username": "newuser2",
            "email": "test@example.com",  # Already used email
            "password1": "Testpass@123",
            "password2": "Testpass@123",
            "phone": "9876543210",
            "resume": SimpleUploadedFile("resume.pdf", b"Test Resume", content_type="application/pdf"),
        })
        self.assertEqual(response.status_code, 200)  # Should render form with error
        self.assertContains(response, "A user with the email <strong>test@example.com</strong> already exists.")

    def test_home_view_authenticated(self):
        """Test home page access for logged-in users"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("automated_resume-home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "automated_resume/home.html")

    def test_home_view_unauthenticated(self):
        """Test home page redirects unauthenticated users"""
        response = self.client.get(reverse("automated_resume-home"))
        self.assertEqual(response.status_code, 302)

    def test_user_profile_json_response(self):
        """Test user profile API response"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("user-profile"))
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["ats_score"], 75)
        self.assertEqual(response_data["ats_remarks"], "Good")

    def test_results_view(self):
        """Test results view for authenticated users"""
        self.client.login(username="testuser", password="testpass123")
        ResultData.objects.create(TestID=self.profile, Marks=5, Result=True)

        response = self.client.get(reverse("results-page"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "5")  # Check score in response

    def test_save_recording(self):
        """Test video recording save functionality"""
        video = SimpleUploadedFile("test.mp4", b"Test video content", content_type="video/mp4")
        response = self.client.post(reverse("save_recording"), {"video": video})
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json())

    def test_save_flags(self):
        """Test saving proctoring flags"""
        response = self.client.post(reverse("save_flags"), json.dumps({"flags": 3}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["flags"], 3)