import unittest
import subprocess
import os
import glob
import time
import pandas as pd

GLADOS_CLI_PATH = "glados_cli.py"
CSV_FILE_PATH = "tests/integration/data/addNumbersExpected.csv"
EXPERIMENT_FILE = "tests/integration/data/addNumbers.py"

class TestGladosCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Clean up environment before starting tests."""
        cls.experiment_id = None
        cls._cleanup_files()

    @staticmethod
    def _cleanup_files():
        for f in glob.glob("Test_AddNums*"):
            os.remove(f)

    def _run_cli(self, args):
        cmd = ["python", GLADOS_CLI_PATH] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result

    def _assert_in_output(self, expected, actual, message=None):
        self.assertIn(expected, actual, message or f"Expected '{expected}' not found in output.")

    def _filter_output(self, text):
        # ID and Time Started lines will vary, so they must be ignored
        skip_prefixes = ("ID:", "Time Started:")
        return "\n".join([
            line.strip() for line in text.splitlines() 
            if not line.strip().startswith(skip_prefixes)
        ])

    def test_01_experiment_creation(self):
        result = self._run_cli(["-z", EXPERIMENT_FILE])
        
        self.assertEqual(result.returncode, 0, f"CLI exited with error: {result.stderr}")
        self._assert_in_output("Experiment started successfully", result.stdout)
        
        # Parse and store the experiment ID for subsequent tests
        try:
            parts = result.stdout.strip().split('=')
            TestGladosCLI.experiment_id = parts[1].strip(' ).').split()[0]
        except (IndexError, AttributeError):
            self.fail("Failed to parse Experiment ID from output.")

    def test_02_experiment_download(self):
        if not self.experiment_id:
            self.skipTest("No experiment ID available from previous step.")

        # Give the system a moment to register the experiment
        time.sleep(10)
        
        result = self._run_cli(["-d", self.experiment_id])
        
        self.assertEqual(result.returncode, 0)
        self.assertRegex(result.stdout, r"Experiment results Test_AddNums_.*\.csv downloaded successfully\.")
        
        downloaded_files = glob.glob("Test_AddNums*.csv")
        if downloaded_files:
            df_actual = pd.read_csv(downloaded_files[0])
            df_expected = pd.read_csv(CSV_FILE_PATH)
            pd.testing.assert_frame_equal(df_actual, df_expected)
        else:
            self.fail("Results CSV file was not found after download.")
        TestGladosCLI._cleanup_files()  # Remove csv file download from previous test to ensure this test is valid
            
    def test_03_experiment_download_all(self):
        if not self.experiment_id:
            self.skipTest("No experiment ID available from previous step.")

        # Give the system a moment to register the experiment
        time.sleep(5)
        
        result = self._run_cli(["-da", self.experiment_id])
        
        self.assertEqual(result.returncode, 0)
        self._assert_in_output("All experiment artifacts downloaded successfully.", result.stdout)
        
        downloaded_files = glob.glob("Test_AddNums*.csv")
        if downloaded_files:
            df_actual = pd.read_csv(downloaded_files[0])
            df_expected = pd.read_csv(CSV_FILE_PATH)
            pd.testing.assert_frame_equal(df_actual, df_expected)
        else:
            self.fail("Results CSV file was not found after download.")
        TestGladosCLI._cleanup_files()  # Remove csv file download from previous test to ensure this test is valid

    def test_04_experiment_query(self):
        result = self._run_cli(["-q", "Test AddNums"])
        
        expected_output_fragment = (
            "Matches:\n***********************************************\nExperiment 1: Test AddNums\n***********************************************\nTags: ['Test', 'AddNums']\nStatus: COMPLETED\nTrials: 100/100 Completed\n"
        )

        actual_filtered = self._filter_output(result.stdout)
        expected_filtered = self._filter_output(expected_output_fragment)
        
        self._assert_in_output(expected_filtered, actual_filtered)

if __name__ == "__main__":
    unittest.main()