# To run this test script, ensure that you are first authenticated with the CLI,
# as it expects there is a valid token stored in the .token.glados file.
# There should also be no existing experiment with the same name as the one 
# specified in the manifest.yml file of the experiment being tested, as this test 
# script expects to create a new experiment and will fail if an experiment with the 
# same name already exists.

import os
import subprocess
import time
import glob
import pandas as pd

GLADOS_CLI_PATH = "glados_cli.py"  # glados_cli.py file path from root of the repository, adjust if necessary
CSV_FILE_PATH = "tests/integration/data/addNumbersExpected.csv"  # csv file path from root of the repository, adjust if necessary
EXPERIMENT_FILE = "tests/integration/data/addNumbers.py" # executable file path from root of the repository, adjust if necessary

def compare_result_files(file1, file2):
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)
    
    if df1.equals(df2):
        print("Test passed: The downloaded results match the expected results.")
    else:
        print("Test failed: The downloaded results do not match the expected results.")
        
def compare_filtered(s1, s2):
    def filter_lines(text):
        skip_prefixes = ("ID:", "Time Started:")
        return [line.strip() for line in text.splitlines() 
                if not line.strip().startswith(skip_prefixes)]

    return filter_lines(s1) == filter_lines(s2)

def teardown():
    for f in glob.glob("Test_AddNums*"):
        os.remove(f)
        
def start_test_printout(test_name):
    print(f"\n{'='*10} Starting {test_name} {'='*10}\n")
    
def end_test_printout(test_name):
    print(f"\n{'='*10} Finished {test_name} {'='*10}\n")
        
def experiment_creation_test():
    start_test_printout("Experiment Creation Test")
    try:
        result = subprocess.run(["python", GLADOS_CLI_PATH, "-z", EXPERIMENT_FILE], capture_output=True, text=True)
        print("Output:\n", result.stdout.strip())
        experiment_id = result.stdout.strip().split('=')[1].strip(' ).')
        if result.stderr:
            print("Errors:\n", result.stderr.strip())
        else:
            print(f"Test passed: Experiment created successfully.")
    except Exception as e:
        print(f"Test failed with error: {e}")
        
    end_test_printout("Experiment Creation Test")
    
    return experiment_id

def experiment_download(experiment_id):
    start_test_printout("Experiment Download Test")
    try:
        result = subprocess.run(["python", GLADOS_CLI_PATH, "-da", experiment_id], capture_output=True, text=True)
        print("Output:\n", result.stdout.strip())
        if result.stderr:
            print("Errors:\n", result.stderr.strip())  
        else:
            print("Test passed: Experiment artifacts downloaded successfully.")
    except Exception as e:
        print(f"Test failed with error: {e}")
    end_test_printout("Experiment Download Test")

def experiment_download_all(experiment_id):
    start_test_printout("Experiment Download All Test")
    try:
        result = subprocess.run(["python", GLADOS_CLI_PATH, "-da", experiment_id], capture_output=True, text=True)
        print("Output:\n", result.stdout.strip())
        if result.stderr:
            print("Errors:\n", result.stderr.strip())  
        else:
            print("Test passed: Experiment artifacts downloaded successfully.")
    except Exception as e:
        print(f"Test failed with error: {e}")
    end_test_printout("Experiment Download All Test")
        
def experiment_query():
    start_test_printout("Experiment Query Test")
    try:
        result = subprocess.run(["python", GLADOS_CLI_PATH, "-q", "Test AddNums"], capture_output=True, text=True)
        print("Output:\n", result.stdout.strip())
        if result.stderr:
            print("Errors:\n", result.stderr.strip())  
        else:
            # Compare expected results with actual results from query output
            expected_output = "Matches:\n***********************************************\nExperiment 1: Test AddNums\n*********************************************** \nID: 69d342be8bb268f5b2add93d\nTags: ['Test', 'AddNums']\nStatus: COMPLETED\nTime Started: 2026-04-06 01:21:14.109000\nTrials: 100/100 Completed"
            if compare_filtered(result.stdout.strip(), expected_output):
                print("\nTest passed: The query output matches the expected output.")
            else:
                print("\nTest failed: The query output does not match the expected output.")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
    end_test_printout("Experiment Query Test")

def main():
    experiment_id = experiment_creation_test()

    time.sleep(10) # Wait for a moment to ensure the experiment is fully registered before attempting to download
    
    experiment_download(experiment_id)
    experiment_download_all(experiment_id)
    experiment_query()

    teardown()

if __name__ == "__main__":
    main()