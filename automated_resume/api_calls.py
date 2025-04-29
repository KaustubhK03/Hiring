import requests
import os
import json
from dotenv import load_dotenv
load_dotenv()

def get_available_languages():
    """
    This function sends a GET request to the server to retrieve the list of available programming languages.
    Returns:
    dict: A dictionary containing the response data from the server.
    """
    url = os.getenv("DOMAIN") + "/languages"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers)
    
    return response.json()

def create_submission(language_id, source_code, stdin):
    """
    Creates new submission. Created submission waits in queue to be processed. On successful creation, 
    you are returned submission token which can be used to check submission status.
    If submission’s source_code, stdin or expected_output contains non printable characters, 
    or characters which cannot be sent with JSON, then set base64_encoded parameter to true and 
    send these attributes Base64 encoded. Your responsibility is to encode each of mentioned attributes 
    (source_code, stdin and expected_output) even if just one of them contains non printable characters. 
    By default, this parameter is set to false and Judge0 assumes you are sending plain text data.
    By default you are returned submission token on successful submission creation. 
    With this token you can check submission status. Instead of checking submission status by 
    making another request, you can set the wait query parameter to true which will enable you to 
    get submission status immediately as part of response to the request you made. Please note that this 
    feature may or may not be enabled on all Judge0 hosts. So before using this feature please check 
    configuration of Judge0 you are using. On an official Judge0 this feature is not enabled.
    
    This is used for creating a custom submission.i.e when the user gives custom input.
    
    Request: POST
    Parameters: language_id, source_code, stdin
    Returns: token of the created submission.
    """
    url = os.getenv("DOMAIN") + "/submissions/?base64_encoded=true&wait=false"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "source_code": source_code,
        "language_id": language_id,
        "stdin": stdin,
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()["token"]

def get_submission(token):
    """
    Returns details about submission.
    
    Just like in create submission you can receive Base64 encoded data for every text type attribute. 
    By default, this parameter is set to false and Judge0 will send you raw data.

    By default Judge0 is sending 8 attributes for submission. By sending fields query parameter you can 
    specify exactly which attributes you want from Judge0. Special value * will return all available attributes.
    
    This function returns details about a the custom input submission from the user.
    
    Request: GET
    Parameters: token
    Returns: details about the custom input submission.
    """
    url = os.getenv("DOMAIN") + "/submissions/" + token + "?base64_encoded=true&fields=stdout,time,memory,token,compile_output,message,status,language_id"
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    return response.json()

def create_submission_batch(source_code, language_id, stdin_list, expected_out_lst):
    """
    Create multiple submissions at once. Used for running multiple test cases in a single submission. 
    Returns a list of tokens for each submission.
    
    Request: POST
    Parameters: list of submissions
    Returns: a list of tokens for each submission in that order of submissions.
    """
    url = os.getenv("DOMAIN") + "/submissions/batch?base64_encoded=true"
    headers = {
        "Content-Type": "application/json"
    }
    submissions = []
    for i in range(len(stdin_list)):
        submission = {
            "language_id": language_id,
            "source_code": source_code,
            "stdin": stdin_list[i],
            "is_public": True if i < 2 else False  # First 2 are public
        }
        if i <= len(expected_out_lst):
            submission["expected_output"] = expected_out_lst[i]
        submissions.append(submission)

    response = requests.post(url, json={"submissions": submissions}, headers=headers)
    return response.json()

def get_submission_batch(token_list):
    """
    Returns details about multiple submissions.
    
    Request: GET
    Parameters: list of tokens
    Returns: a list of details about each submission
    """
    # exit_code,exit_signal,expected_output,language_id,source_code,status,status_id,stderr,stdin,stdout,time,token
    url = os.getenv("DOMAIN") + "/submissions/batch?" + "tokens=" + ",".join(token_list) + "&base64_encoded=true&fields=exit_code,exit_signal,expected_output,language_id,source_code,status,status_id,stderr,stdin,stdout,time,token"
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    return response.json()