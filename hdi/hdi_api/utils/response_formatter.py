import json
from odoo.http import Response


class ResponseFormatter:
    
    HTTP_OK = 200
    HTTP_CREATED = 201
    HTTP_BAD_REQUEST = 400
    HTTP_UNAUTHORIZED = 401
    HTTP_FORBIDDEN = 403
    HTTP_NOT_FOUND = 404
    HTTP_PROXY_AUTH_REQUIRED = 407
    HTTP_INTERNAL_ERROR = 500
    
    STATUS_SUCCESS = 'Success'
    STATUS_ERROR = 'Error'

    @staticmethod
    def success(message, data=None, code=HTTP_OK):
        return {
            'code': code,
            'status': ResponseFormatter.STATUS_SUCCESS,
            'message': message,
            'data': data or {}
        }

    @staticmethod
    def error(message, code=HTTP_BAD_REQUEST, data=None):
        return {
            'code': code,
            'status': ResponseFormatter.STATUS_ERROR,
            'message': message,
            'data': data or {}
        }

    @staticmethod
    def make_response(response_dict, status_code=200):
        return Response(
            json.dumps(response_dict, ensure_ascii=False),
            status=status_code,
            mimetype='application/json',
            headers={'Content-Type': 'application/json; charset=utf-8'}
        )

    @staticmethod
    def success_response(message, data=None, status_code=HTTP_OK, http_status_code=None):
        if http_status_code is None:
            http_status_code = status_code
        response_dict = ResponseFormatter.success(message, data, status_code)
        return ResponseFormatter.make_response(response_dict, http_status_code)

    @staticmethod
    def error_response(message, status_code=HTTP_BAD_REQUEST, data=None, http_status_code=None):
        if http_status_code is None:
            http_status_code = status_code
        response_dict = ResponseFormatter.error(message, status_code, data)
        return ResponseFormatter.make_response(response_dict, http_status_code)
