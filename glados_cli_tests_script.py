# To run this test suite, ensure that you are first authenticated with the CLI,
# as it expects there is a valid token stored in the .token.glados file.

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
