# To run this test suite, ensure that you are first authenticated with the CLI,
# as it expects there is a valid token stored in the .token.glados file.
# There should also be no existing experiment with the same name as the one 
# specified in the manifest.yml file of the experiment being tested, as this test 
# suite expects to create a new experiment and will fail if an experiment with the 
# same name already exists.

import subprocess
import time
import pandas as pd

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

print("Starting experiment creation test...\n")
try:
    result = subprocess.run(["python", "glados_cli.py", "-z", "test_submission_results/test_add_nums/addNumbers.py"], capture_output=True, text=True)
    print("Output:\n", result.stdout.strip())
    experiment_id = result.stdout.strip().split('=')[1].strip(' ).')
    if result.stderr:
        print("Errors:\n", result.stderr.strip())
except Exception as e:
    print(f"Test failed with error: {e}")
    
print("\nExperiment creation test completed.")

time.sleep(10) # Wait for a moment to ensure the experiment is fully registered before attempting to download

print("\nStarting experiment download test...\n")
try:
    result = subprocess.run(["python", "glados_cli.py", "-d", experiment_id], capture_output=True, text=True)
    print("Output:\n", result.stdout.strip())
    if result.stderr:
        print("Errors:\n", result.stderr.strip())  
    else:
        words = result.stdout.strip().split()
        file_name = next((w for w in words if w.endswith('.csv')), None)
        compare_result_files("test_submission_results/test_add_nums/addNumbersExpected.csv", file_name)
except Exception as e:
    print(f"Test failed with error: {e}")
    
print("\nStarting experiment query test...\n")
try:
    result = subprocess.run(["python", "glados_cli.py", "-q", "Test AddNums"], capture_output=True, text=True)
    print("Output:\n", result.stdout.strip())
    if result.stderr:
        print("Errors:\n", result.stderr.strip())  
    else:
        # Compare expected results with actual results from query output
        expected_output = "Matches:\n***********************************************\nExperiment 1: Test AddNums\n*********************************************** \nID: 69d342be8bb268f5b2add93d\nTags: ['Neural Network', 'ECE497']\nStatus: COMPLETED\nTime Started: 2026-04-06 01:21:14.109000\nTrials: 100/100 Completed"
        if compare_filtered(result.stdout.strip(), expected_output):
            print("\nTest passed: The query output matches the expected output.")
        else:
            print("\nTest failed: The query output does not match the expected output.")
        print("\nFinished querying experiment.")
except Exception as e:
    print(f"\nTest failed with error: {e}")

