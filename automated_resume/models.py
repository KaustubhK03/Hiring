from django.db import models
from datetime import timedelta
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from pgcrypto.fields import EncryptedTextField
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

class CustomUser(AbstractUser):
    """
    Custom user model with additional fields. This extends the built-in Django User model and adds additional fields.
    """
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('N', 'Prefer not to say')
    ]
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=False)
    last_name = models.CharField(max_length=30, blank=False)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='N')

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


    
    
class Profile(models.Model):
    """
    Profile model for storing additional information about the user. 
    This extends the built-in Django UserProfile model and adds additional fields.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone = models.CharField(max_length=10)
    resume = models.FileField(upload_to='resumes/')
    experience = models.CharField(max_length=14)
    skills = models.TextField()
    ats_score = models.FloatField(null=True, blank=True)
    missing_keywords = models.TextField(null=True, blank=True)
    ats_remarks = models.TextField(null=True, blank=True)

class QuesModel(models.Model):
    """
    Question model for storing the questions and options.
    """
    TestID = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True)
    question = models.CharField(max_length=200, null=True)
    op1 = models.CharField(max_length=200, null=True)
    op2 = models.CharField(max_length=200, null=True)
    op3 = models.CharField(max_length=200, null=True)
    op4 = models.CharField(max_length=200, null=True)
    ans = models.CharField(max_length=200, null=True)

class ResultData(models.Model):
    """
    Result model for storing the results of the test.
    """
    TestID = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True)
    Marks = models.IntegerField()
    Result = models.BooleanField()
    Flags = models.IntegerField(default=0)


class SelectedOptionDatabase(models.Model):
    """
    SelectedOptionDatabase model for storing the selected options of the candidates.
    """
    selected_id = models.ForeignKey(QuesModel, on_delete=models.CASCADE, null=True)
    selectOption = models.TextField()


class EmailManager(models.Model):
    """
    EmailManager model for storing the email data for the users who have cleared the quiz test.
    """
    receiver = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field='email',  # Reference the 'email' field of ResumeData
        db_column='receiver',  # Set the column name explicitly
        primary_key=True,  # Make it the primary key
        unique=True
    )
    sender = models.EmailField(default="kalambkarkaustubh@gmail.com")
    msg = models.TextField(default=None)

    def __str__(self):
        return self.receiver.email

class AdminDashboardConfig(models.Model):
    """
    AdminDashboardConfig model for storing the configurations for the admin dashboards. Right now it is not used.
    """
    name = models.CharField(max_length=100, unique=True)  # Dashboard Name
    selected_model = models.CharField(max_length=100)  # Model Name as String
    selected_fields = models.JSONField(default=list)  # Store fields in JSON format
    CHART_CHOICES = [
        ('bar', 'Bar Chart'),
        ('pie', 'Pie Chart'),
        ('line', 'Line Chart'),
        ('table', 'Table'),
        ('scatter', 'Scatter Plot'),
        ('histogram', 'Histogram'),
        ('boxplot', 'Box Plot'),
        ('heatmap', 'Heatmap'),
        ('bubble', 'Bubble Chart'),
        ('area', 'Area Chart'),
        ('violin', 'Violin Plot'),
        ('radar', 'Radar Chart'),
        ('donut', 'Donut Chart'),
        ('stacked_bar', 'Stacked Bar Chart'),
        ('funnel', 'Funnel Chart')
    ]
    chart_type = models.CharField(
        max_length=20, choices=CHART_CHOICES
    )
    
    def __str__(self):
        return self.name


class AdminSetting(models.Model):
    LLM = models.CharField(max_length=20, choices=[('chatgpt', 'ChatGpt'), ('gemini', 'Gemini')], default="gemini")
    PASSING_PERCENT = models.FloatField(default=0.75)
    CUTOFF = models.IntegerField(default=25)
    JD_TO_USE = models.TextField(default="Dot Net Developer")
    NUMBER_OF_QUIZ_QUESTIONS =  models.IntegerField(default=30)
    NUMBER_OF_CODING_QUESTIONS = models.IntegerField(default=2)
    NUMBER_OF_VIOLATIONS = models.IntegerField(default=15)
    QUIZ_TIME_LIMIT = models.DurationField(default=timedelta(minutes=15))
    CODING_TIME_LIMIT = models.DurationField(default=timedelta(minutes=60))
    FIRST_QUESTION_DIFFICULTY = models.CharField(max_length=20, default="easy")
    SECOND_QUESTION_DIFFICULTY = models.CharField(max_length=20, default="medium")
    
    
class QuestionBank(models.Model):
    """
    QuestionBank model for storing the questions, options, and test cases.
    """
    problem_name = models.TextField()
    problem_statement = models.TextField()
    problem_description = models.TextField()
    input_format = models.TextField()
    output_format = models.TextField()
    difficulty_level = models.CharField(
        max_length=10, 
        choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')]
    )
    
    def __str__(self):
        return self.problem_name
    
class TestCases(models.Model):
    """
    TestCases model for storing the test cases for each problem. Has a many to one relationship with QuestionBank.
    """
    problem = models.ForeignKey(QuestionBank, on_delete=models.CASCADE, related_name="test_cases")
    input_test_case = models.TextField()
    expected_output = models.TextField()
    is_public = models.BooleanField(default=False)
    output_explanation = models.TextField(null=True, blank=True)
    
    def clean(self):
        # Ensure output_explanation is provided if test case is public
        if self.is_public and not self.output_explanation:
            raise ValidationError("Public test cases must have an output explanation.")
        
        
    def __str__(self):
        return f"TestCase for {self.problem.problem_name} (Public: {self.is_public})"
    
class CodingResult(models.Model):
    """
    CodingResult model for storing the coding results submitted by each user. Has a many to one relationship with QuestionBank and User.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    problem = models.ForeignKey(QuestionBank, on_delete=models.CASCADE)
    submitted_code = models.TextField()
    language_id = models.IntegerField()
    submitted_time = models.DateTimeField(auto_now_add=False)
    total_test_cases = models.IntegerField()
    test_cases_passed = models.IntegerField()
    flags_raised = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('user', 'problem')
        
    def __str__(self):
        return f"CodingResult for {self.user.username} on {self.problem.problem_name}"
    