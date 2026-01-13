from odoo import http
from odoo.http import request

from .auth_controller import _verify_token_http, _get_json_data
from ..utils.response_formatter import ResponseFormatter
from ..utils.env_helper import get_env


class TimeOffController(http.Controller):

    @http.route('/api/v1/time-off/types', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_leave_types(self):
        try:
            env, cr = get_env()

            try:
                types_data = env['hr.leave'].sudo().api_get_leave_types()
                cr.commit()

                return ResponseFormatter.success_response('Lấy danh sách loại nghỉ thành công', types_data)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/time-off/remaining-days', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_remaining_days(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                result = env['hr.leave'].sudo().api_get_remaining_days(user_id)
                cr.commit()

                return ResponseFormatter.success_response('Lấy số ngày phép còn lại thành công', result)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/time-off/list', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_leave_list(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            data = _get_json_data()
            limit = int(data.get('limit', 10))
            offset = int(data.get('offset', 0))
            state = data.get('state')

            env, cr = get_env()

            try:
                result = env['hr.leave'].sudo().api_get_leave_list(user_id, limit=limit, offset=offset, state=state)
                cr.commit()

                return ResponseFormatter.success_response('Lấy danh sách đơn xin nghỉ thành công', result)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/time-off/detail', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_leave_detail(self):
        try:
            data = _get_json_data()
            leave_id = data.get('leave_id')
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                leave_data = env['hr.leave'].sudo().api_get_leave_detail(leave_id, user_id)
                cr.commit()

                return ResponseFormatter.success_response('Lấy chi tiết đơn xin nghỉ thành công', leave_data)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/time-off/create', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def create_leave(self):
        try:
            data = _get_json_data()
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                result = env['hr.leave'].sudo().api_create_leave(data, user_id)
                cr.commit()

                return ResponseFormatter.success_response('Tạo đơn xin nghỉ thành công', result)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/time-off/update', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def update_leave(self):
        try:
            data = _get_json_data()
            leave_id = data.get('leave_id')
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                leave = env['hr.leave'].sudo().browse(leave_id)
                result = leave.api_update_leave(data, user_id)
                cr.commit()

                return ResponseFormatter.success_response('Cập nhật đơn xin nghỉ thành công', result)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)
