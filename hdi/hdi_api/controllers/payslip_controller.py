from datetime import datetime
from odoo import http
from odoo.http import request

from .auth_controller import _verify_token
from ..utils.response_formatter import ResponseFormatter
from ..utils.env_helper import get_env


class PayslipController(http.Controller):

    @http.route('/api/v1/payslip/list', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def get_payslip_list(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                employee = env['hr.employee'].search([('user_id', '=', user_id)], limit=1)

                if not employee:
                    return ResponseFormatter.error_response(
                        'Không tìm thấy thông tin nhân viên',
                        ResponseFormatter.HTTP_NOT_FOUND, http_status_code=ResponseFormatter.HTTP_OK)

                # Lấy danh sách payslip
                payslips = env['hr.payslip'].search(
                    [('employee_id', '=', employee.id)],
                    order='date_from desc',
                    limit=100
                )

                result = []
                for payslip in payslips:
                    result.append({
                        'id': payslip.id,
                        'name': payslip.name,
                        'number': payslip.number,
                        'date_from': payslip.date_from.isoformat() if payslip.date_from else None,
                        'date_to': payslip.date_to.isoformat() if payslip.date_to else None,
                        'state': payslip.state,
                        'basic_wage': payslip.basic_wage,
                        'gross_wage': payslip.gross_wage,
                        'net_wage': payslip.net_wage,
                        'created_date': payslip.create_date.isoformat() if payslip.create_date else None,
                    })

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
    @_verify_token
    def get_payslip_detail(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                import json
                from datetime import datetime, timedelta
                
                data = json.loads(request.httprequest.data.decode('utf-8'))
                employee_id = data.get('employee_id')
                month = data.get('month')

                if not employee_id:
                    return ResponseFormatter.error_response(
                        'employee_id là bắt buộc',
                        ResponseFormatter.HTTP_BAD_REQUEST, http_status_code=ResponseFormatter.HTTP_OK)

                if not month:
                    return ResponseFormatter.error_response(
                        'month là bắt buộc (định dạng: YYYY-MM)',
                        ResponseFormatter.HTTP_BAD_REQUEST, http_status_code=ResponseFormatter.HTTP_OK)

                try:
                    employee_id = int(employee_id)
                except (ValueError, TypeError):
                    return ResponseFormatter.error_response(
                        'employee_id phải là số',
                        ResponseFormatter.HTTP_BAD_REQUEST, http_status_code=ResponseFormatter.HTTP_OK)

                # Lấy user hiện tại
                current_user = env['res.users'].browse(user_id)

                # Kiểm tra quyền: chỉ admin hoặc chính nhân viên đó mới có thể xem
                is_admin = current_user.has_group('base.group_system')
                current_employee = env['hr.employee'].search([('user_id', '=', user_id)], limit=1)

                if not is_admin and (not current_employee or current_employee.id != employee_id):
                    return ResponseFormatter.error_response(
                        'Bạn không có quyền xem dữ liệu của nhân viên này',
                        ResponseFormatter.HTTP_FORBIDDEN, http_status_code=ResponseFormatter.HTTP_OK)

                # Kiểm tra employee tồn tại
                employee = env['hr.employee'].browse(employee_id)
                if not employee.exists():
                    return ResponseFormatter.error_response(
                        'Không tìm thấy nhân viên',
                        ResponseFormatter.HTTP_NOT_FOUND, http_status_code=ResponseFormatter.HTTP_OK)

                # Parse month và lấy date_from, date_to
                try:
                    date_from = datetime.strptime(month + '-01', '%Y-%m-%d').date()
                    if date_from.month == 12:
                        date_to = date_from.replace(year=date_from.year + 1, month=1, day=1)
                    else:
                        date_to = date_from.replace(month=date_from.month + 1, day=1)
                    date_to = (date_to - timedelta(days=1))
                except ValueError:
                    return ResponseFormatter.error_response(
                        'month phải có định dạng: YYYY-MM',
                        ResponseFormatter.HTTP_BAD_REQUEST, http_status_code=ResponseFormatter.HTTP_OK)

                # Lấy payslip theo employee_id và month
                payslip = env['hr.payslip'].search([
                    ('employee_id', '=', employee_id),
                    ('date_from', '>=', date_from),
                    ('date_to', '<=', date_to)
                ], limit=1, order='date_from desc')

                if not payslip:
                    return ResponseFormatter.error_response(
                        'Không tìm thấy phiếu lương cho tháng này',
                        ResponseFormatter.HTTP_NOT_FOUND, http_status_code=ResponseFormatter.HTTP_OK)

                # Xây dựng dữ liệu chi tiết
                values = {
                    'employee': {
                        'name': payslip.employee_id.name,
                        'id': payslip.employee_id.id,
                        'department': payslip.employee_id.department_id.name if payslip.employee_id.department_id else '',
                        'email': payslip.employee_id.work_email or '',
                    },
                    'name': payslip.name,
                    'date_from': payslip.date_from.strftime('%d/%m/%Y') if payslip.date_from else None,
                    'date_to': payslip.date_to.strftime('%d/%m/%Y') if payslip.date_to else None,
                    'code': payslip.number or '',
                    'contract': {
                        'id': payslip.contract_id.id if payslip.contract_id else None,
                        'name': payslip.contract_id.name if payslip.contract_id else '',
                    },
                    'struct_id': {
                        'id': payslip.struct_id.id if payslip.struct_id else None,
                        'name': payslip.struct_id.name if payslip.struct_id else '',
                    },
                    'lines': []
                }

                # Chi tiết các quy tắc lương
                for line in payslip.line_ids.sorted(lambda l: l.sequence):
                    values['lines'].append({
                        'name': line.name,
                        'code': line.code,
                        'category_id': {
                            'id': line.category_id.id if line.category_id else None,
                            'name': line.category_id.name if line.category_id else '',
                        },
                        'quantity': line.quantity,
                        'rate': line.rate,
                        'amount': line.amount,
                        'total': line.total,
                        'number_order': line.sequence,
                    })

                result = {'values': [values]}

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
    @_verify_token
    def get_payslip_data(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                import json
                data = json.loads(request.httprequest.data.decode('utf-8'))
                employee_id = data.get('employee_id')

                if not employee_id:
                    return ResponseFormatter.error_response(
                        'employee_id là bắt buộc',
                        ResponseFormatter.HTTP_BAD_REQUEST, http_status_code=ResponseFormatter.HTTP_OK)

                try:
                    employee_id = int(employee_id)
                except (ValueError, TypeError):
                    return ResponseFormatter.error_response(
                        'employee_id phải là số',
                        ResponseFormatter.HTTP_BAD_REQUEST, http_status_code=ResponseFormatter.HTTP_OK)

                # Lấy user hiện tại
                current_user = env['res.users'].browse(user_id)

                # Kiểm tra quyền: chỉ admin hoặc chính nhân viên đó mới có thể xem
                is_admin = current_user.has_group('base.group_system')
                current_employee = env['hr.employee'].search([('user_id', '=', user_id)], limit=1)

                if not is_admin and (not current_employee or current_employee.id != employee_id):
                    return ResponseFormatter.error_response(
                        'Bạn không có quyền xem dữ liệu của nhân viên này',
                        ResponseFormatter.HTTP_FORBIDDEN, http_status_code=ResponseFormatter.HTTP_OK)

                # Kiểm tra employee tồn tại
                employee = env['hr.employee'].browse(employee_id)
                if not employee.exists():
                    return ResponseFormatter.error_response(
                        'Không tìm thấy nhân viên',
                        ResponseFormatter.HTTP_NOT_FOUND, http_status_code=ResponseFormatter.HTTP_OK)

                # Lấy danh sách payslip
                payslips = env['hr.payslip'].search(
                    [('employee_id', '=', employee_id)],
                    order='date_from desc',
                    limit=100
                )

                result = []
                for payslip in payslips:
                    result.append({
                        'id': payslip.id,
                        'name': payslip.name,
                        'number': payslip.number,
                        'date_from': payslip.date_from.isoformat() if payslip.date_from else None,
                        'date_to': payslip.date_to.isoformat() if payslip.date_to else None,
                        'state': payslip.state,
                        'basic_wage': payslip.basic_wage,
                        'gross_wage': payslip.gross_wage,
                        'net_wage': payslip.net_wage,
                        'created_date': payslip.create_date.isoformat() if payslip.create_date else None,
                    })

                cr.commit()
                return ResponseFormatter.success_response(
                    'Lấy dữ liệu bảng lương thành công',
                    {
                        'employee_id': employee_id,
                        'employee_name': employee.name,
                        'payslips': result,
                        'total': len(result)
                    },
                    ResponseFormatter.HTTP_OK
                )
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(
                f'Lỗi: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR, http_status_code=ResponseFormatter.HTTP_OK)
