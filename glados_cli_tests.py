import glados_cli as gcli

from unittest import mock
from typing import *

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
        self._assert_status_code(['-q', 'some_value', '-z', 'another_value'], gcli.EX_PARSE_ERROR)
        self._assert_status_code(['-d', 'some_value', '-q', 'another_value'], gcli.EX_PARSE_ERROR)
        self._assert_status_code(['-z', 'some_value', '-d', 'another_value'], gcli.EX_PARSE_ERROR)
        self._assert_in_error("-z")
        self._assert_in_error("-q")
        self._assert_in_error("-d")
        
    def test_with_invalid_token(self) -> None:
        # Test with an invalid token
        self.request_manager.authenticate.return_value = False
        self._assert_status_code(['-t', 'invalid_token1', '-z', 'experiment.zip'], gcli.EX_INVALID_TOKEN)
        self._assert_in_error("token")
        self._assert_status_code(['-t', 'invalid_token2', '-q', 'experiment_name'], gcli.EX_INVALID_TOKEN)
        self._assert_in_error("token")
        self._assert_status_code(['-t', 'invalid_token3', '-d', 'experiment.zip'], gcli.EX_INVALID_TOKEN)
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
        self._assert_status_code(['-t', 'valid_token', '-z', 'valid-experiment.zip'], gcli.EX_SUCCESS)
        
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
        self._assert_status_code(['-z', 'valid-experiment.zip'], gcli.EX_SUCCESS)
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
        self._assert_status_code(['-t', 'valid_token', '-z', 'missing_experiment.zip'], gcli.EX_NOTFOUND)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self._assert_in_error('missing_experiment.zip')
        self._assert_in_error('not found')
        
    #NOTE: This is commented out due to formatting changes expected
    # def test_run_invalid_experiment_format(self) -> None:
    #     # Test running an experiment with an invalid file format
    #     with open('invalid-experiment.zip', 'w') as f:
    #         f.write('Hehehe yup')
        
    #     self.request_manager.authenticate.return_value = True
    #     self._assert_status_code(['-t', 'valid_token', '-z', 'invalid-experiment.zip'], gcli.EX_INVALID_EXP_FORMAT)
    #     self.request_manager.authenticate.assert_called_with('valid_token')
    #     self._assert_in_error('invalid-experiment.zip')
    #     self._assert_in_error('format')
        
    #NOTE: This is commented out due to formatting changes expected
    # def test_run_experiment_format_missing_files(self) -> None:
    #     # Test running an experiment that might be missing files
    #     self.request_manager.authenticate.return_value = True
    #     self._assert_status_code(['-t', 'valid_token', '-z', 'empty-experiment.zip'], gcli.EX_INVALID_EXP_FORMAT)
    #     self.request_manager.authenticate.assert_called_with('valid_token')
    #     self._assert_in_error('empty-experiment.zip')
    #     self._assert_in_error('manifest.yaml')
        
        
    def test_run_experiment_backend_format_failure(self) -> None:
        # Test running an experiment where the backend's format validation fails
        self.request_manager.authenticate.return_value = True
        self.request_manager.upload_and_start_experiment.return_value = {
            'success': False,
            'error': 'bad_format',
            'exp_id': ''
        }
        self._assert_status_code(['-t', 'valid_token', '-z', 'valid-experiment.zip'], gcli.EX_INVALID_EXP_FORMAT)
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
        self._assert_status_code(['-t', 'valid_token', '-z', 'valid-experiment.zip'], gcli.EX_UNKNOWN)
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
        self._assert_status_code(['-t', 'valid_token', '-d', 'exp123'], gcli.EX_SUCCESS)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.download_experiment_results.assert_called_with('exp123')
        self._assert_in_output('downloaded_results.zip')
        
    def test_download_experiment_not_found(self):
        self.request_manager.download_experiment_results.return_value = {
            'success': False,
            'error': 'not_found'
        }
        self._assert_status_code(['-t', 'valid_token', '-d', 'exp123'], gcli.EX_NOTFOUND)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.download_experiment_results.assert_called_with('exp123')
        self._assert_in_error("not found")
        
    def test_download_experiment_still_running(self):
        self.request_manager.download_experiment_results.return_value = {
            'success': False,
            'error': 'not_done'
        }
        self._assert_status_code(['-t', 'valid_token', '-d', 'exp123'], gcli.EX_NOT_DONE)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.download_experiment_results.assert_called_with('exp123')
        self._assert_in_error("still running")
        
    def test_download_experiment_failed(self):
        self.request_manager.download_experiment_results.return_value = {
            'success': False,
            'error': 'exp_failed'
        }
        self._assert_status_code(['-t', 'valid_token', '-d', 'exp123'], gcli.EX_EXP_FAILED)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.download_experiment_results.assert_called_with('exp123')
        self._assert_in_error("did not complete successfully")
        
        
        
    
if __name__ == '__main__':
    unittest.main()
