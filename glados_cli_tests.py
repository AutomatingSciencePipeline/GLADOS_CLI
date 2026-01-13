import glados_cli as gcli

from unittest import mock
from typing import *
from io import StringIO
from contextlib import redirect_stdout

import os
import io
import unittest
import zipfile

class GladosCliTests(unittest.TestCase):
    
    def setUp(self):
        self.request_manager: gcli.RequestManager = mock.MagicMock()
        self._makeZipFile('valid-experiment')
        self._makeZipFile('empty-experiment')
        # Allow for testing what's printed to stdout and stderr
        self.out = io.StringIO()
        self.err = io.StringIO()
                    
    def _makeZipFile(self, dirname: str) -> None:
        with zipfile.ZipFile(f'{dirname}.zip', 'w') as zf:
            for dirpath, _, filenames in os.walk(dirname):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    zf.write(filepath, os.path.relpath(filepath, dirname))
        
    def parse_args(self, args: List[str]) -> int:
        return gcli.parse_args(self.request_manager, args, stdout=self.out, stderr=self.err)
    
    def _assert_status_code(self, args: List[str], expected_code: int) -> None:
        status = self.parse_args(args)
        self.assertEqual(status, expected_code)
        
    def _assert_in_output(self, substring: str) -> None:
        output = self.out.getvalue()
        if (substring not in output):
            print("OUTPUT:")
            print(output)
        self.assertIn(substring, output)
        
    def _assert_in_error(self, substring: str) -> None:
        error = self.err.getvalue()
        if (substring not in error):
            print("ERROR:")
            print(error)
        self.assertIn(substring, error)
    
    def test_mutually_exclusive_parameters(self) -> None:
        # Test that -s and -z cannot be used together
        self.request_manager.authenticate.return_value = True
        self._assert_status_code(['-q', 'some_value', '-r', 'another_value'], gcli.EX_PARSE_ERROR)
        self._assert_status_code(['-d', 'some_value', 'some_value', '-q', 'another_value'], gcli.EX_PARSE_ERROR)
        self._assert_status_code(['-r', 'some_value', '-d', 'another_value', 'another_value'], gcli.EX_PARSE_ERROR)
        self._assert_in_error("-r")
        self._assert_in_error("-q")
        self._assert_in_error("-d")
        
    def test_with_invalid_token(self) -> None:
        # Test with an invalid token
        self.request_manager.authenticate.return_value = False
        self._assert_status_code(['-t', 'invalid_token1', '-r', 'experiment.zip'], gcli.EX_INVALID_TOKEN)
        self._assert_in_error("token")
        self._assert_status_code(['-t', 'invalid_token2', '-q', 'experiment_name'], gcli.EX_INVALID_TOKEN)
        self._assert_in_error("token")
        self._assert_status_code(['-t', 'invalid_token3', '-d', 'experiment.zip', 'example_path'], gcli.EX_INVALID_TOKEN)
        self._assert_in_error("token")
        self.request_manager.authenticate.assert_has_calls([
            mock.call('invalid_token1'), 
            mock.call('invalid_token2'),
            mock.call('invalid_token3')], any_order=False)
        
    def test_run_experiment(self) -> None:
        # Test running an experiment with a valid token
        self.request_manager.authenticate.return_value = True
        self.request_manager.upload_and_start_experiment.return_value = {
            'success': True,
            'error': '',
            'exp_id': 'exp123'
        }
        self._assert_status_code(['-t', 'valid_token', '-r', 'valid-experiment.zip'], gcli.EX_SUCCESS)
        
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.upload_and_start_experiment.assert_called_with('valid-experiment.zip')
        self._assert_in_output('exp123')
        
    def test_with_stored_token(self) -> None:
        # Test running an experiment with a stored token
        with open('.token.glados', 'w') as f:
            f.write('valid_token')
            
        self.request_manager.authenticate.return_value = True
        self.request_manager.upload_and_start_experiment.return_value = {
            'success': True,
            'error': '',
            'exp_id': 'expabc'
        }
        self._assert_status_code(['-r', 'valid-experiment.zip'], gcli.EX_SUCCESS)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.upload_and_start_experiment.assert_called_with('valid-experiment.zip')
        self._assert_in_output('expabc')
        
        os.remove('.token.glados')
        
    def test_generate_token(self) -> None:
        # Test running an experiment without any token
        self.request_manager.generate_token.return_value = {
            "access_token": "new_valid_token",
            "error": None
        }
        self._assert_status_code(['--generate-token'], gcli.EX_SUCCESS)
        self.request_manager.generate_token.assert_called_once()
        self._assert_in_output('new_valid_token')
    
    def test_run_missing_experiment(self) -> None:
        # Test running a non-existent experiment file
        self.request_manager.authenticate.return_value = True
        self._assert_status_code(['-t', 'valid_token', '-r', 'missing_experiment.zip'], gcli.EX_NOTFOUND)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self._assert_in_error('missing_experiment.zip')
        self._assert_in_error('not found')
        
    def test_run_experiment_backend_format_failure(self) -> None:
        # Test running an experiment where the backend's format validation fails
        self.request_manager.authenticate.return_value = True
        self.request_manager.upload_and_start_experiment.return_value = {
            'success': False,
            'error': 'bad_format',
            'exp_id': ''
        }
        self._assert_status_code(['-t', 'valid_token', '-r', 'valid-experiment.zip'], gcli.EX_INVALID_EXP_FORMAT)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.upload_and_start_experiment.assert_called_with('valid-experiment.zip')
        self._assert_in_error('format')
        
    def test_run_experiment_other_backend_failure(self) -> None:
        # Test running an experiment where the backend fails for other reasons
        self.request_manager.authenticate.return_value = True
        self.request_manager.upload_and_start_experiment.return_value = {
            'success': False,
            'error': 'other',
            'exp_id': ''
        }
        self._assert_status_code(['-t', 'valid_token', '-r', 'valid-experiment.zip'], gcli.EX_UNKNOWN)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.upload_and_start_experiment.assert_called_with('valid-experiment.zip')
        self._assert_in_error('other')
        
    def test_query_one_experiment(self):
        self.request_manager.authenticate.return_value = True
        self.request_manager.query_experiments.return_value = {
            'success': True,
            'matches': [
                {'id': 'exp1', 
                 'name': 'Test Experiment', 
                 'tags': ['tag1', 'tag2'],
                 'status': 'completed',
                 'started_on': 1762488593221,
                 'current_permutation': 50,
                 'total_permutations': 100},
            ]
        }
        self._assert_status_code(['-t', 'valid_token', '-q', 'Test Experiment'], gcli.EX_SUCCESS)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.query_experiments.assert_called_with('Test Experiment')     
        self._assert_in_output('Test Experiment')
    
    def test_query_multiple_experiments(self):
        self.request_manager.authenticate.return_value = True
        self.request_manager.query_experiments.return_value = {
            'success': True,
            'matches': [
                {'id': 'exp1', 
                 'name': 'Test Experiment 1', 
                 'tags': ['tag1'],
                 'status': 'running',
                 'started_on': 1762488593221,
                 'current_permutation': 70,
                 'total_permutations': 100},
                {'id': 'exp2', 
                 'name': 'Test Experiment 2', 
                 'tags': ['tag2'],
                 'status': 'completed',
                 'started_on': 1762489593221,
                 'current_permutation': 80,
                 'total_permutations': 100},
            ]
        }
        self._assert_status_code(['-t', 'valid_token', '-q', 'Test Experiment'], gcli.EX_SUCCESS)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.query_experiments.assert_called_with('Test Experiment')
        self._assert_in_output('Test Experiment 1')
        self._assert_in_output('Test Experiment 2')
        
    def test_query_no_experiments(self):
        self.request_manager.authenticate.return_value = True
        self.request_manager.query_experiments.return_value = {
            'success': True,
            'matches': []
        }
        self._assert_status_code(['-t', 'valid_token', '-q', 'Nonexistent Experiment'], gcli.EX_NOTFOUND)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.query_experiments.assert_called_with('Nonexistent Experiment')
        self._assert_in_error('No experiments found')
    
    def test_download_experiment_results(self):
        self.request_manager.authenticate.return_value = True
        self.request_manager.download_experiment_results.return_value = {
            'success': True,
            'files': [
                {
                    'name': 'downloaded_results.zip',
                    'content': b'PK\x03\x04...'  # Simulated binary content of a zip file
                }
            ]
        }
        self._assert_status_code(['-t', 'valid_token', '-d', 'exp123', r'C:\Users\exampleUser\Downloads'], gcli.EX_SUCCESS)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.download_experiment_results.assert_called_with('exp123', r'C:\Users\exampleUser\Downloads')
        self._assert_in_output('downloaded_results.zip')
        
    def test_download_experiment_not_found(self):
        self.request_manager.download_experiment_results.return_value = {
            'success': False,
            'error': 'not_found'
        }
        self._assert_status_code(['-t', 'valid_token', '-d', 'exp123', r'C:\Users\exampleUser\Downloads'], gcli.EX_NOTFOUND)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.download_experiment_results.assert_called_with('exp123', r'C:\Users\exampleUser\Downloads')
        self._assert_in_error("not found")
        
    def test_download_experiment_still_running(self):
        self.request_manager.download_experiment_results.return_value = {
            'success': False,
            'error': 'not_done'
        }
        self._assert_status_code(['-t', 'valid_token', '-d', 'exp123', r'C:\Users\exampleUser\Downloads'], gcli.EX_NOT_DONE)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.download_experiment_results.assert_called_with('exp123', r'C:\Users\exampleUser\Downloads')
        self._assert_in_error("still running")
        
    def test_download_experiment_failed(self):
        self.request_manager.download_experiment_results.return_value = {
            'success': False,
            'error': 'exp_failed'
        }
        self._assert_status_code(['-t', 'valid_token', '-d', 'exp123', r'C:\Users\exampleUser\Downloads'], gcli.EX_EXP_FAILED)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.download_experiment_results.assert_called_with('exp123', r'C:\Users\exampleUser\Downloads')
        self._assert_in_error("did not complete successfully")
        
    def test_download_all_experiment_results(self):
        self.request_manager.authenticate.return_value = True
        self.request_manager.download_all.return_value = {
            'success': True,
            'files': [
                {
                    'name': 'downloaded_results.zip',
                    'content': b'PK\x03\x04...'  # Simulated binary content of a zip file
                }
            ]
        }
        self._assert_status_code(['-t', 'valid_token', '-da', 'exp123', r'C:\Users\exampleUser\Downloads'], gcli.EX_SUCCESS)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.download_all.assert_called_with('exp123', r'C:\Users\exampleUser\Downloads')
        self._assert_in_output('All experiment artifacts downloaded successfully to C:\\Users\\exampleUser\\Downloads.')
        
    def test_download_all_experiment_not_found(self):
        self.request_manager.download_all.return_value = {
            'success': False,
            'error': 'not_found'
        }
        self._assert_status_code(['-t', 'valid_token', '-da', 'exp123', r'C:\Users\exampleUser\Downloads'], gcli.EX_NOTFOUND)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.download_all.assert_called_with('exp123', r'C:\Users\exampleUser\Downloads')
        self._assert_in_error("not found")
        
    def test_download_all_experiment_still_running(self):
        self.request_manager.download_all.return_value = {
            'success': False,
            'error': 'not_done'
        }
        self._assert_status_code(['-t', 'valid_token', '-da', 'exp123', r'C:\Users\exampleUser\Downloads'], gcli.EX_NOT_DONE)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.download_all.assert_called_with('exp123', r'C:\Users\exampleUser\Downloads')
        self._assert_in_error("still running")
        
    def test_download_all_experiment_failed(self):
        self.request_manager.download_all.return_value = {
            'success': False,
            'error': 'exp_failed'
        }
        self._assert_status_code(['-t', 'valid_token', '-da', 'exp123', r'C:\Users\exampleUser\Downloads'], gcli.EX_EXP_FAILED)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.download_all.assert_called_with('exp123', r'C:\Users\exampleUser\Downloads')
        self._assert_in_error("did not complete successfully")
        
    def test_cli_update_success(self):
        self.request_manager.update.return_value = {
            "success": True,
            "error": False
        }
        self._assert_status_code(['--update'], gcli.UPDATE_SUCCEED)
        self.request_manager.update.assert_called_once()
        self._assert_in_output("Downloaded most up-to-date CLI successfully")     
        
    def test_cli_update_failure(self):
        self.request_manager.update.return_value = {
            "success": False,
            "error": "network"
        }
        self._assert_status_code(['-u'], gcli.UPDATE_FAIL)
        self.request_manager.update.assert_called_once()
        self._assert_in_output("Unable to download most up-to-date version")
        
    def test_manifest_no_errors(self):
        gcli.check_manifest_format("test_manifests/test_manifest_no_errors.yml", False)
        self._assert_in_output("")
        
    def test_manifest_string_errors(self):
        buf = StringIO()
        with redirect_stdout(buf):
            result = gcli.check_manifest_format("test_manifests/test_manifest_string_errors.yml", True)
        output = buf.getvalue()
        self.assertEqual(result, gcli.EX_INVALID_EXP_FORMAT)
        self.assertIn("name attribute in manifest.yml is empty, missing, or not a string.", output)
        self.assertIn("trialResult attribute in manifest.yml is empty, missing, or not a string.", output)
        self.assertIn("scatterIndVar attribute in manifest.yml is empty, missing, or not a string.", output)
        self.assertIn("scatterDepVar attribute in manifest.yml is empty, missing, or not a string.", output)
        self.assertIn("experimentExecutable attribute in manifest.yml is empty, missing, or not a string.", output)
        
    def test_manifest_int_errors(self):
        buf = StringIO()
        with redirect_stdout(buf):
            result = gcli.check_manifest_format("test_manifests/test_manifest_int_errors.yml", True)
        output = buf.getvalue()
        self.assertEqual(result, gcli.EX_INVALID_EXP_FORMAT)
        self.assertIn("trialResultLineNumber attribute in manifest.yml is empty or missing.", output)
        self.assertIn("timeout attribute in manifest.yml is not greater than 0.", output)
        self.assertIn("workers attribute in manifest.yml is not greater than 0", output)
        
    def test_manifest_bool_errors(self):
        buf = StringIO()
        with redirect_stdout(buf):
            result = gcli.check_manifest_format("test_manifests/test_manifest_bool_errors.yml", True)
        output = buf.getvalue()
        self.assertEqual(result, gcli.EX_INVALID_EXP_FORMAT)
        self.assertIn("keepLogs attribute in manifest.yml is empty, missing, or not true or false.", output)
        self.assertIn("sendEmail attribute in manifest.yml is empty, missing, or not true or false.", output)
        self.assertIn("scatter attribute in manifest.yml is empty, missing, or not true or false.", output)
        
    def test_manifest_param_errors(self):
        buf = StringIO()
        with redirect_stdout(buf):
            result = gcli.check_manifest_format("test_manifests/test_manifest_param_errors.yml", True)
        output = buf.getvalue()
        self.assertEqual(result, gcli.EX_INVALID_EXP_FORMAT)
        self.assertIn("min attribute in hyperparameter x is not a float.", output)
        self.assertIn("values attribute in hyperparameter values1 is not a list.", output)
        self.assertIn("min attribute in hyperparameter y is not an integer.", output)
        self.assertIn("max attribute in hyperparameter z is not greater than 12.", output)
        self.assertIn("default attribute in hyperparameter values2 is empty, missing, or not true or false.", output)
        self.assertIn("Type specified in hyperparameter values3 is not integer, float, bool, stringlist, or paramgroup.", output)
    
if __name__ == '__main__':
    unittest.main()
