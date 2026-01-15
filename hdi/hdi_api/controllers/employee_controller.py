from odoo import http
from odoo.http import request

from ..decorators.auth import verify_token
from ..utils.request_helper import get_json_data
from ..utils.response_formatter import ResponseFormatter
from ..utils.env_helper import get_env


class EmployeeController(http.Controller):
    @http.route('/api/v1/employee/list', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def get_employee_list(self):
        try:
            request_data = {
                'user_id': request.jwt_payload.get('user_id'),
                'search': get_json_data().get('search', ''),
                'department_id': get_json_data().get('department_id', False),
                'job_id': get_json_data().get('job_id', False),
                'active': get_json_data().get('active', True),
                'limit': get_json_data().get('limit', 20),
                'page': get_json_data().get('page', 1),
            }

            env, cr = get_env()

            result_data = env['hr.employee'].api_get_employee_list(request_data)

            cr.commit()
            return ResponseFormatter.success_response('Thành công', result_data, ResponseFormatter.HTTP_OK)

        except Exception as e:
            cr.rollback()
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/employee/detail', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def get_employee_detail(self):
        try:
            request_data = {
                'user_id': request.jwt_payload.get('user_id'),
                'employee_id': get_json_data().get('employee_id'),
            }

            env, cr = get_env()

            result_data = env['hr.employee'].api_get_employee_detail(request_data)

            cr.commit()
            return ResponseFormatter.success_response('Thành công', result_data, ResponseFormatter.HTTP_OK)

        except ValueError as e:
            cr.rollback()
            return ResponseFormatter.error_response(str(e), ResponseFormatter.HTTP_BAD_REQUEST,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

        except LookupError as e:
            cr.rollback()
            return ResponseFormatter.error_response(str(e), ResponseFormatter.HTTP_NOT_FOUND,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

        except PermissionError as e:
            cr.rollback()
            return ResponseFormatter.error_response(str(e), ResponseFormatter.HTTP_FORBIDDEN,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

        except Exception as e:
            cr.rollback()
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/employee/get-departments-and-employee', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def get_departments_and_employee(self):
        try:
            request_data = {
                'user_id': request.jwt_payload.get('user_id'),
            }

            env, cr = get_env()

            result_data = env['hr.employee'].api_get_departments_and_employee(request_data)

            cr.commit()
            return ResponseFormatter.success_response('Thành công', result_data, ResponseFormatter.HTTP_OK)

        except ValueError as e:
            cr.rollback()
            return ResponseFormatter.error_response(str(e), ResponseFormatter.HTTP_BAD_REQUEST,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

        except LookupError as e:
            cr.rollback()
            return ResponseFormatter.error_response(str(e), ResponseFormatter.HTTP_NOT_FOUND,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

        except PermissionError as e:
            cr.rollback()
            return ResponseFormatter.error_response(str(e), ResponseFormatter.HTTP_FORBIDDEN,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

        except Exception as e:
            cr.rollback()
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/hr/get-employee-new', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def get_employee_new(self):
        try:
            env, cr = get_env()

            result_data = env['hr.employee'].api_get_employee_new()

            cr.commit()
            return ResponseFormatter.success_response('Thành công', result_data, ResponseFormatter.HTTP_OK)

        except Exception as e:
            cr.rollback()
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/hr/get-birthday', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def get_birthday(self):
        try:
            env, cr = get_env()

            result_data = env['hr.employee'].api_get_birthday()

            cr.commit()
            return ResponseFormatter.success_response('Thành công', result_data, ResponseFormatter.HTTP_OK)

        except Exception as e:
            cr.rollback()
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)