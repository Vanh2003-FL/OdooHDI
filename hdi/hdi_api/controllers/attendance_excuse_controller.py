from odoo import http
from odoo.http import request

from ..decorators.auth import verify_token
from ..utils.request_helper import get_json_data
from ..utils.response_formatter import ResponseFormatter
from ..utils.env_helper import get_env


class MobileAppAttendanceExcuseAPI(http.Controller):

    @http.route('/api/v1/attendance-excuse/create', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def create_excuse(self):
        try:
            data = get_json_data()
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                result = env['attendance.excuse'].sudo().api_create_excuse(data, user_id)
                cr.commit()
                return ResponseFormatter.success_response('Tạo giải trình thành công', result)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/attendance-excuse/detail', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def get_excuse(self):
        try:
            data = get_json_data()
            attendance_excuse_id = data.get('attendance_excuse_id')
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                excuse = env['attendance.excuse'].sudo().browse(attendance_excuse_id)
                result = excuse.api_get_excuse_detail(user_id)
                cr.commit()
                return ResponseFormatter.success_response('Lấy chi tiết giải trình thành công', result)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/attendance-excuse/list', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def get_excuse_list(self):
        try:
            data = get_json_data()
            user_id = request.jwt_payload.get('user_id')
            limit = data.get('limit', 10)
            offset = data.get('offset', 0)
            state = data.get('state')
            env, cr = get_env()

            try:
                result = env['attendance.excuse'].sudo().api_get_my_excuse_list(
                    user_id, limit=limit, offset=offset, state=state
                )
                cr.commit()
                return ResponseFormatter.success_response('Lấy danh sách giải trình thành công', result)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/attendance-excuse/action', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def handle_excuse_action(self):
        try:
            data = get_json_data()
            attendance_excuse_id = data.get('attendance_excuse_id')
            action = data.get('action')
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            if not attendance_excuse_id:
                return ResponseFormatter.error_response('Vui lòng cung cấp attendance_excuse_id', 
                                                       ResponseFormatter.HTTP_BAD_REQUEST,
                                                       http_status_code=ResponseFormatter.HTTP_OK)
            
            if not action:
                return ResponseFormatter.error_response('Vui lòng cung cấp action', 
                                                       ResponseFormatter.HTTP_BAD_REQUEST,
                                                       http_status_code=ResponseFormatter.HTTP_OK)

            try:
                excuse = env['attendance.excuse'].sudo().browse(attendance_excuse_id)
                if not excuse.exists():
                    return ResponseFormatter.error_response('Giải trình không tồn tại', 
                                                           ResponseFormatter.HTTP_NOT_FOUND,
                                                           http_status_code=ResponseFormatter.HTTP_OK)

                if action == 'send':
                    result = excuse.api_submit_excuse(user_id)
                    message = 'Gửi giải trình thành công'
                elif action == 'draft':
                    result = excuse.api_draft_excuse(user_id)
                    message = 'Quay về nháp thành công'
                elif action == 'delete':
                    excuse.unlink()
                    cr.commit()
                    return ResponseFormatter.success_response('Xóa giải trình thành công', {'deleted': True})
                else:
                    return ResponseFormatter.error_response(f'Action không hợp lệ: {action}', 
                                                           ResponseFormatter.HTTP_BAD_REQUEST,
                                                           http_status_code=ResponseFormatter.HTTP_OK)

                cr.commit()
                return ResponseFormatter.success_response(message, result)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)



