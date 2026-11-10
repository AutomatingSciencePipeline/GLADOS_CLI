import io
import json
import unittest
from contextlib import redirect_stdout
from unittest import mock

import requests

import glados_cli as gcli


def response(status=200, payload=None, content=None):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(payload).encode() if content is None else content
    return result


class AuthenticatedStartTests(unittest.TestCase):
    def upload(self, start_response, upload_response=None, submission_response=None, open_failures=None):
        manager = gcli.RequestManager()
        manager.token = "synthetic-token"
        if upload_response is None:
            upload_response = response(payload={"fileId": "file-id", "message": "Uploaded"})
        if submission_response is None:
            submission_response = response(payload={"success": True, "expId": "experiment-id"})
        handles = []
        open_calls = []

        def open_fixture(*args, **kwargs):
            open_calls.append(args)
            error = (open_failures or {}).get(len(open_calls))
            if error is not None:
                raise error
            handle = io.BytesIO(b"fixture")
            handles.append(handle)
            return handle

        with mock.patch("builtins.open", side_effect=open_fixture), \
                mock.patch.object(gcli.time, "sleep"), \
                mock.patch.object(gcli, "perror"), \
                mock.patch.object(gcli.requests, "post", side_effect=[
                    upload_response, submission_response, start_response,
                ]) as post, redirect_stdout(io.StringIO()):
            result = manager.upload_and_start_experiment("fixture.zip")
        return result, post, handles

    def assert_closed(self, handles):
        self.assertTrue(handles)
        self.assertTrue(all(handle.closed for handle in handles))

    def test_start_sends_token_and_accepts_empty_http_success(self):
        result, post, handles = self.upload(response(content=b""))
        self.assertEqual(result, {"success": True, "error": "", "exp_id": "experiment-id"})
        self.assertEqual(post.call_count, 3)
        self.assertEqual(post.call_args.kwargs["json"], {
            "id": "experiment-id", "token": "synthetic-token",
        })
        self.assertEqual(post.call_args.args[0], gcli.START_EXPERIMENT_URL + "experiment-id")
        for call in post.call_args_list:
            self.assertFalse(call.kwargs["allow_redirects"])
        self.assert_closed(handles)

    def test_upload_message_is_optional_and_created_responses_are_accepted(self):
        result, post, handles = self.upload(
            response(content=b""),
            response(201, {"fileId": "file-id"}),
            response(201, {"expId": "experiment-id"}),
        )
        self.assertEqual(result, {"success": True, "error": "", "exp_id": "experiment-id"})
        self.assertEqual(post.call_count, 3)
        self.assert_closed(handles)

    def failure_responses(self, id_key):
        yield "timeout", requests.Timeout("mock timeout")
        yield "connection", requests.ConnectionError("mock refusal")
        for status in (300, 302, 304, 307, 308, 401, 404, 500):
            yield "http-" + str(status), response(status, {id_key: "valid-id"})
        yield "non-json", response(content=b"not JSON")
        yield "deeply-nested-json", response(content=b"[" * 1200)
        for label, payload in (("null", None), ("array", []), ("number", 42),
                               ("boolean", True), ("string", "unexpected"), ("missing-id", {})):
            yield label, response(payload=payload)
        for invalid_id in (None, "", " ", 0, False, [], {}):
            yield "invalid-id-" + repr(invalid_id), response(payload={id_key: invalid_id})
        yield "explicit-failure-with-id", response(payload={id_key: "valid-id", "success": False})

    def test_upload_open_failures_stop_before_requests(self):
        for error in (PermissionError("mock denied"), FileNotFoundError("mock missing")):
            with self.subTest(error=type(error).__name__):
                result, post, handles = self.upload(response(content=b""), open_failures={1: error})
                self.assertEqual(result, {"success": False, "error": "other", "exp_id": ""})
                post.assert_not_called()
                self.assertEqual(handles, [])

    def test_manifest_open_failures_stop_before_submission_and_start(self):
        for error in (PermissionError("mock denied"), FileNotFoundError("mock missing")):
            with self.subTest(error=type(error).__name__):
                result, post, handles = self.upload(response(content=b""), open_failures={2: error})
                self.assertEqual(result, {"success": False, "error": "other", "exp_id": ""})
                self.assertEqual(post.call_count, 1)
                self.assertEqual(post.call_args.args[0], gcli.UPLOAD_EXPERIMENT_URL)
                self.assert_closed(handles)

    def test_upload_failures_stop_before_submission_and_start(self):
        for label, failure in self.failure_responses("fileId"):
            with self.subTest(failure=label):
                result, post, handles = self.upload(response(content=b""), upload_response=failure)
                self.assertEqual(result, {"success": False, "error": "other", "exp_id": ""})
                self.assertEqual(post.call_count, 1)
                self.assertEqual(post.call_args.args[0], gcli.UPLOAD_EXPERIMENT_URL)
                self.assertFalse(post.call_args.kwargs["allow_redirects"])
                self.assert_closed(handles)

    def test_upload_format_failure_preserves_backend_message(self):
        result, post, handles = self.upload(
            response(content=b""), upload_response=response(payload={"message": "bad_format"}),
        )
        self.assertEqual(result, {"success": False, "error": "bad_format", "exp_id": ""})
        self.assertEqual(post.call_count, 1)
        self.assert_closed(handles)

    def test_submission_failures_stop_before_start(self):
        for label, failure in self.failure_responses("expId"):
            with self.subTest(failure=label):
                result, post, handles = self.upload(response(content=b""), submission_response=failure)
                self.assertEqual(result, {"success": False, "error": "other", "exp_id": ""})
                self.assertEqual(post.call_count, 2)
                self.assertEqual(post.call_args.args[0], gcli.SUBMIT_EXPERIMENT_URL)
                for call in post.call_args_list:
                    self.assertFalse(call.kwargs["allow_redirects"])
                self.assert_closed(handles)

    def test_start_http_failures_do_not_report_success(self):
        for status in (300, 302, 304, 307, 400, 401, 403, 404, 500, 503):
            with self.subTest(status=status):
                result, post, handles = self.upload(response(status))
                self.assertEqual(result, {
                    "success": False, "error": "other", "exp_id": "experiment-id",
                })
                self.assertEqual(post.call_count, 3)
                self.assert_closed(handles)

    def test_start_transport_failures_do_not_report_success(self):
        for error in (requests.Timeout("mock timeout"), requests.ConnectionError("mock refusal")):
            with self.subTest(error=type(error).__name__):
                result, post, handles = self.upload(error)
                self.assertFalse(result["success"])
                self.assertEqual(result["exp_id"], "experiment-id")
                self.assertEqual(post.call_count, 3)
                self.assert_closed(handles)


if __name__ == "__main__":
    unittest.main()
