from app.utils.auth import SlackJWTVerifier
from unittest.mock import patch, mock_open
import pytest
from fastapi import HTTPException


def test_when_valid_jwt_then_returns_payload():
    # Setup
    token = "valid.jwt.token"
    key_filename = "public.pem"
    desired_app = "myapp"
    desired_task = "mytask"
    payload = {"app": desired_app, "task": desired_task}
    key_data = b"publickey"

    with patch("builtins.open", mock_open(read_data=key_data)):
        with patch("app.utils.auth.jwt.decode", return_value=payload) as mock_decode:
            result = SlackJWTVerifier.verify_slack_jwt_token(token, key_filename, desired_app, desired_task)
            mock_decode.assert_called_once_with(token, key_data, algorithms=["RS256"])
            assert result == payload


def test_when_bad_keyfile_then_raises_http_400():
    with patch("builtins.open", side_effect=Exception("fail")):
        with pytest.raises(HTTPException) as excinfo:
            SlackJWTVerifier.verify_slack_jwt_token("token", "badfile", "app", "task")
        assert excinfo.value.status_code == 400
        assert "Bad public key filename" in str(excinfo.value.detail)


def test_when_invalid_jwt_then_raises_http_401():
    key_data = b"publickey"
    with patch("builtins.open", mock_open(read_data=key_data)):
        with patch("app.utils.auth.jwt.decode", side_effect=Exception("bad jwt")):
            with pytest.raises(HTTPException) as excinfo:
                SlackJWTVerifier.verify_slack_jwt_token("token", "file", "app", "task")
            assert excinfo.value.status_code == 401
            assert "Invalid JSON Web Token" in str(excinfo.value.detail)


def test_when_invalid_app_in_payload_then_raises_http_401():
    key_data = b"publickey"
    payload = {"app": "wrongapp", "task": "task"}
    with patch("builtins.open", mock_open(read_data=key_data)):
        with patch("app.utils.auth.jwt.decode", return_value=payload):
            with pytest.raises(HTTPException) as excinfo:
                SlackJWTVerifier.verify_slack_jwt_token("token", "file", "app", "task")
            assert excinfo.value.status_code == 401
            assert "Invalid app" in str(excinfo.value.detail)


def test_when_invalid_task_in_payload_then_raises_http_401():
    key_data = b"publickey"
    payload = {"app": "app", "task": "wrongtask"}
    with patch("builtins.open", mock_open(read_data=key_data)):
        with patch("app.utils.auth.jwt.decode", return_value=payload):
            with pytest.raises(HTTPException) as excinfo:
                SlackJWTVerifier.verify_slack_jwt_token("token", "file", "app", "task")
            assert excinfo.value.status_code == 401
            assert "Invalid task" in str(excinfo.value.detail)


def test_when_verifier_called_then_delegates_to_staticmethod():
    verifier = SlackJWTVerifier("file", "app", "task")
    with patch.object(SlackJWTVerifier, "verify_slack_jwt_token", return_value={"app": "app", "task": "task"}) as mock_verify:
        result = verifier("token")
        mock_verify.assert_called_once_with("token", key_filename="file", desired_app="app", desired_task="task")
        assert result == {"app": "app", "task": "task"}
