import os
import json
import re
import random
import logging
import base64
import time
from pprint import pprint
from datetime import datetime, timedelta
from django.db.models import Max
from django.apps import apps
from django.db.utils import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.utils.timezone import localtime
from django.contrib.auth import login, logout
from django.core.exceptions import ObjectDoesNotExist
from celery.result import AsyncResult
from dotenv import load_dotenv
from .forms import *
from .models import *
from .tasks import *
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
from .utils import *
from .api_calls import *

load_dotenv()  # loading the environment variables

# Make a Directory for storing video files
if not os.path.exists(settings.VIDEO_UPLOAD_DIR):
    os.makedirs(settings.VIDEO_UPLOAD_DIR)

# To calculate the six months timer for re-attempting the quiz
def six_months_timer(quiz_date) -> bool:
    """
    Checks if the quiz was attempted within the last six months.

    Parameters:
    quiz_date (datetime): The date of the quiz attempt.

    Returns:
    bool: True if the quiz was attempted within the last six months, False otherwise.

    """
    current_date = datetime.now()
    six_months_ago = current_date - timedelta(days=6 * 30)
    six_months_ago = six_months_ago.date()
    if six_months_ago >= quiz_date:
        return True
    else:
        return False

# Create a cache for storing dashboard data, works with celery to cache data every 5 minutes
def get_dashboard_data():
    """
    Retrieves and caches dashboard data.

    Returns:
    dict: The dashboard data containing pie chart data, top performer data, and results.
    """
    pie_cache_key = "PieChartData"
    top_performer_cache = "TopPerformerData"
    result_cache = "Results_cache"
    bar_chart_cache = "TopScoresData"
    
    dashboard_data = cache.get(pie_cache_key)
    top_performer_data = cache.get(top_performer_cache)
    results = cache.get(result_cache)
    top_scores_data = cache.get(bar_chart_cache)
    
    if not dashboard_data or not top_performer_data or not results or not top_scores_data:
        # Pie chart data (Pass/Fail)
        total_tests = ResultData.objects.count()
        passed_tests = ResultData.objects.filter(Result=True).count()
        failed_tests = total_tests - passed_tests

        graph_data = {
            "labels": ["Passed", "Failed"],
            "data": [passed_tests, failed_tests],
        }
        dashboard_data = json.dumps(graph_data)
        cache.set(pie_cache_key, dashboard_data, timeout=300)

        # Handle case when there are no results
        if total_tests == 0:
            top_performer_data = {
                "TopPerformerMail": "N/A",
                "TopPerformerMarks": 0,
                "TopPerformerFlags": 0,
            }
            results = []
            top_scores_data = {
                "labels": [],
                "data": [],
                "colors": []
            }
        else:
            max_marks = ResultData.objects.aggregate(Max("Marks"))["Marks__max"]
            top_performers = ResultData.objects.filter(Marks=max_marks)
            top_performer = top_performers.first()
            top_performer_details = ResultData.objects.filter(Marks=max_marks).select_related("TestID").first()
            user_profile = top_performer_details.TestID

            results = ResultData.objects.select_related('TestID__user').values(
                'TestID__user__first_name',
                'TestID__user__last_name',
                'TestID__user__gender',
                'Marks',
                'Flags',
            ).order_by('-Marks')[:10]

            usernames = []
            scores = []
            colors = []

            for result in results:
                username = f"{result['TestID__user__first_name']} {result['TestID__user__last_name']}"
                usernames.append(username)
                scores.append(result['Marks'])

                if result['TestID__user__gender'].lower() == "female":
                    colors.append("pink")
                else:
                    colors.append("blue")

            top_performer_data = {
                "TopPerformerMail": user_profile.user,
                "TopPerformerMarks": top_performer.Marks,
                "TopPerformerFlags": top_performer.Flags,
            }
            top_scores_data = {
                "labels": usernames,
                "data": scores,
                "colors": colors
            }

        cache.set(top_performer_cache, top_performer_data, timeout=300)
        cache.set(result_cache, results, timeout=300)
        cache.set(bar_chart_cache, json.dumps(top_scores_data), timeout=300)

    return dashboard_data, top_performer_data, results, top_scores_data

def extract_email(text):
    """
    Extracts the email from the given text.

    Parameters:
    text (str): The text from which to extract the email.

    Returns:
    str: The extracted email, or an empty string if no email was found.
    """
    match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
    return match.group(0)


def landing_page(request):
    """
    Renders the landing page.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    HttpResponse: The rendered landing page.
    """
    return render(request, "automated_resume/landing_page.html")


def logout_view(request):
    """
    Logs out the user and redirects to the landing page. This uses the django built-in logout function.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    """
    logout(request)
    return redirect('landing_page')

def sign_up(request):
    """
    Handles the sign-up form submission.

    Parameters:
    request (HttpRequest): The HTTP request object.
    """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            email = form.cleaned_data['email']
            username = form.cleaned_data['username']
            resume = request.FILES['resume']
            password = form.cleaned_data['password1']
            phone = form.cleaned_data['phone']
            
            # Check if a user with the same email or username already exists
            if CustomUser.objects.filter(email=email).exists():
                messages.error(
                    request,
                    mark_safe(f"A user with the email <strong>{email}</strong> already exists. Please use a different email.")
                )
                return render(request, "registration/sign_up.html", {"form": form})

            if CustomUser.objects.filter(username=username).exists():
                messages.error(
                    request,
                    mark_safe(f"A user with the username <strong>{username}</strong> already exists. Please choose a different username.")
                )
                return render(request, "registration/sign_up.html", {"form": form})
            
            # Save the resume file in a resume folder
            resume_folder = os.path.join(settings.RESUME_PATH, 'resumes')
            os.makedirs(resume_folder, exist_ok=True)  # Create folder if it doesn't exist
            
            # Define resume file path inside 'resume/' folder
            resume_filename = resume.name
            resume_path = os.path.join(resume_folder, resume_filename)
            
            # Check if the resume already exists
            if os.path.exists(resume_path):
                print(f"Resume '{resume_filename}' already exists. Using existing file.")
            else:
                # Save the new resume file
                fs = FileSystemStorage(location=resume_folder)
                resume_path = os.path.join(resume_folder, fs.save(resume_filename, resume))

            
            # Handle the case when user does not provide a valid resume
            try:
                email_of_candidate = extract_email(extract_text_from_resume(resume_path))
            except AttributeError:
                messages.error(
                    request,
                    mark_safe("This file does not contain any email.... Are you sure you uploaded a resume?")
                )
                return render(request, "registration/sign_up.html", {"form": form})
            
            # Handle the case when user does not provide the same email mentioned in the resume
            if email != email_of_candidate:
                messages.error(
                    request,
                    mark_safe(
                        f"The email you provided ({email}) does not match the email extracted from your resume "
                        f"({email_of_candidate}). Please update the email field.")
                )
                return render(request, "registration/sign_up.html", {"form": form})
            
            user = form.save(commit=False)
            user.set_password(password)
            user.save()
            
            # Create Profile
            Profile.objects.create(
                user=user,
                phone=phone,  
                resume=resume_path
            )
            
            login(request, user)  # Automatically log in the user
            
            # This line takes all The job descriptions in the jd folder declared in static and stores it in a list
            # Then it finds the required JD based on the given form input in adminsettings.html
            JD_Names_list = (os.listdir(settings.PATH_TO_JDS))
            admin_settings_object = AdminSetting.objects.first() or AdminSetting()
            jd_pdf_path = get_required_jd_path(JD_Names_list, admin_settings_object.JD_TO_USE)
            
            # Start parsing resume asynchronously if user is authenticated and there is a valid job description path
            if request.user.is_authenticated:
                task = parse_resume.delay(
                    user_id = user.id,
                    pdf_path=resume_path,
                    jd_path=jd_pdf_path
                )
            response = redirect('automated_resume-home')  # Redirect to home page
            response.set_cookie("task_id", task.id)  # Store task ID in cookies
            return response
    else:
        #If the request method is not POST, render the sign-up form
        form = CustomUserCreationForm()
    return render(request, 'registration/sign_up.html', {'form': form})


def task_status(request, task_id):
    """
    Retrieves the status of a task given to celery asynchronously. All the tasks are defined in tasks.py.

    Parameters:
    request (HttpRequest): The HTTP request object.
    task_id (str): The ID of the asynchronous task.

    Returns:
    JsonResponse: The status of the task in JSON format.
    """
    if request.user.is_authenticated:
        result = AsyncResult(task_id)
        response_data = {"status": result.status}
        
        if result.status == 'PROGRESS':
            response_data["progress"] = result.info.get("current", 0) / result.info.get("total", 1) * 100
            response_data["description"] = result.info.get("description", "Processing...")
        
        elif result.status == "SUCCESS":
            user = request.user
            profile = Profile.objects.get(user=user)
            response_data["ats_score"] = profile.ats_score
            response_data["missing_keywords"] = profile.missing_keywords.replace("[", "").replace("]", "").replace("'", "").replace('"', "").split(",")
            response_data["ats_remarks"] = profile.ats_remarks
        
        return JsonResponse(response_data)
    return render(request, 'automated_resume/landing_page.html')

# Create your views here.
@login_required
def home(request):
    """
    Renders the home page for authenticated users. And the dashboard for admins.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    HttpResponse: The rendered home page.
    """
    if request.user.is_superuser:
        return redirect('admin_dashboard')
    return render(request, "automated_resume/home.html")


@login_required
def user_profile(request):
    """
    Renders the user profile page for authenticated users. i.e it displayes the ats score to the front end.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    HttpResponse: The rendered user profile page.
    """
    try:
        profile = Profile.objects.get(user=request.user)
        # missing_keywords = profile.missing_keywords
        # if isinstance(missing_keywords, str):
        #     try:
        #         missing_keywords = json.loads(missing_keywords)  # Convert string to list if needed
        #     except json.JSONDecodeError:
        #         missing_keywords = [] 
                
        response_data = {
            "ats_score": profile.ats_score,
            "missing_keywords": profile.missing_keywords.replace("[", "").replace("]", "").replace("'", "").replace('"', "").split(","),
            "ats_remarks": profile.ats_remarks,
        }
    except Profile.DoesNotExist:
        response_data = {
            "ats_score": "No Score Available",
            "missing_keywords": [],
            "ats_remarks": "No remarks available",
        }

    return JsonResponse(response_data)

@never_cache
@login_required
def display_instructions(request):
    """
    This is the main quiz page it displays the quiz questions. and also the instructions. This page can be visited only once as it never caches the page.
    Parameters:
    request (HttpRequest): The HTTP request object.
    Returns:
    HttpResponse: The rendered quiz page.
    """
    user_object = get_object_or_404(CustomUser, email=request.user.email)
    profile = get_object_or_404(Profile, user=user_object)
    
    # Check if the user has already attempted the quiz
    if ResultData.objects.filter(TestID=profile).exists():
        return HttpResponseRedirect("results")
    
    # Fetch the time limit for the quiz from the Admin Setting DB
    admin_settings_object = AdminSetting.objects.first() or AdminSetting()
    quiz_time_limit = admin_settings_object.QUIZ_TIME_LIMIT
    
    # Check if questions already exist in the database for this user
    existing_questions = QuesModel.objects.filter(TestID=profile)

    if existing_questions.exists():
        # If questions exist, retrieve them and prepare them for display
        questions_dict = {
            question_obj.question: {
                "a": question_obj.op1,
                "b": question_obj.op2,
                "c": question_obj.op3,
                "d": question_obj.op4
            }
            for question_obj in existing_questions
        }

        answer_dict = {
            question_obj.question: question_obj.ans
            for question_obj in existing_questions
        }
    else:
        try:
            questionnaire = extract_question(extracted_skills=profile.skills, experience_level=profile.experience)
            questions_dict = parse_questions(questionnaire)
            answer_dict, questions_dict = extract_correct_answers(questions_dict)
        except Exception:
            return render(request, "automated_resume/gemini_crash.html")
        
        
        # Give the below code to celery for storing questions and answers
        save_questions.delay(
            profile_id=profile.id,
            answer_dict=answer_dict,
            questions_dict=questions_dict
        )
    cleaned_questions_dict = clean_questions_dict(questions_dict=questions_dict)
    context = {
        "questions_dict": cleaned_questions_dict,
        "answer_dict": answer_dict,
        "quiz_time_limit": quiz_time_limit.seconds / 60
    }
    return render(request, "automated_resume/instructions.html", context)

def clean_questions_dict(questions_dict):
    """
    Removes extra spaces and asterisks from the question options.
    Parameters:
    questions_dict (dict): The dictionary containing the questions and options.
    Returns:
    dict: The cleaned dictionary containing the questions and options.
    """
    # Remove extra spaces and asterisks from the question options.
    # Example: {"Question": {"a": "Option A ****", "b": "Option B ****"}} -> {"Question": {"a": "Option A", "b": "Option B"}}
    cleaned_dict = {}
    for question, options in questions_dict.items():
        cleaned_options = {key: value.replace(' ****', '') for key, value in options.items()}
        cleaned_dict[question] = cleaned_options
    return cleaned_dict


@login_required
def results(request):
    """
    This is the page where the user can see their results.
    Parameters:
    request (HttpRequest): The HTTP request object.
    Returns:
    HttpResponse: The rendered results page.
    """
    user_object = get_object_or_404(CustomUser, email=request.user.email)
    profile = get_object_or_404(Profile, user=user_object)

    question_objects_list = get_list_or_404(QuesModel, TestID=profile)
    admin_settings_object = AdminSetting.objects.first() or AdminSetting()
    cutoff = admin_settings_object.CUTOFF
    questions_dict = {
        f"{question_obj.question}":{
            "a": question_obj.op1.strip(),
            "b": question_obj.op2.strip(),
            "c": question_obj.op3.strip(),
            "d": question_obj.op4.strip()
        }
        for idx, question_obj in enumerate(question_objects_list)
    }
    answer_dict = {
        f"{question_obj.question}": question_obj.ans.strip()
        for idx, question_obj in enumerate(question_objects_list)
    }
    flags = request.session.get("user_flags", 0)
    # if flags == 0:
    #     try:
    #         data = json.loads(request.body)
    #         flags = data.get("flags", 0)
    #     except json.JSONDecodeError:
    #         user_profile = Profile.objects.get(user=request.user)
    #         result_entry = ResultData.objects.filter(TestID=user_profile).first()
    #         flags = result_entry.Flags if result_entry else 0
    if request.method == "POST":
        selected_answers = request.POST.get("selectedAnswers")
        selected_answers = json.loads(selected_answers)  # Parse JSON string to a Python dictionary

        # Calculate the score
        score = 0
        total_questions = len(questions_dict)
        for count, correct_answer in enumerate(answer_dict.values(), start=1):
            user_answer = selected_answers.get(f"q{count}", "").strip()
            correct_answer = correct_answer.strip()

            if user_answer == correct_answer:
                score += 1

        percent = round((score / total_questions) * 100, 0)
        request.session["score"] = score

        # Save selected answers in database
        for index, question_object in enumerate(question_objects_list):
            existing_entry = SelectedOptionDatabase.objects.filter(
                selected_id=question_object,
                selectOption=selected_answers.get(f"q{index + 1}", "Not Answered")
            ).exists()
            if not existing_entry:
                SelectedOptionDatabase.objects.create(
                    selected_id=question_object,
                    selectOption=selected_answers.get(f"q{index + 1}", "Not Answered")
                )
        # Save result in database if not already stored
        if not ResultData.objects.filter(TestID=profile).exists():
            result_entry = ResultData.objects.create(
                TestID=profile,
                Marks=score,
                Result=cutoff <= score,
                Flags=flags,
            )

    else:  # Handle GET request
        result_obj = ResultData.objects.get(TestID=profile.id)
        score = result_obj.Marks
        percent = round((score / len(question_objects_list)) * 100, 0)
        selected_answers = {
            f"q{idx + 1}": SelectedOptionDatabase.objects.filter(selected_id=question_obj).first().selectOption
            for idx, question_obj in enumerate(question_objects_list)
        }

    # Prepare review data
    review_data = []
    correct_answers = 0
    for idx, question_obj in enumerate(question_objects_list):
        is_correct = question_obj.ans.strip() == selected_answers.get(f"q{idx + 1}", "").strip()
        if is_correct:
            correct_answers += 1

        options = [
            question_obj.op1.strip(),
            question_obj.op2.strip(),
            question_obj.op3.strip(),
            question_obj.op4.strip(),
        ]
        review_data.append({
            "question": question_obj.question,
            "options": options,
            "selected_option": selected_answers.get(f"q{idx + 1}", "Not Answered"),
            "correct_option": question_obj.ans,
        })

    context = {
        "percentage": percent,
        "score": score,
        "total_questions": len(question_objects_list),
        "cutoff": cutoff,
        "review_data": review_data,
        "flags": flags,
    }
    if score >= cutoff:
        # try:
        #     email_obj = EmailManager.objects.get(receiver=request.user.email)
        # except ObjectDoesNotExist:
        #     send_email.delay(request.user.email, user_object.id)
        try:
            email_obj, created = EmailManager.objects.get_or_create(
                receiver=request.user,
                sender=os.getenv("EMAIL"),
                msg="Email will be sent soon."
            )
            if created:
                print("Sending email to:", request.user.email)
                send_email.delay(request.user.email, user_object.id)
        except IntegrityError:
            return render(request, "automated_resume/review_n_result.html", context)
    return render(request, "automated_resume/review_n_result.html", context)


@csrf_exempt
def save_recording(request):
    """
    This function is responsible for saving the recorded video.
    Parameters:
    request (HttpRequest): The HTTP request object.
    Returns:
    JsonResponse: A JSON response containing the message and file path of the saved video.
    """
    if request.method == 'POST' and request.FILES.get('video'):
        video_file = request.FILES['video']
        file_path = os.path.join(settings.VIDEO_UPLOAD_DIR, video_file.name)

        with open(file_path, 'wb') as f:
            for chunk in video_file.chunks():
                f.write(chunk)

        return JsonResponse({'message': 'Recording saved successfully', 'file_path': file_path})

    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt 
def save_flags(request):
    """
    This function is responsible for saving the flags generated by the user. A flag is generated automatically if 
    he is caught cheating.
    Parameters:
    request (HttpRequest): The HTTP request object.
    Returns:
    JsonResponse: A JSON response containing the status and flags value.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # Parse JSON request body
            flags = data.get("flags", 0)  # Extract flags value
            request.session['user_flags'] = flags  # Update flags in session
            return JsonResponse({"status": "success", "flags": flags})
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)


def send_otp_view(request):
    """
    This function is responsible for sending the OTP to the user's email address.
    Parameters:
    request (HttpRequest): The HTTP request object.
    Returns:
    HttpResponse: A rendered HTML page with a success message if the OTP is sent successfully.
    """
    if request.method == "POST":
        form = EmailVerification(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                receiver = EmailManager.objects.get(receiver=email)
            except ObjectDoesNotExist:
                messages.error(request, mark_safe("User email not found in the database. Make sure you have passed the "
                                                  "first screening process"))
            else:
                otp = str(random.randint(100000, 999999))  # Generate 6-digit OTP

                # Store OTP in session (alternative: store in database)
                request.session['otp'] = otp
                request.session['email'] = email

                send_otp.delay(user_email=email, otp=otp)

                messages.success(request, mark_safe("OTP sent to your email."))
                return redirect('verify_otp')  # Redirect to OTP verification page
    else:
        if 'otp' in request.session:
            del request.session['otp']
        if 'email' in request.session:
            del request.session['email']
        form = EmailVerification()
    return render(request, "automated_resume/verify_mail.html", {"form": form})


def verify_otp(request):
    """
    This function is responsible for verifying the OTP entered by the user.
    Parameters:
    request (HttpRequest): The HTTP request object.
    Returns:
    HttpResponse: A rendered HTML page with success message if the OTP is verified successfully, or an error message if not.
    """
    if request.method == "POST":
        entered_otp = request.POST.get("otp")  # Get OTP entered by the user
        stored_otp = request.session.get("otp")  # Retrieve OTP from session
        email = request.session.get("email")

        if entered_otp == stored_otp:
            # Login the user if OTP is valid
            login(request, CustomUser.objects.get(email=email))
            messages.success(request, "Email verified successfully!")
            del request.session['otp']
            del request.session['email']
            # Check Weather the user has already given the coding test before
            if not CodingResult.objects.filter(user=request.user).exists():
                return redirect('setup-page')  # Redirect to the coding test page
            else:
                messages.error(request, mark_safe("You have already given the coding test."))
                return redirect('get_result')
        else:
            messages.error(request, mark_safe("Invalid OTP. Please try again."))
            return redirect('verify_otp')

    return render(request, "automated_resume/verify_mail.html")

@login_required
def setup_for_coding_with_instructions(request):
    """
    This function is responsible for displaying the coding instructions to the user. 
    It uses the data from the admin_settings table.
    Parameters:
    request (HttpRequest): The HTTP request object.
    Returns:
    HttpResponse: A rendered HTML page with the coding instructions.
    """
    try:
        receiver = EmailManager.objects.get(receiver=request.user.email)
    except ObjectDoesNotExist:
        messages.error(request, mark_safe("User email not found in the database. Make sure you have passed the "
                                            "first screening process"))
        return redirect('automated_resume-home')
    admin_settings_object = AdminSetting.objects.first() or AdminSetting()
    context = {
        "NUMBER_OF_CODING_QUESTIONS": admin_settings_object.NUMBER_OF_CODING_QUESTIONS,
        "CODING_TIME_LIMIT": admin_settings_object.CODING_TIME_LIMIT
    }
    return render(request, "automated_resume/coding_instructions.html", context)

def fetch_question_from_db(difficulty_level):
    """
    Fetches a question from the database based on the difficulty level.
    Parameters:
    difficulty_level (str): The difficulty level of the question (e.g., easy, medium, hard).
    Returns:
    tuple: A tuple containing the question object, public test cases, and private test cases.
    """
    # if question_id:
    #     question_obj = QuestionBank.objects.get(id=question_id)
    question_obj = QuestionBank.objects.filter(difficulty_level=difficulty_level).first()
    public_test_cases = []
    private_test_cases = []

    for tc in question_obj.test_cases.all():
        case = {
            "Input": tc.input_test_case,
            "Expected_Output": tc.expected_output,
            "is_public": tc.is_public,
        }
        if tc.is_public:
            case["Explanation"] = tc.output_explanation
            public_test_cases.append(case)
        else:
            private_test_cases.append(case)
    return question_obj, public_test_cases, private_test_cases

def fetch_question_with_id(question_id):
    """
    Fetches a question from the database based on the provided question ID.
    Parameters:
    question_id (int): The ID of the question.
    Returns:
    tuple: A tuple containing the question object, public test cases, and private test cases.
    """
    question_obj = QuestionBank.objects.get(id=question_id)
    public_test_cases = []
    private_test_cases = []

    for tc in question_obj.test_cases.all():
        case = {
            "Input": tc.input_test_case,
            "Expected_Output": tc.expected_output,
            "is_public": tc.is_public,
        }
        if tc.is_public:
            case["Explanation"] = tc.output_explanation
            public_test_cases.append(case)
        else:
            private_test_cases.append(case)
    return question_obj, public_test_cases, private_test_cases

@never_cache
@login_required
def route_to_coding_test(request):
    """
    This function is responsible for routing the user to the coding test page. 
    Fetches the coing questions, test cases, and difficulty level, before rendering the page.
    Parameters:
    request (HttpRequest): The HTTP request object.
    Returns:
    HttpResponse: A rendered HTML page with the coding test page.
    """
    try:
        receiver = EmailManager.objects.get(receiver=request.user.email)
    except ObjectDoesNotExist:
        messages.error(request, mark_safe("User email not found in the database. Make sure you have passed the "
                                            "first screening process"))
        return redirect('automated_resume-home')
    
    if CodingResult.objects.filter(user=request.user).exists():
        return HttpResponseRedirect("get_result")
    admin_settings = AdminSetting.objects.first() or AdminSetting()
    first_difficulty_level = admin_settings.FIRST_QUESTION_DIFFICULTY
    second_difficulty_level = admin_settings.SECOND_QUESTION_DIFFICULTY
    coding_time_limit = admin_settings.CODING_TIME_LIMIT
    
    # fetch the first coding question from the database
    question_obj1, public_test_cases1, private_test_cases1 = fetch_question_from_db(first_difficulty_level)
    question_obj2, public_test_cases2, private_test_cases2 = fetch_question_from_db(second_difficulty_level)
    
    question = [
        {
            "id": question_obj1.id,
            "Problem_Name": question_obj1.problem_name,
            "Problem_Statement": question_obj1.problem_statement,
            "Description": question_obj1.problem_description,
            "Public_Test_Cases": public_test_cases1,
            "Private_Test_Cases": private_test_cases1,
        },
        {
            "id": question_obj2.id,
            "Problem_Name": question_obj2.problem_name,
            "Problem_Statement": question_obj2.problem_statement,
            "Description": question_obj2.problem_description,
            "Public_Test_Cases": public_test_cases2,
            "Private_Test_Cases": private_test_cases2,  
        }
    ]
    context = {
        "Available_languages": get_available_languages(),
        "question_list": question,
        "current_question": question[0],
        "coding_time_limit": coding_time_limit,
    }
    return render(request=request, template_name="automated_resume/ide_quiz.html", context=context)


@user_passes_test(lambda u: u.is_superuser) # is_superuser means the user is a superuser/admin/superadmin
def admin_home(request):
    """
    This function is responsible for rendering the admin dashboard.
    It retrieves the dashboard data, top performer data, results, and top scores data from the database.
    Parameters:
    request (HttpRequest): The HTTP request object.
    Returns:
    HttpResponse: A rendered HTML page with the admin dashboard.
    """
    dashboard_data, top_performer_data, results, top_scores_data = get_dashboard_data()
    context = {
        "graph_data": dashboard_data,
        "result_data" : top_performer_data,
        "results": results,
        "top_scores_data": top_scores_data,
    }
    return render(request, 'automated_resume/dashboard.html', context)

@user_passes_test(lambda u: u.is_superuser)
def dashboard_page2(request):
    """
    This function is responsible for rendering the admin dashboard page 2.
    It retrieves the dashboard configurations and data from the database. Right now it is not used.
    Parameters:
    request (HttpRequest): The HTTP request object.
    Returns:
    HttpResponse: A rendered HTML page with the admin dashboard page 2.
    """
    dashboard_configs = AdminDashboardConfig.objects.all()
    dashboard_data = []

    for config in dashboard_configs:
        try:
            ModelClass = apps.get_model('automated_resume', config.selected_model)
            fields = json.loads(config.selected_fields)

            queryset = ModelClass.objects.values(*fields)
            data = list(queryset)

            dashboard_data.append({
                'name': config.name,
                'chart_type': config.chart_type,
                'fields': fields,
                'data': data
            })
        except Exception as e:
            print(f"Error loading model {config.selected_model}: {e}")

    return render(request, "automated_resume/admin_dashboard_page_2.html", {"dashboard_data": dashboard_data})

@user_passes_test(lambda u: u.is_superuser)
def dashboard_settings(request):
    """
    This function is responsible for rendering the admin settings page.
    It retrieves the current admin settings from the database and prepares them for rendering.
    Parameters:
    request (HttpRequest): The HTTP request object.
    Returns:
    HttpResponse: A rendered HTML page with the admin settings.
    """
    settings = AdminSetting.objects.first() or AdminSetting()
    context = {
        "LLM": settings.LLM,
        "CUTOFF": settings.CUTOFF,
        "PASSING_PERCENT": settings.PASSING_PERCENT,
        "JD_TO_USE": settings.JD_TO_USE,
        "NUMBER_OF_QUIZ_QUESTIONS": settings.NUMBER_OF_QUIZ_QUESTIONS,
        "NUMBER_OF_CODING_QUESTIONS": settings.NUMBER_OF_CODING_QUESTIONS,
        "NUMBER_OF_VIOLATIONS": settings.NUMBER_OF_VIOLATIONS,
        "QUIZ_TIME_LIMIT": settings.QUIZ_TIME_LIMIT.seconds / 60,
        "CODING_TIME_LIMIT": settings.CODING_TIME_LIMIT.seconds / 60,
        "FIRST_QUESTION_DIFFICULTY": settings.FIRST_QUESTION_DIFFICULTY,
        "SECOND_QUESTION_DIFFICULTY": settings.SECOND_QUESTION_DIFFICULTY,
    }
    return render(request, "automated_resume/admin_settings.html", context=context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def save_admin_settings(request):
    """
    This function is responsible for saving the admin settings.
    It retrieves the updated settings from the request data and saves them to the database.
    Parameters:
    request (HttpRequest): The HTTP request object.
    Returns:
    JsonResponse: A JSON response with success or error message.
    """
    if request.method == "POST":
        data = request.POST
        settings, created = AdminSetting.objects.get_or_create(id=1)
        settings.LLM = data.get("llm_model", "chatgpt")
        settings.PASSING_PERCENT = float(data.get("passing_percent"))
        settings.NUMBER_OF_QUIZ_QUESTIONS = int(data.get("quiz_questions", 30))
        settings.CUTOFF = settings.NUMBER_OF_QUIZ_QUESTIONS * (settings.PASSING_PERCENT / 100)
        settings.NUMBER_OF_CODING_QUESTIONS = int(data.get("coding_questions", 2))
        settings.NUMBER_OF_VIOLATIONS = int(data.get("violation_frames", 15))
        settings.JD_TO_USE = data.get("job_description", "Dot Net Developer")
        settings.QUIZ_TIME_LIMIT = timedelta(minutes=float(data.get("quiz_time", 15)))
        settings.CODING_TIME_LIMIT = timedelta(minutes=float(data.get("coding_time", 60)))
        settings.FIRST_QUESTION_DIFFICULTY = data.get("firstQuestionDifficulty", "easy")
        settings.SECOND_QUESTION_DIFFICULTY = data.get("secondQuestionDifficulty", "medium")
        settings.save()
        return JsonResponse({"message": "Settings saved successfully."})
    return JsonResponse({"error": "Invalid request."}, status=400)

@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def delete_user_data(request):
    """
    This function is responsible for deleting user data.
    It retrieves the email of the candidate from the request data and deletes all related data from the database.
    Parameters:
    request (HttpRequest): The HTTP request object.
    """
    if request.method == "POST":
        data = request.POST
        email_to_delete = data.get("email_of_user", "") # Get email of the candidate
        
        user_obj = get_object_or_404(CustomUser, email=email_to_delete) # get user obj from CustomUser Model
        profile = get_object_or_404(Profile, user=user_obj) # Get Profile Object 
        
        # Fetch related QuesModel entries
        questions = QuesModel.objects.filter(TestID=profile)
        
        # Delete all SelectedOptionDatabase entries related to these QuesModel entries
        SelectedOptionDatabase.objects.filter(selected_id__in=questions).delete()
        
        # Delete all QuesModel entries related to the profile
        questions.delete()
        
        # Delete all ResultData entries related to the profile
        ResultData.objects.filter(TestID=profile).delete()
        
        # Delete the EmailManager entry related to the user
        EmailManager.objects.filter(receiver=user_obj).delete()
        
        return JsonResponse({"message": "User data deleted successfully."})
    return JsonResponse({"error": "Invalid request."}, status=400)

@csrf_exempt
def get_code_from_frontend(request):
    """
    This function is responsible for receiving code from the frontend and sending it to the backend for execution.
    It retrieves the source code, language ID, and standard input from the request data and sends it to the backend for execution.
    The compiler used here is Judge0, which is hosted on our own server. The request data and response data should be base64 encoded.
    Parameters:
    request (HttpRequest): The HTTP request object.
    Returns:
    JsonResponse: A JSON response with the execution result.
    """
    if request.method == "POST":
        data = json.loads(request.body)
        source_code = data.get("source_code", "")
        language_id = data.get("language_id", "")
        stdin = data.get("stdin", "")
        
        # encode the source code to base64 format for sending to the backend
        encoded_source_code = base64.b64encode(source_code.encode()).decode()
        encoded_stdin = base64.b64encode(stdin.encode()).decode()
        
        # API Call here
        token = create_submission(language_id=language_id, source_code=encoded_source_code, stdin=encoded_stdin)
        output = get_submission(token)
        while output["status"]["id"] in [1, 2]:  # 1 = In Queue, 2 = Processing
            time.sleep(0.5)
            output = get_submission(token)
        decoded_compile_output = base64.b64decode(output["compile_output"]).decode() if output.get("compile_output") else None
        decode_message = base64.b64decode(output["message"]).decode() if output.get("message") else None
        decoded_output = base64.b64decode(output["stdout"]).decode() if output.get("stdout") else None
        
        # stdout,time,memory,token,compile_output,message,status,language_id
        return JsonResponse({"stdout": decoded_output,
                             "time": output["time"],
                             "memory": output["memory"],
                            "token": output["token"],
                            "compile_output": decoded_compile_output,
                            "message": decode_message,
                            "status_id": output["status"],
                            "language_id": output["language_id"],
                            })
    return JsonResponse({"error": "Invalid request."}, status=400)

@csrf_exempt
def run_test_cases(request):
    """
    This function is responsible for running test cases for a given problem.
    It retrieves the source code, language ID, and question ID, public test cases and private test cases from the request data and sends it to the backend for execution.
    The test cases are fetched from the database and sent to the backend for execution.
    Parameters:
    request (HttpRequest): The HTTP request object.
    Returns:
    JsonResponse: A JSON response with the execution results for each test case.
    """
    if request.method == "POST":
        data = json.loads(request.body)
        source_code = data["source_code"]
        language_id = data["language_id"]
        question_id = data["question_id"]
        stdin_lst = []
        expected_output_lst = []
        
        # call the fetch_question_from_db function to get test cases
        question_obj, public_test_cases, private_test_cases = fetch_question_with_id(question_id)
        
        # make the question dictionary
        question = {
            "Problem_Name": question_obj.problem_name,
            "Problem_Statement": question_obj.problem_statement,
            "Description": question_obj.problem_description,
            "Public_Test_Cases": public_test_cases,
            "Private_Test_Cases": private_test_cases,
        }
        for lst in question["Public_Test_Cases"]:
            encoded_stdin = base64.b64encode(lst["Input"].encode()).decode()
            encoded_expected_output = base64.b64encode(lst["Expected_Output"].encode()).decode()
            stdin_lst.append(encoded_stdin)
            expected_output_lst.append(encoded_expected_output)
        for lst in question["Private_Test_Cases"]:
            encoded_stdin = base64.b64encode(lst["Input"].encode()).decode()
            encoded_expected_output = base64.b64encode(lst["Expected_Output"].encode()).decode()
            stdin_lst.append(encoded_stdin)
            expected_output_lst.append(encoded_expected_output)
        
        # encode the source code to base64 format for sending to the backend
        encoded_source_code = base64.b64encode(source_code.encode()).decode()
        
        # API Call here
        tokens = create_submission_batch(source_code=encoded_source_code, language_id=language_id, stdin_list=stdin_lst, expected_out_lst=expected_output_lst)
        token_list = []
        for dct in tokens:
            token_list.append(dct["token"])
        batch_output = get_submission_batch(token_list)
        
        while batch_output["submissions"][-1]["status_id"] in [1, 2]:  # 1 = In Queue, 2 = Processing
            time.sleep(0.5)
            batch_output = get_submission_batch(token_list)
        
        # Decoding Before Giving to JsonResponse
        decoded_expected_outputs = []
        decoded_stderrors = []
        decoded_stdins = []
        decoded_stdouts = []
        accepted_lst = []
        
        for submission in batch_output["submissions"]:
            decoded_stdins.append(base64.b64decode(submission["stdin"]).decode())
            decoded_stdouts.append(base64.b64decode(submission["stdout"]).decode()) if submission.get("stdout") else None
            decoded_stderrors.append(base64.b64decode(submission["stderr"]).decode() if submission.get("stderr") else None)
            decoded_expected_outputs.append(base64.b64decode(submission["expected_output"]).decode())
            accepted_lst.append(submission["status"]["description"] if submission["status_id"] == 3 else "Wrong Answer")
        
        public_accepted_lst = accepted_lst[:len(question["Public_Test_Cases"])]
        private_accepted_lst = accepted_lst[len(question["Public_Test_Cases"]):]
        
        total_test_cases = len(accepted_lst)
        passed_test_cases = sum([1 for accepted in accepted_lst if accepted == "Accepted"])
        
        return JsonResponse({"decoded_expected_outputs": decoded_expected_outputs,
                             "decoded_stderrors": decoded_stderrors,
                             "decoded_stdins": decoded_stdins,
                             "decoded_stdouts": decoded_stdouts,
                             "public_accepted_lst": public_accepted_lst,
                             "private_accepted_lst": private_accepted_lst,
                             "total_test_cases": total_test_cases,
                             "passed_test_cases": passed_test_cases}, status=200)
        
    else:
        return JsonResponse({"error": "Invalid request."}, status=400)
    
@csrf_exempt
def submit_code(request):
    """
    This function is responsible for submitting the code to the database and also save the 
    number of test cases passed for each submission.
    Parameters:
    request (HttpRequest): The HTTP request object.
    Returns:
    JsonResponse: A JSON response with the execution result.
    """
    if request.method == "POST":
        data = json.loads(request.body)
        submissions = data["submissions"]
        flags = data['flags']  # flags can be None if not provided in the request
        
        user = request.user  # the logged-in user
        submitted_time = timezone.now()  # you can record submission time once
        
        try:
            if not flags:
                flags = 0
        except UnboundLocalError:
            flags = 0  # initialize flags to 0 if it's not defined before
        
        # Loop over each submitted question
        for question_id_str, submission in submissions.items():
            question_id = int(question_id_str)  # because keys are strings ('1', '5', etc.)

            source_code = submission["source_code"]
            language_id = submission["language_id"]
            total_test_cases = submission["total_test_cases"]
            passed_test_cases = submission["passed_test_cases"]

            # Fetch the QuestionBank object
            try:
                problem = QuestionBank.objects.get(id=question_id)
            except QuestionBank.DoesNotExist:
                continue  # if question not found, skip saving it

            # Save or Update the CodingResult
            coding_result, created = CodingResult.objects.update_or_create(
                user=user,
                problem=problem,
                defaults={
                    'submitted_code': source_code,
                    'submitted_time': submitted_time,
                    'language_id': language_id,
                    'total_test_cases': total_test_cases,
                    'test_cases_passed': passed_test_cases,
                    'flags_raised': flags,
                }
            )
        
        redirect_url = reverse('get_result')
        
        return JsonResponse({"redirect_url": redirect_url})
    return JsonResponse({"error": "Invalid request."}, status=400)
    
@login_required
def get_result(request):
    """
        Render the coding_result.html page with candidate's coding test results.
    """
    user = request.user
    coding_results_qs = CodingResult.objects.filter(user=user)
    
    # Prepare Coding result context
    coding_results = []
    problems_passed = 0

    for result in coding_results_qs:
        passed = result.test_cases_passed == result.total_test_cases
        if passed:
            problems_passed += 1
        coding_results.append({
            "problem_name": result.problem.problem_name,
            "test_cases_passed": result.test_cases_passed,
            "total_test_cases": result.total_test_cases,
            "submitted_time": localtime(result.submitted_time).strftime("%Y-%m-%d %H:%M"),
            "passed": passed
        })

    context = {
        "coding_results": coding_results,
        "total_attempted": coding_results_qs.count(),
        "problems_passed": problems_passed,
    }
    return render(request, 'automated_resume/coding_result.html', context)