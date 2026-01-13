from odoo import http
from odoo.http import request

from .auth_controller import _verify_token_http, _get_json_data
from ..utils.response_formatter import ResponseFormatter
from ..utils.env_helper import get_env


class EmployeeController(http.Controller):

    @http.route('/api/v1/employee/list', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_employee_list(self):
        try:
            data = _get_json_data()
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            search_text = data.get('search', '')
            department_id = data.get('department_id', False)
            job_id = data.get('job_id', False)
            active = data.get('active', True)
            items_per_page = data.get('limit', 20)
            current_page = data.get('page', 1)
            offset = (current_page - 1) * items_per_page

            result_data = env['hr.employee'].get_employee_list_api(
                current_user_id=user_id,
                search_text=search_text,
                department_id=department_id,
                job_id=job_id,
                active=active,
                limit=items_per_page,
                offset=offset
            )

            result = {
                'app_data': result_data['employees'],
                'page': {
                    'total_record': result_data['total_record'],
                    'current_page': result_data['current_page'],
                    'next_page': result_data['next_page'],
                    'items_per_page': result_data['items_per_page'],
                }
            }

            cr.commit()
            return ResponseFormatter.success_response('Thành công', result, ResponseFormatter.HTTP_OK)

        except Exception as e:
            cr.rollback()
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/employee/detail', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_employee_detail(self):
        try:
            data = _get_json_data()
            employee_id = data.get('employee_id')
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            if not employee_id:
                return ResponseFormatter.error_response(
                    'Vui lòng cung cấp employee_id',
                    ResponseFormatter.HTTP_BAD_REQUEST, http_status_code=ResponseFormatter.HTTP_OK)

            employee_data = env['hr.employee'].get_employee_detail_api(
                current_user_id=user_id,
                employee_id=employee_id
            )

            if employee_data is None:
                return ResponseFormatter.error_response(
                    'Nhân viên không tồn tại',
                    ResponseFormatter.HTTP_NOT_FOUND, http_status_code=ResponseFormatter.HTTP_OK)

            cr.commit()
            return ResponseFormatter.success_response('Thành công', {'app_data': employee_data},
                                                      ResponseFormatter.HTTP_OK)

        except Exception as e:
            cr.rollback()
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)
