from django.test import TestCase, Client
from django.urls import reverse
from automated_resume.models import *
from faker import Faker

faker = Faker()

class UrlsTest(TestCase):
    
    def setUp(self):
        """ setup test client and user """
        self.client = Client()
        self.user = CustomUser.objects.create_user(username=faker.user_name(), email=faker.email(), password="TestUser123")
        
        
    def test_redirect_for_unauthenticated_user(self):
        """Ensure unauthenticated users are redirected"""
        response = self.client.get(reverse("results-page"))
        self.assertEqual(response.status_code, 302)
        