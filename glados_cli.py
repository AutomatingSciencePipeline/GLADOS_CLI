import argparse
import os
import sys
import typing
import zipfile

HOST = "http://localhost:5050"

EX_UNKNOWN = -2
EX_PARSE_ERROR = -1
EX_SUCCESS = 0
EX_INVALID_TOKEN = 1
EX_NOTFOUND = 2
EX_INVALID_EXP_FORMAT = 3

class RequestManager(object):
    def __init__(self):
        pass  # Initialization code for RequestManager
    
    def authenticate(self, token: str) -> bool:
        pass  # Implementation for authenticating with the provided token
    
    def upload_and_start_experiment(self, experiment_path: str) -> dict[str, typing.Any]:
        return EX_SUCCESS  # Implementation for uploading and starting an experiment
    
    def query_experiments(self, experiment_name: str) -> dict[str, typing.Any]:
        pass  # Implementation for querying experiments by name
    
    def get_experiment_status(self, experiment_type: str) -> dict[str, typing.Any]:
        pass  # Implementation for viewing the status of an experiment
    
    def download_experiment_results(self, experiment_id: str, destination_path: str) -> dict[str, typing.Any]:
        pass  # Implementation for downloading experiment results
    
def perror(*args, **kwargs) -> None:
    """Prints to stderr."""
    print(*args, file=sys.stderr, **kwargs)
    
def validate_token(token: str) -> bool:
    """Validates the provided authentication token."""
    # Placeholder implementation for token validation
    return token == "valid_token"

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

def get_experiment_status(request_manager, parsed):
    results = request_manager.get_experiment_status(parsed.status)
    if not results.get('success', False):
        if results['error'] == 'not_found':
            perror(f"error: Experiment '{parsed.status}' not found.")
            return EX_NOTFOUND
        else:
            perror(f"error: backend: {results.get('error')}")
            return EX_UNKNOWN
    print(f"Status: {results['status']} ({results['current_permutation']}/{results['total_permutations']} permutations)")
    return EX_SUCCESS

def validate_experiment_file(filepath: str) -> str | None:
    if not zipfile.is_zipfile(filepath):
        return f"'{filepath}' is in an invalid format."
    with zipfile.ZipFile(filepath, 'r') as zf:
        if 'manifest.yaml' not in zf.namelist():
            return f"'{filepath}' is missing 'manifest.yaml'."
    return None

def parse_args(request_manager: RequestManager, args: typing.Sequence[str] | None=None, stdout = sys.stdout, stderr = sys.stderr) -> int:
    
    # Save original stdout and stderr
    _out, _err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = stdout, stderr
    
    parser = argparse.ArgumentParser(
        prog="GLADOS CLI",
        description="The command line interface for GLADOS.")
    parser.add_argument('--token',  '-t', type=str, help='Authentication token to use. Required.')
    parser.add_argument('--upload', '-z', type=str, help='Upload a ZIP file. Cannot be used with -s, -q, or -d.')
    parser.add_argument('--query',  '-q', type=str, help='Search for experiments with the specified name. Cannot be used with -z, -s, or -d.')
    parser.add_argument('--status', '-s', type=str, help='View the status of an experiment. Cannot be used with -z, -q, or -d.')
    parser.add_argument('--download', '-d', type=str, help='Download the results of a completed experiment. Cannot be used with -z, -q, or -s.')
    
    parsed = parser.parse_args(args)
    
    if not parsed.token:
        if not os.path.exists(".token.glados"):
            perror("error: Please provide an authentication token using '-t <token>' or by creating a file named '.token.glados'.")
            return EX_INVALID_TOKEN
        with open(".token.glados", "r") as token_file:
            parsed.token = token_file.read().strip()
    
    # Check that exactly one of -z, -q, or -s is provided
    if not exactly_one([parsed.upload, parsed.query, parsed.status, parsed.download]):
        perror("error: Exactly one of -z, -q, -s, or -d must be provided.")
        return EX_PARSE_ERROR
    
    if not request_manager.authenticate(parsed.token):
        perror("error: Cannot authenticate token - check your internet connection and token.")
        return EX_INVALID_TOKEN
    
    # Authentication successful, proceed with requested operation
    result = EX_SUCCESS
    if parsed.upload:
        result = upload_and_start_experiment(request_manager, parsed.upload)
    if parsed.status:
        result = get_experiment_status(request_manager, parsed)
    
    # Restore original stdout and stderr
    sys.stdout, sys.stderr = _out, _err
    return result
    


def exactly_one(args : list[str]) -> bool:
    """Returns True if exactly one argument in args is not None."""
    count = 0
    for arg in args:
        if arg is not None:
            count += 1
    return count == 1
    

def main():
    parse_args(RequestManager()) 
    

if __name__ == "__main__":
    main()