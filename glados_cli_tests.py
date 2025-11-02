import glados_cli as gcli
from unittest import mock

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
        
    def parse_args(self, args: list[str]) -> int:
        return gcli.parse_args(self.request_manager, args, stdout=self.out, stderr=self.err)
    
    def _assert_status_code(self, args: list[str], expected_code: int) -> None:
        status = self.parse_args(args)
        self.assertEqual(status, expected_code)
        
    def _assert_in_output(self, substring: str) -> None:
        output = self.out.getvalue()
        self.assertIn(substring, output)
        
    def _assert_in_error(self, substring: str) -> None:
        error = self.err.getvalue()
        self.assertIn(substring, error)
    
    def test_mutually_exclusive_parameters(self) -> None:
        # Test that -s and -z cannot be used together
        self._assert_status_code(['-s', '', '-z', 'another_value'], gcli.EX_PARSE_ERROR)
        self._assert_in_error("-z")
        self._assert_in_error("-q")
        self._assert_in_error("-s")
        self._assert_in_error("-d")
        self._assert_status_code(['-q', 'some_value', '-z', 'another_value'], gcli.EX_PARSE_ERROR)
        self._assert_status_code(['-s', 'some_value', '-q', 'another_value'], gcli.EX_PARSE_ERROR)
        self._assert_status_code(['-s', 'some_value', '-d', 'another_value'], gcli.EX_PARSE_ERROR)
        
    def test_with_invalid_token(self) -> None:
        # Test with an invalid token
        self.request_manager.authenticate.return_value = False
        self._assert_status_code(['-t', 'invalid_token1', '-z', 'experiment.zip'], gcli.EX_INVALID_TOKEN)
        self._assert_in_error("token")
        self._assert_status_code(['-t', 'invalid_token2', '-q', 'experiment_name'], gcli.EX_INVALID_TOKEN)
        self._assert_in_error("token")
        self._assert_status_code(['-t', 'invalid_token3', '-s', 'experiment_type'], gcli.EX_INVALID_TOKEN)
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
        
    def test_with_no_stored_token(self) -> None:
        # Test running an experiment without any token
        os.remove('.token.glados')
        self._assert_status_code(['-z', 'valid-experiment.zip'], gcli.EX_INVALID_TOKEN)
        self._assert_in_error('token')
    
    def test_run_missing_experiment(self) -> None:
        # Test running a non-existent experiment file
        self.request_manager.authenticate.return_value = True
        self._assert_status_code(['-t', 'valid_token', '-z', 'missing_experiment.zip'], gcli.EX_NOTFOUND)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self._assert_in_error('missing_experiment.zip')
        self._assert_in_error('not found')
        
    def test_run_invalid_experiment_format(self) -> None:
        # Test running an experiment with an invalid file format
        with open('invalid-experiment.zip', 'w') as f:
            f.write('Hehehe yup')
        
        self.request_manager.authenticate.return_value = True
        self._assert_status_code(['-t', 'valid_token', '-z', 'invalid-experiment.zip'], gcli.EX_INVALID_EXP_FORMAT)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self._assert_in_error('invalid-experiment.zip')
        self._assert_in_error('format')
        
    def test_run_experiment_format_missing_files(self) -> None:
        # Test running an experiment that might be missing files
        self.request_manager.authenticate.return_value = True
        self._assert_status_code(['-t', 'valid_token', '-z', 'empty-experiment.zip'], gcli.EX_INVALID_EXP_FORMAT)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self._assert_in_error('empty-experiment.zip')
        self._assert_in_error('manifest.yaml')
        
        
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
        
    def test_get_experiment_status(self) -> None:
        # Test getting the status of an experiment
        self.request_manager.authenticate.return_value = True
        self.request_manager.get_experiment_status.return_value = {
            'success': True,
            'status': 'completed',
            'current_permutation': 500,
            'total_permutations': 500
        }
        self._assert_status_code(['-t', 'valid_token', '-s', 'exp123'], gcli.EX_SUCCESS)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.upload_and_start_experiment.assert_not_called()
        self.request_manager.get_experiment_status.assert_called_with('exp123')
        self._assert_in_output('completed')
        self._assert_in_output('500/500')
        
        self.request_manager.get_experiment_status.return_value = {
            'success': True,
            'status': 'running',
            'current_permutation': 100,
            'total_permutations': 500
        }
        self._assert_status_code(['-t', 'valid_token', '-s', 'exp123'], gcli.EX_SUCCESS)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.get_experiment_status.assert_called_with('exp123')
        self._assert_in_output('running')
        self._assert_in_output('100/500')
        
    def test_get_nonexistent_experiment_status(self) -> None:
        # Test getting the status of a non-existent experiment
        self.request_manager.authenticate.return_value = True
        self.request_manager.get_experiment_status.return_value = {
            'success': False,
            'error': 'not_found'
        }
        self._assert_status_code(['-t', 'valid_token', '-s', 'nonexistent_exp'], gcli.EX_NOTFOUND)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.get_experiment_status.assert_called_with('nonexistent_exp')
        self._assert_in_error('not found')
        
    def test_get_experiment_status_other_backend_failure(self) -> None:
        # Test getting the status of an experiment where the backend fails for unknown reasons
        self.request_manager.authenticate.return_value = True
        self.request_manager.get_experiment_status.return_value = {
            'success': False,
            'error': 'other'
        }
        self._assert_status_code(['-t', 'valid_token', '-s', 'exp123'], gcli.EX_UNKNOWN)
        self.request_manager.authenticate.assert_called_with('valid_token')
        self.request_manager.get_experiment_status.assert_called_with('exp123')
        self._assert_in_error('other')        
    
if __name__ == '__main__':
    unittest.main()