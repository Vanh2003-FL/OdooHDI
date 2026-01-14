from functools import wraps

import jwt
from odoo.http import request

from ..utils.jwt_helper import get_jwt_secret_key, is_token_blacklisted
from ..utils.response_formatter import ResponseFormatter


def verify_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None

        # Extract token from Authorization header
        auth_header = request.httprequest.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]

        if not token:
            return ResponseFormatter.error_response(
                'Access token không hợp lệ',
                ResponseFormatter.HTTP_PROXY_AUTH_REQUIRED,
                http_status_code=ResponseFormatter.HTTP_OK
            )

        try:
            secret_key = get_jwt_secret_key()
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])

            # Check if token is blacklisted
            if is_token_blacklisted(token, payload.get('db')):
                return ResponseFormatter.error_response(
                    'Access token không hợp lệ',
                    ResponseFormatter.HTTP_PROXY_AUTH_REQUIRED,
                    http_status_code=ResponseFormatter.HTTP_OK
                )

            request.jwt_payload = payload
        except jwt.ExpiredSignatureError:
            return ResponseFormatter.error_response(
                'Access token không hợp lệ',
                ResponseFormatter.HTTP_PROXY_AUTH_REQUIRED,
                http_status_code=ResponseFormatter.HTTP_OK
            )
        except jwt.InvalidTokenError:
            return ResponseFormatter.error_response(
                'Access token không hợp lệ',
                ResponseFormatter.HTTP_PROXY_AUTH_REQUIRED,
                http_status_code=ResponseFormatter.HTTP_OK
            )

        return f(*args, **kwargs)

    return decorated_function
