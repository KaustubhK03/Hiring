# my_app/tasks.py
import os
import time
import smtplib
import json
from django.db.models import Max
from celery import shared_task
from celery_progress.backend import ProgressRecorder
from django.core.cache import cache  # To store progress state
from .models import EmailManager
from celery import shared_task
from django.core.mail import send_mail
from dotenv import load_dotenv
from .models import *
from .utils import *

load_dotenv()

@shared_task(bind=True)
def send_email(self, user_email, resume_data_id):
    try:
        start_time = time.time()
        profile_data = CustomUser.objects.get(id=resume_data_id)
        html_content = f"""
                <html>
                    <body>
                        <p>Congratulations! You have passed the first screening.</p>
                        <p>Click on the link below to continue with the coding test before the specified date:</p>
                        <a href='http://127.0.0.1:8000/verify-email/'>Start Coding Test</a>
                    </body>
                </html>
                """
        with smtplib.SMTP(f"{os.getenv('EMAIL_SERVICE')}", port=587) as connection:
            connection.starttls()
            connection.login(user=os.getenv("EMAIL"), password=os.getenv("APP_PASSWORD"))
            connection.sendmail(
                from_addr=os.getenv("EMAIL"),
                to_addrs=user_email,
                msg=f"Subject: Coding Test Link\n"
                    f"Content-Type: text/html; charset=UTF-8\n\n"
                    f"{html_content}"
            )
        EmailManager.objects.filter(receiver=profile_data).update(
            msg=f"Subject: Coding Test Link\n"
                f"Content-Type: text/html; charset=UTF-8\n\n"
                f"{html_content}"
        )
        end_time = time.time()  # End timer
        time_taken = end_time - start_time  # Calculate time difference
        return f"Email sent successfully to {user_email} in {time_taken:.2f} seconds"  # Return a success message
    except CustomUser.DoesNotExist:
        print(f"❌ No ResumeData found for ID: {resume_data_id}")
        return "Email sending failed: User not found"
    except Exception as e:
        print(f"Error sending email to {user_email}: {e}")
        raise  # Re-raise the exception to trigger retry (if configured)
        # Or return a failure message: return f"Email sending failed: {e}"

@shared_task(bind=True)
def send_otp(self, user_email, otp):
    try:
        start_time = time.time()
        otp_html_content = f"""
                        <html>
                            <body>
                                <p>{otp} is your one-time otp to start the coding test. PLease do not share this 
                                with anyone else</p>
                            </body>
                        </html>
                        """
        with smtplib.SMTP(f"{os.getenv('EMAIL_SERVICE')}", port=587) as connection:
            connection.starttls()
            connection.login(user=os.getenv("EMAIL"), password=os.getenv("APP_PASSWORD"))
            connection.sendmail(
                from_addr=os.getenv("EMAIL"),
                to_addrs=user_email,
                msg=f"Subject: Resume Analyser-OTP\n"
                    f"Content-Type: text/html; charset=UTF-8\n\n"
                    f"{otp_html_content}"
            )
        end_time = time.time()  # End timer
        time_taken = end_time - start_time  # Calculate time difference
        return f"Email sent successfully to {user_email} in {time_taken:.2f} seconds"  # Return a success message
    except Exception as e:
        print(f"Error sending email to {user_email}: {e}")
        raise  # Re-raise the exception to trigger retry (if configured)
    
@shared_task(bind=True)
def parse_resume(self, user_id, pdf_path, jd_path):
    progress_recorder = ProgressRecorder(self)
    
    progress_recorder.set_progress(1, 5, description="Extracting text from resume and Job Description")
    resume_text = extract_text_from_resume(pdf_path)
    jd_text = extract_text_from_resume(jd_path)
    
    progress_recorder.set_progress(2, 5, description="Calculating ATS Score")
    ats_response = ats_score(resume_text, jd_text)
    ats_dict = extract_dict_from_ats_response(ats_response)
    
    
    progress_recorder.set_progress(3, 5, description="Extracting info from resume")
    experience_level, skills_str = extract_skills(pdf_path)
    
    user = CustomUser.objects.get(id=user_id)
    
    # Update or Create Profile
    progress_recorder.set_progress(5, 5, description="Saving Profile")
    profile, created = Profile.objects.get_or_create(user=user)

    profile.resume = pdf_path  # Resume file
    profile.experience = experience_level
    profile.skills = skills_str
    profile.ats_score = float(ats_dict['JD_Match'].replace("%", ""))
    profile.missing_keywords = ats_dict['MissingKeywords']
    profile.ats_remarks = ats_dict['Profile_Summary']
    profile.save()

@shared_task(bind=True)
def save_questions(self, profile_id, answer_dict, questions_dict):
    from automated_resume.models import Profile
    profile = Profile.objects.get(id=profile_id)
    correct_answers = []
    for count, (question, options_dict) in enumerate(questions_dict.items()):
        correct_answer = answer_dict.get(question, "")
        correct_answers.append(correct_answer)
        options_list = [text.replace("**", "").replace("****", "").replace("*(Correct)*", "")
                        .replace("**(Correct)**", "").replace("(Correct)", "") for text in options_dict.values()]
        QuesModel.objects.create(
            TestID=profile,
            question=question,
            op1=options_list[0],
            op2=options_list[1],
            op3=options_list[2],
            op4=options_list[3],
            ans=correct_answer
        )
        
@shared_task
def update_dashboard_cache():
    total_tests = ResultData.objects.count()
    passed_tests = ResultData.objects.filter(Result=True).count()
    failed_tests = total_tests - passed_tests
    # Get the maximum marks
    max_marks = ResultData.objects.aggregate(Max("Marks"))["Marks__max"]

    # Retrieve the user(s) with the highest marks
    top_performers = ResultData.objects.filter(Marks=max_marks)

    # Get the first top performer (if needed)
    top_performer = top_performers.first()
    
    top_performer_details = ResultData.objects.filter(Marks=max_marks).select_related("TestID").first()
    user_profile = top_performer_details.TestID  # Profile object
    results = ResultData.objects.select_related('TestID__user').values(
            'TestID__user__first_name',  # First Name
            'TestID__user__last_name',   # Last Name
            'Marks',                     # Percent (Assuming Marks represent percentage)
            'Flags'                      # Flags
        )

    pie_chart_graph_data = {
        "labels": ["Passed", "Failed"],
        "data": [passed_tests, failed_tests]
    }
    
    top_performer_data = {
        "TopPerformerMail": user_profile.user,
        "TopPerformerMarks": top_performer.Marks,
        "TopPerformerFlags" : top_performer.Flags,
    }
    cache.set("TopPerformerData", top_performer_data, timeout=300)
    cache.set("PieChartData", json.dumps(pie_chart_graph_data), timeout=300)
    cache.set("Results_cache", results, timeout=300)