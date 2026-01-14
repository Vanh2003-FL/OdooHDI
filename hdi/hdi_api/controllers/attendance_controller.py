import json
from datetime import datetime, timedelta
from odoo import http
from odoo.http import request

from ..decorators.auth import verify_token
from ..utils.request_helper import get_json_data, get_request_data
from ..utils.response_formatter import ResponseFormatter
from ..utils.env_helper import get_env


class AttendanceAPI(http.Controller):

    @http.route('/api/v1/attendance/check-in', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def check_in(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                data = get_request_data()
                in_latitude = data.get('in_latitude')
                in_longitude = data.get('in_longitude')
                check_in_location = data.get('check_in_location')

                result = env['hr.attendance'].sudo().api_check_in(user_id, in_latitude, in_longitude, check_in_location)
                cr.commit()

                return ResponseFormatter.success_response('Chấm công vào thành công', result, ResponseFormatter.HTTP_OK)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/attendance/check-out', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def check_out(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                data = get_request_data()
                out_latitude = data.get('out_latitude')
                out_longitude = data.get('out_longitude')
                check_out_location = data.get('check_out_location')

                result = env['hr.attendance'].sudo().api_check_out(user_id, out_latitude, out_longitude, check_out_location)
                cr.commit()

                return ResponseFormatter.success_response('Chấm công ra thành công', result, ResponseFormatter.HTTP_OK)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/attendance/status', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def get_status(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                result = env['hr.attendance'].sudo().api_get_status(user_id)
                cr.commit()
                return ResponseFormatter.success_response('Trạng thái chấm công', result, ResponseFormatter.HTTP_OK)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/attendance/history', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def get_history(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                data = get_request_data()
                limit = int(data.get('limit', 30))
                offset = int(data.get('offset', 0))
                from_date = data.get('from_date')
                to_date = data.get('to_date')

                result = env['hr.attendance'].sudo().api_get_history(user_id, limit, offset, from_date, to_date)
                cr.commit()
                return ResponseFormatter.success_response('Lịch sử chấm công', result, ResponseFormatter.HTTP_OK)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/attendance/summary', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def get_summary(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                data = get_request_data()
                month = data.get('month')

                result = env['hr.attendance'].sudo().api_get_summary(user_id, month)
                cr.commit()
                return ResponseFormatter.success_response('Tổng hợp chấm công', result, ResponseFormatter.HTTP_OK)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/attendance/detail', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def get_detail(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                data = get_request_data()
                attendance_id = data.get('attendance_id')

                result = env['hr.attendance'].sudo().api_get_detail(user_id, attendance_id)
                cr.commit()
                return ResponseFormatter.success_response('Chi tiết bản ghi chấm công', result, ResponseFormatter.HTTP_OK)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)


