import os
import json
import re
import docx2txt
import logging
from dotenv import load_dotenv
import google.generativeai as genai
from pdfminer.high_level import extract_text
from django.conf import settings
import openpyxl
from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.contrib.auth.forms import PasswordResetForm
from .forms import CustomSetPasswordForm
from .models import AdminSetting

# get logger
logger = logging.getLogger(__name__)


load_dotenv()   # loading the environment variables

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = genai.GenerativeModel('gemini-2.0-flash')

class CustomPasswordResetView(PasswordResetView):
    email_template_name = 'automated_resume/password_reset_email.html'
    subject_template_name = 'automated_resume/password_reset_subject.txt'
    template_name = 'automated_resume/reset_password.html'
    success_url = reverse_lazy('reset_password_done')
    form_class = PasswordResetForm


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = CustomSetPasswordForm
    template_name = 'automated_resume/reset_password_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


def extract_text_from_resume(pdf_path):
    try:
        # for pdf files
        text = extract_text(pdf_path)
    except:
        # for docs file
        text = docx2txt.process(pdf_path)
    return text


def get_required_jd_path(JD_LIST, JD_NEEDED):
    for index, jd in enumerate(JD_LIST):
        jd = jd.replace("_", " ").replace(".pdf", "").lower()
        if JD_NEEDED.lower() in jd:
            return f"{settings.PATH_TO_JDS}/{JD_LIST[index]}"
        
        
def ats_score(resume_text, jd_text):
    input_prompt = f"""
    Hey Act Like a skilled or very experienced ATS(Application Tracking System) with a deep 
    understanding of the tech field, software engineering, data science, data analysis and 
    big data engineering and full stack engineering and Devops engineering.
    
    Evaluate the resume based on the given job description. You must consider the job market is very competitive and you should provide the best 
    assistance for improving their resumes. Assign the percentage Matching based on the 
    Job description and the missing keywords with high accuracy.  
    
    Please return a JSON response with **EXACTLY** the following format. Also, use only single quotes('') in keys and values. Use Proper JSON Format:
    {{"JD_Match":"XX%", "MissingKeywords":["keyword1", "keyword2"], "Profile_Summary":"Your detailed feedback"}}

    resume:{resume_text}
    description:'{jd_text}'
    
    Only output a valid JSON object. Do not include extra text, explanations, or markdown or else my program will crash.
    """
    response = model.generate_content(input_prompt)
    try:
        if response.text is None or response.candidates[0].finish_reason == "RECITATION":
            ats_score(resume_text, jd_text)
        else:
            return response.text
    except ValueError:
        ats_score(resume_text, jd_text)

def extract_skills(pdf_path):
    resume_text = extract_text_from_resume(pdf_path)
    prompt1 = f'''
            You are an AI bot designed to act as a professional for parsing resumes. You are given with a resume, read the 
            resume thoroughly and get a knowledge of candidate's experience and select a category for user from these 5
            levels: beginner, intermediate, advanced, advance pro, or expert without any clarification or explanation, your job is to extract 
            the following information from the text based resume:
            1. Experience level.
            2. technical skills.
            Give the output in the following format:
            <Experience level>
            <Technical skills(In the form of a csv)>
            The resume text is:
            {resume_text}
            '''

    response = model.generate_content(prompt1)
    thank_you()
    global experience_level
    try:
        if response.text is None or response.candidates[0].finish_reason == "RECITATION":
            extract_skills(pdf_path)
        intermediate_list = response.text.split(",")
        experience_level = ""
        for char in intermediate_list[0]:
            if char == "\n":
                break
            experience_level += char
        intermediate_string = ", ".join(intermediate_list)
        global skills_str
        skills_str = intermediate_string.replace(experience_level, "")
        return experience_level, skills_str
    except ValueError:
        extract_skills(pdf_path=pdf_path)


def extract_question(extracted_skills, experience_level):
    admin_settings_object = AdminSetting.objects.first() or AdminSetting()
    prompt2 = f'''
            You are an AI assistant designed to help with interview preparation. 
        You will be provided with skills from a candidate's resume. Now based on the provided skills, and his level
        of experience which is {experience_level}, prepare a technical questionnaire for the candidate containing {admin_settings_object.NUMBER_OF_QUIZ_QUESTIONS} 
        Multiple Choice questions with precisely 4 options for each question. Do not give less than 4 options or even
        more than 4 options. The number of options should be precisely 4. Mark the correct answer in the options 
        itself with a ** or (Correct). The skills are: {extracted_skills}.
        for example if one of the skills in the resume is Python, then the response should be in the following format:
        **1. Which of the following is not a core data type in python?** (This indicates the start of each question, 
        i.e start each question with '**')
        a) Bool
        b) String (Correct) --> this marks the answer in the options itself
        c) Int
        d) Char
        Also note that here the number of options are 4. PLease do not give options more than 4.
        As it is the first round: do not give any coding questions for example:
        **2. What is the output of the following Python code?**
        ```python
        print(10 / 3)
        ```
        a) 3
        b) 3.33
        c) 3.3333333333333335 **(Correct)**
        d) 3.0
        Also don't mention the topic of the following question. Example:
        **Network Deployment and Operation** (Do not mention this line, if you do then do not add **)
        1. Which of the following protocols is primarily used for routing packets on the internet?
            a) TCP
            b) IP (Correct)
            c) HTTP
            d) DNS
        Just before starting the question add the following lines for instructions and the level of the candidate:
        ' ## Technical Questionnaire for Intermediate Level Candidate\n
        **Instructions:** Please select the best answer for each question.'
        '''

    questions = model.generate_content(prompt2)
    thank_you()

    if questions.candidates[0].finish_reason == "RECITATION":
        extract_question(skills_str, experience_level)
    try:
        if questions.text is not None:
            return questions.text
    except:
        try:
            if questions.parts[0].text is not None:
                return questions.parts[0].text
        except:
            extract_question(skills_str, experience_level)


def thank_you():
    prompt = "Thank you, Good Job!"
    res = model.generate_content(prompt)
    try:
        if res.text is None or res.candidates[0].finish_reason == "RECITATION":
            thank_you()
        return res.text
    except ValueError:
        print(res.prompt_feedback)

def extract_dict_from_ats_response(response_string):
    """
    Extracts a dictionary from a string formatted as a JSON-like dictionary.

    Args:
        response_string: The string containing the dictionary.

    Returns:
        A dictionary if extraction is successful, None otherwise.
    """
    response_string = response_string.replace("```", "").replace("json", "").replace("JSON", "").replace("Json", "")
    response_string = json.loads(response_string)
    return response_string

def save_to_excel(data):
    file_path = 'resumes.xlsx'
    if os.path.exists(file_path):
        workbook = openpyxl.load_workbook(file_path)
    else:
        workbook = openpyxl.Workbook()
        workbook.active.append(['Name', 'Email', 'Phone', 'Date of Birth', 'Resume Path'])

    sheet = workbook.active
    sheet.append(data)
    workbook.save(file_path)


def parse_questions(questions_text):
    questions_dict = {}
    lines = questions_text.split('\n')
    question = None
    options = {}

    for line in lines:
        if line.startswith("**") and not line.startswith("**Instructions"):
            if question and options:
                questions_dict[question] = options
            question = line.split("**")[1].strip()
            options = {}
        elif line.startswith("Answer:"):
            answer = line.split("Answer:")[1].strip()
            for option in options:
                if options[option] == answer:
                    options[option] = 1
                else:
                    options[option] = 0
        else:
            if line.strip() and ")" in line:
                option, text = line.split(")", 1)
                options[option.strip()] = text.strip()

    if question and options:
        questions_dict[question] = options
    return questions_dict


def extract_correct_answers(questions_dict):
    answer_dict = {}
    # Check if "Answer Key:" exists in the dictionary
    for question, option_dict in questions_dict.items():
        for option, text in option_dict.items():
            if text.startswith("**") or text.endswith("**") or "**" in text or "✅" in text or "(Correct)" in text:
                answer_dict[question] = (text.replace("**", "").replace("✅", "").replace("✔️", "").
                                         replace(" (Correct)", "").replace(" **(Correct)**", "").
                                         replace("**(Correct)", "").replace("(Correct)**", "").replace("(Correct)", ""))
                option_dict[option] = (text.replace("**", "").replace("✅", "").replace("✔️", "").
                                       replace(" (Correct)", "").replace(" **(Correct)**", "").
                                       replace("**(Correct)", "").replace("(Correct)**", "").replace("(Correct)", ""))
                if "(Correct)" in text:
                    option_dict[option] = text.replace("(Correct)", "")
                elif "**(Correct)**" in text:
                    option_dict[option] = text.replace("**(Correct)**", "")
    return answer_dict, questions_dict

