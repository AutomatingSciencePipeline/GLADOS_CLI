import unittest
from unittest import mock

import requests

import glados_cli as gcli


class AuthenticatedStartTests(unittest.TestCase):
    def upload(self, start_response):
        manager = gcli.RequestManager()
        manager.token = "synthetic-token"
        upload = mock.Mock()
        upload.json.return_value = {"fileId": "file-id", "message": "Uploaded"}
        submission = mock.Mock()
        submission.json.return_value = {"success": True, "expId": "experiment-id"}
        with mock.patch("builtins.open", mock.mock_open(read_data=b"fixture")), \
                mock.patch.object(gcli.time, "sleep"), \
                mock.patch.object(gcli, "perror"), \
                mock.patch.object(gcli.requests, "post", side_effect=[
                    upload, submission, start_response,
                ]) as post:
            result = manager.upload_and_start_experiment("fixture.zip")
        return result, post

    def test_start_sends_token_and_accepts_empty_http_success(self):
        response = requests.Response()
        response.status_code = 200
        response._content = b""
        result, post = self.upload(response)
        self.assertEqual(result, {"success": True, "error": "", "exp_id": "experiment-id"})
        self.assertEqual(post.call_args.kwargs["json"], {
            "id": "experiment-id", "token": "synthetic-token",
        })
        self.assertEqual(post.call_args.args[0], gcli.START_EXPERIMENT_URL + "experiment-id")
        self.assertFalse(post.call_args.kwargs["allow_redirects"])

    def test_start_http_failures_do_not_report_success(self):
        for status in (300, 302, 304, 307, 400, 401, 403, 404, 500, 503):
            with self.subTest(status=status):
                response = requests.Response()
                response.status_code = status
                result, _ = self.upload(response)
                self.assertEqual(result, {
                    "success": False, "error": "other", "exp_id": "experiment-id",
                })

    def test_start_transport_failures_do_not_report_success(self):
        for error in (requests.Timeout("mock timeout"), requests.ConnectionError("mock refusal")):
            with self.subTest(error=type(error).__name__):
                result, _ = self.upload(error)
                self.assertFalse(result["success"])
                self.assertEqual(result["exp_id"], "experiment-id")


if __name__ == "__main__":
    unittest.main()
