import argparse
import os
import sys
import typing
import zipfile
import time
from typing import Any, Dict, Optional
import requests
from datetime import datetime

API_HOST = "http://localhost:3000"

CLIENT_ID = os.getenv("GLADOS_CLIENT_ID")

DEVICE_CODE_URL = "https://github.com/login/device/code"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
VIEW_EXPERIMENT_URL = "http://localhost:3000/api/experiments/queryExp"
AUTH_URL = "http://localhost:3000/api/auth/tokenAuth/token"
EXPERIMENT_STATUS_URL = "http://localhost:3000/api/experiments/status"

EX_UNKNOWN = -2
EX_PARSE_ERROR = -1
EX_SUCCESS = 0
EX_INVALID_TOKEN = 1
EX_NOTFOUND = 2
EX_INVALID_EXP_FORMAT = 3

class RequestManager(object):
    def __init__(self):
        pass  # Initialization code for RequestManager
    
    def generate_token(self) -> Dict[str, Any]:
        device_code_url = DEVICE_CODE_URL
        scope = "read:user user:email"
        data_GitHub = {"client_id": CLIENT_ID, "scope": scope}
        try:
            res = requests.post(device_code_url, data=data_GitHub, headers={"Accept": "application/json"}, timeout=20)
        except requests.RequestException as error:
            return {"access_token": None, "error": f'{error}'}
        data = res.json()
        device_code = data['device_code']
        expire_time = data['expires_in']
        interval = data['interval']
        user_code = data['user_code']
        current_time = 0
        print(f"Please enter the following user code: {user_code} at the following address: {data['verification_uri']}")
    
        while (current_time < expire_time):
            access_token_url = ACCESS_TOKEN_URL
            data_GitHub = {"client_id":CLIENT_ID, "device_code": device_code, "grant_type": "urn:ietf:params:oauth:grant-type:device_code"}
            time.sleep(interval)
            res = requests.post(access_token_url, data=data_GitHub, headers={"Accept": "application/json"}, timeout=interval)
            current_time += interval
            response = res.json()
            if "access_token" in response:
                access_token = response['access_token']
                return {"access_token": access_token, "error": None}
            elif  response.get("error") == "authorization_pending":
                continue
            elif response.get("error") == "slow_down":
                interval +=5
            elif response.get("error") == "incorrect_client_credentials":
                return {"access_token": None, "error": "Incorrect client credentials"}
            elif response.get("error") == "expired_token":
                return {"access_token": None, "error": "Token is expired"}
            elif response.get("error") == "access_denied":
                return {"access_token": None, "error": "Access is denied"}
            elif response.get("error") == "incorrect_device_code":
                return {"access_token": None, "error": "Incorrect device code"}
        return {"access_token": None, "error": "Time out occurred"}   
        # Implementation for generating a device token for authorization   
    
    def authenticate(self, token: str) -> Dict[str, typing.Any]:
        try:
            user_token = {"token": token}
            res = requests.post(AUTH_URL, verify=False, json=user_token, timeout=5)
            response = res.json()
            self.token = token
            return {"uid": response["_id"], "error": None}
        except requests.RequestException as error:
            return {"uid": None, "error": f'{error}'}
        # Implementation for authenticating with the provided token
    
    def upload_and_start_experiment(self, experiment_path: str) -> Dict[str, typing.Any]:
        return EX_SUCCESS  # Implementation for uploading and starting an experiment
    
    def query_experiments(self, experiment_name: str, token: str) -> Dict[str, typing.Any]:
        experiment_req_json = {
            "token": token,
            "exp_title": experiment_name
        }
        try:
            res = requests.post(VIEW_EXPERIMENT_URL, verify=False, json=experiment_req_json, timeout=20)
        except requests.RequestException as error:
            perror(f'{error}')
        return res.json()
    
    def get_experiment_status(self, experiment_id: str, token: str) -> Dict[str, typing.Any]:
        experiment_req_json = {
            "token": token,
            "eid": experiment_id
        }
        try:
            res = requests.post(EXPERIMENT_STATUS_URL, verify=False, json=experiment_req_json, timeout=20)
        except requests.RequestException as error:
            perror(f'{error}')
        return res.json()
    
    def download_experiment_results(self, experiment_id: str, destination_path: str) -> Dict[str, typing.Any]:
        pass  # Implementation for downloading experiment results
    
def perror(*args, **kwargs) -> None:
    """Prints to stderr."""
    print(*args, file=sys.stderr, **kwargs)
    
def generate_token(request_manager: RequestManager) -> str:
    result = request_manager.generate_token()
    access_token = result["access_token"]
    error = result["error"]
    if error is None:
        print(f"Your token is: {access_token}")
        return access_token
    else:
        perror(f'{result["error"]}')

def validate_token(request_manager: RequestManager, token: str) -> bool:
    """Validates the provided authentication token."""
    result = request_manager.authenticate(token)
    return result['error'] is None

def upload_and_start_experiment(request_manager: RequestManager, experiment_path: str) -> int:
    """Uploads and starts an experiment given the path to the experiment ZIP file."""
    if not os.path.isfile(experiment_path):
        perror(f"error: Experiment file '{experiment_path}' not found.")
        return EX_NOTFOUND
    validation_error = validate_experiment_file(experiment_path)
    if validation_error is not None:
        perror(f"error: {validation_error}")
        return EX_INVALID_EXP_FORMAT

    results = request_manager.upload_and_start_experiment(experiment_path)
    if not results.get('success', False):
        perror(f"error: backend: {results.get('error')}")
        return EX_INVALID_EXP_FORMAT if results['error'] == 'bad_format' else EX_UNKNOWN
    
    print(f"Experiment started successfully (ID = {results['exp_id']}).")
    return EX_SUCCESS

def get_experiment_status(request_manager: RequestManager, eid):
    results = request_manager.get_experiment_status(eid, get_token())
    if not results.get('success', False):
        if results['error'] == 'not_found':
            perror(f"error: Experiment '{eid}' not found.")
            return EX_NOTFOUND
        else:
            perror(f"error: backend: {results.get('error')}")
            return EX_UNKNOWN
    print(f"Status: {results['status']} ({results['current_permutation']}/{results['total_permutations']} permutations)")
    return EX_SUCCESS

def query_experiments(request_manager: RequestManager, title: str):
    results = request_manager.query_experiments(title, get_token())
    print("Matches:")
    for index, match in enumerate(results["matches"]):
        s = match["startedAtEpochMillis"] / 1000.0
        time_started = datetime.fromtimestamp(s)
        print("***********************************************")
        print(f"Experiment {index + 1}: {match['name']}")
        print("***********************************************")
        print(f"ID: {match['id']}")
        print(f"Status: {match['status']}")
        print(f"Time Started: {time_started}\n")
    return EX_SUCCESS

def validate_experiment_file(filepath: str) -> Optional[str]:
    if not zipfile.is_zipfile(filepath):
        return f"'{filepath}' is in an invalid format."
    with zipfile.ZipFile(filepath, 'r') as zf:
        if 'manifest.yaml' not in zf.namelist():
            return f"'{filepath}' is missing 'manifest.yaml'."
    return None

def store_token(token: str) -> str:
    with open(".token.glados", "w") as token_file:
        token_file.write(token)
    return "Successfully stored authentication token!"

def get_token() -> str:
    with open(".token.glados", "r") as token_file:
        token = token_file.read().strip()
    return token

def parse_args(request_manager: RequestManager, args: Optional[typing.Sequence[str]]=None, stdout = sys.stdout, stderr = sys.stderr) -> int:
    
    # Save original stdout and stderr
    _out, _err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = stdout, stderr
    
    parser = argparse.ArgumentParser(
        prog="GLADOS CLI",
        description="The command line interface for GLADOS.")
    
    #TODO: How to get no argument generate option without having the awkward store_true argument
    parser.add_argument('--generate',  '-g', action='store_true', help='Generate or update token to use.')
    parser.add_argument('--token',  '-t', type=str, help='Authentication token to use.')
    parser.add_argument('--upload', '-z', type=str, help='Upload a ZIP file. Cannot be used with -s, -q, or -d.')
    parser.add_argument('--query',  '-q', type=str, help='Search for experiments with the specified name. Cannot be used with -z, -s, or -d.')
    parser.add_argument('--status', '-s', type=str, help='View the status of an experiment. Cannot be used with -z, -q, or -d.')
    parser.add_argument('--download', '-d', type=str, help='Download the results of a completed experiment. Cannot be used with -z, -q, or -s.')
    
    parsed = parser.parse_args(args)

    #TODO: Change logic to passing through token to each method instead of reading each time
    if not parsed.generate and not parsed.token:
        if not os.path.exists(".token.glados"):
            perror("error: Please provide an authentication token using '-t <token>' or by creating a file named '.token.glados'.")
            return EX_INVALID_TOKEN
        # else:
        #     parsed.token = get_token()
    
    # Check that exactly one of -z, -q, or -s is provided
    if not exactly_one([parsed.generate, parsed.upload, parsed.query, parsed.status, parsed.download, parsed.token]):
        perror("error: Exactly one of -g, -t, -z, -q, -s, or -d must be provided.")
        return EX_PARSE_ERROR
    
    # TODO: Does this serve a purpose when we have to reauthenticate to get UID at each step?
    # if not request_manager.authenticate(parsed.token):
    #     perror("error: Cannot authenticate token - check your internet connection and token.")
    #     return EX_INVALID_TOKEN
    
    # Authentication successful, proceed with requested operation
    result = EX_SUCCESS
    if parsed.generate:
        result = generate_token(request_manager)
    if parsed.token:
        result = store_token(parsed.token)
    if parsed.upload:
        result = upload_and_start_experiment(request_manager, parsed.upload)
    if parsed.status:
        result = get_experiment_status(request_manager, parsed.status)
    if parsed.query:
        result = query_experiments(request_manager, parsed.query)
    
    # Restore original stdout and stderr
    sys.stdout, sys.stderr = _out, _err
    return result
    


def exactly_one(args : typing.Sequence[str]) -> bool:
    """Returns True if exactly one argument in args is not None."""
    count = 0
    for arg in args:
        if arg is not None and arg is not False:
            count += 1
    return count == 1
    

def main():
    parse_args(RequestManager()) 
    

if __name__ == "__main__":
    main()
    
    
