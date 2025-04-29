from django.test import TestCase
from faker import Faker
from django.contrib.auth import get_user_model
from automated_resume.models import *

faker = Faker()

class CustomUserModelTest(TestCase):
    
    def test_create_user(self):
        """ Test creating a user with a valid email """
        email = faker.email()
        username = faker.user_name()
        user = CustomUser.objects.create_user(username=username, email=email, password="Testpass123")
        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password("Testpass123"))
        
    def test_create_superuser(self):
        """Test Creating a superuser """
        email = faker.email()
        super_user = CustomUser.objects.create_superuser(username="admin", email=email, password="Adminpass123")
        self.assertTrue(super_user.is_staff)
        self.assertTrue(super_user.is_superuser)

class ProfileModelTest(TestCase):
    def setUp(self):
        """Set up a user and profile for testing"""
        self.user = CustomUser.objects.create_user(username=faker.user_name(), email=faker.email(), password="TestPass123")
        self.profile = Profile.objects.create(
            user=self.user,
            phone=faker.random_number(digits=10),
            resume="resumes/test_resume.pdf",
            experience="3 years",
            skills="Python, Django, Machine Learning",
            ats_score=85.5,
            missing_keywords="NLP, AI",
            ats_remarks="Needs more AI-related keywords"
        )
    
    def test_profile_creation(self):
        """Test profile is created correctly"""
        self.assertEqual(self.profile.user, self.user)
        
        
class QuesModelTest(TestCase):
    def setUp(self):
        """Set up a test profile and question"""
        self.user = CustomUser.objects.create_user(username=faker.user_name(), email=faker.email(), password="TestPass123")
        self.profile = Profile.objects.create(user=self.user, phone="1234567890", resume="test.pdf", experience="2 years", skills="Python")
        self.question = QuesModel.objects.create(
            TestID=self.profile,
            question=faker.sentence(),
            op1="Option A",
            op2="Option B",
            op3="Option C",
            op4="Option D",
            ans="Option A"
        )

    def test_question_creation(self):
        """Test question model creation"""
        self.assertEqual(self.question.TestID, self.profile)
        self.assertEqual(self.question.ans, "Option A")


class ResultDataTest(TestCase):
    def setUp(self):
        """Set up a profile and result data"""
        self.user = CustomUser.objects.create_user(username=faker.user_name(), email=faker.email(), password="TestPass123")
        self.profile = Profile.objects.create(user=self.user, phone="1234567890", resume="test.pdf", experience="2 years", skills="Python")
        self.result = ResultData.objects.create(TestID=self.profile, Marks=80, Result=True)

    def test_result_data_creation(self):
        """Test result data is stored properly"""
        self.assertEqual(self.result.Marks, 80)
        self.assertTrue(self.result.Result)