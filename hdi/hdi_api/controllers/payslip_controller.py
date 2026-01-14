from datetime import datetime
from odoo import http
from odoo.http import request

from ..decorators.auth import verify_token
from ..utils.request_helper import get_json_data
from ..utils.response_formatter import ResponseFormatter
from ..utils.env_helper import get_env


class PayslipController(http.Controller):

    @http.route('/api/v1/payslip/list', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def get_payslip_list(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                result = env['hr.payslip'].sudo().api_get_payslip_list(user_id)
                cr.commit()
                
                return ResponseFormatter.success_response(
                    'Lấy danh sách bảng lương thành công',
                    {'payslips': result, 'total': len(result)},
                    ResponseFormatter.HTTP_OK
                )
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(
                f'Lỗi: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR, http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/payslip/detail', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def get_payslip_detail(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            data = get_json_data()
            employee_id = data.get('employee_id')
            month = data.get('month')
            env, cr = get_env()

            try:
                result = env['hr.payslip'].sudo().api_get_payslip_detail(employee_id, month, user_id)
                cr.commit()
                
                return ResponseFormatter.success_response(
                    'Lấy chi tiết bảng lương thành công',
                    result,
                    ResponseFormatter.HTTP_OK
                )
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(
                f'Lỗi: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR, http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/payslip/data', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def get_payslip_data(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            data = get_json_data()
            employee_id = data.get('employee_id')
            env, cr = get_env()

            try:
                result = env['hr.payslip'].sudo().api_get_payslip_data(employee_id, user_id)
                cr.commit()
                
                return ResponseFormatter.success_response(
                    'Lấy dữ liệu bảng lương thành công',
                    result,
                    ResponseFormatter.HTTP_OK
                )
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(
                f'Lỗi: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR, http_status_code=ResponseFormatter.HTTP_OK)


