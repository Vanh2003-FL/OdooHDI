from odoo import http
from odoo.http import request

from ..decorators.auth import verify_token
from ..utils.jwt_helper import get_jwt_secret_key
from ..utils.request_helper import get_json_data
from ..utils.response_formatter import ResponseFormatter


class MobileAppAuthAPI(http.Controller):

    @http.route('/api/v1/auth/login', type='http', auth='none', methods=['POST'], csrf=False)
    def login(self):
        try:
            data = get_json_data()
            login = data.get('login')
            password = data.get('password')

            if not login or not password:
                return ResponseFormatter.error_response(
                    'Tên đăng nhập và mật khẩu là bắt buộc',
                    ResponseFormatter.HTTP_BAD_REQUEST,
                    http_status_code=ResponseFormatter.HTTP_OK)

            db_name = request.env.cr.dbname
            secret_key = get_jwt_secret_key()

            user_data = request.env['res.users'].sudo().api_login(login, password, secret_key, db_name)

            return ResponseFormatter.success_response('Đăng nhập thành công', user_data)

        except Exception as e:
            return ResponseFormatter.error_response(
                f'Lỗi: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR,
                http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/refresh-token', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def refresh_token(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            db_name = request.jwt_payload.get('db')
            old_token_exp = request.jwt_payload.get('exp')
            old_token = request.httprequest.headers.get('Authorization', '').replace('Bearer ', '')
            secret_key = get_jwt_secret_key()

            token_data = request.env['res.users'].sudo().api_refresh_token(
                user_id, old_token, old_token_exp, secret_key, db_name
            )

            return ResponseFormatter.success_response('Làm mới token thành công', token_data)

        except Exception as e:
            return ResponseFormatter.error_response(
                f'Lỗi: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR,
                http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/logout', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def logout(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            token_exp = request.jwt_payload.get('exp')
            token = request.httprequest.headers.get('Authorization', '').replace('Bearer ', '')

            request.env['res.users'].sudo().api_logout(user_id, token, token_exp)

            return ResponseFormatter.success_response('Đã đăng xuất thành công')

        except Exception as e:
            return ResponseFormatter.error_response(
                f'Lỗi: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR,
                http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/refresh-info', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def get_current_user(self):
        try:
            user_id = request.jwt_payload.get('user_id')

            user_data = request.env['res.users'].sudo().api_get_current_user(user_id)

            return ResponseFormatter.success_response('Lấy thông tin người dùng thành công', user_data)

        except Exception as e:
            return ResponseFormatter.error_response(
                f'Lỗi: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR,
                http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/change-password', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def change_password(self):
        try:
            data = get_json_data()
            user_id = request.jwt_payload.get('user_id')

            old_password = data.get('old_password')
            new_password = data.get('new_password')
            confirm_password = data.get('confirm_password')

            request.env['res.users'].sudo().api_change_password(
                user_id, old_password, new_password, confirm_password
            )

            return ResponseFormatter.success_response('Đổi mật khẩu thành công')

        except Exception as e:
            return ResponseFormatter.error_response(
                f'Lỗi: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR,
                http_status_code=ResponseFormatter.HTTP_OK)


