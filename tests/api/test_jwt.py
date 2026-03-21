import os
import time

import pytest

os.environ.setdefault('AIM_SECRET_KEY', 'test-secret-key-for-jwt')


class TestJWTUtils:
    def test_create_and_decode_access_token(self):
        from aim.web.api.auth.jwt_utils import create_access_token, decode_token

        token = create_access_token(user_id=42, username='alice')
        payload = decode_token(token)
        assert payload['user_id'] == 42
        assert payload['username'] == 'alice'
        assert payload['type'] == 'access'

    def test_create_and_decode_refresh_token(self):
        from aim.web.api.auth.jwt_utils import create_refresh_token, decode_token

        token = create_refresh_token(user_id=42, username='alice')
        payload = decode_token(token)
        assert payload['user_id'] == 42
        assert payload['type'] == 'refresh'

    def test_expired_token_raises(self):
        from aim.web.api.auth.jwt_utils import decode_token

        import jwt as pyjwt
        token = pyjwt.encode(
            {'user_id': 1, 'exp': time.time() - 10},
            'test-secret-key-for-jwt',
            algorithm='HS256',
        )
        with pytest.raises(Exception):
            decode_token(token)

    def test_invalid_token_raises(self):
        from aim.web.api.auth.jwt_utils import decode_token

        with pytest.raises(Exception):
            decode_token('not.a.valid.token')

    def test_missing_secret_key_raises(self, monkeypatch):
        monkeypatch.delenv('AIM_SECRET_KEY', raising=False)

        from aim.web.api.auth import jwt_utils
        with pytest.raises(ValueError, match='AIM_SECRET_KEY'):
            jwt_utils._get_secret_key()
