from datetime import datetime
from odoo import http
from odoo.http import request

from .base_controller import BaseController
from .auth_controller import _verify_token_http, _get_json_data
from ..utils.response_formatter import ResponseFormatter


class EmployeeController(BaseController):
    """Controller để quản lý thông tin nhân viên"""
    pass

    @http.route('/api/v1/employee/list', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_employee_list(self):
        try:
            data = _get_json_data()
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()

            search_text = data.get('search', '')
            department_id = data.get('department_id', False)
            job_id = data.get('job_id', False)
            active = data.get('active', True)
            items_per_page = data.get('limit', 20)
            current_page = data.get('page', 1)
            offset = (current_page - 1) * items_per_page

            try:
                domain = []

                if active is not None:
                    domain.append(('active', '=', active))

                if search_text:
                    domain.append('|')
                    domain.append('|')
                    domain.append(('name', 'ilike', search_text))
                    domain.append(('work_email', 'ilike', search_text))
                    domain.append(('mobile_phone', 'ilike', search_text))

                if department_id:
                    domain.append(('department_id', '=', department_id))

                if job_id:
                    domain.append(('job_id', '=', job_id))

                employees = env['hr.employee'].sudo().search(
                    domain,
                    limit=items_per_page,
                    offset=offset,
                    order='name asc'
                )

                total_record = env['hr.employee'].sudo().search_count(domain)
                next_page = current_page + 1 if (offset + items_per_page) < total_record else None

                employee_list = []
                for emp in employees:
                    # Get base URL for image
                    base_url = env['ir.config_parameter'].sudo().get_param('web.base.url',
                                                                           'http://localhost:8069').rstrip('/')
                    img_url = f"{base_url}/web/image/hr.employee/{emp.id}?timestamp={int(datetime.now().timestamp())}" if emp.image_1920 else False

                    employee_list.append({
                        'id': emp.id,
                        'code': emp.barcode or '',
                        'name': emp.name,
                        'mobile_phone': emp.mobile_phone or False,
                        'work_phone': emp.work_phone or False,
                        'work_email': emp.work_email or False,
                        'img_url': img_url,
                        'scale_area': {
                            'name': '',
                            'code': ''
                        },
                        'subsidiary': {
                            'name': '',
                            'code': ''
                        },
                        'department_id': {
                            'name': emp.department_id.name if emp.department_id else '',
                            'code': getattr(emp.department_id, 'code', '') if emp.department_id else ''
                        },
                        'job': {
                            'name': emp.job_id.name if emp.job_id else '',
                            'code': getattr(emp.job_id, 'code', '') if emp.job_id else ''
                        },
                        'position': emp.job_title or '',
                        'tax_code': emp.identification_id or False,
                        'insurance_code': emp.permit_no or False,
                        'social_insurance_code': emp.ssnid or False,
                    })

                result = {
                    'app_data': employee_list,
                    'page': {
                        'total_record': total_record,
                        'current_page': current_page,
                        'next_page': next_page,
                        'items_per_page': items_per_page,
                    }
                }

                cr.commit()
                return ResponseFormatter.success_response('Thành công', result, ResponseFormatter.HTTP_OK)

            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/employee/detail', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_employee_detail(self):
        try:
            data = _get_json_data()
            employee_id = data.get('employee_id')
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()

            try:
                if not employee_id:
                    return ResponseFormatter.error_response(
                        'Vui lòng cung cấp employee_id',
                        ResponseFormatter.HTTP_BAD_REQUEST, http_status_code=ResponseFormatter.HTTP_OK)

                employee = env['hr.employee'].sudo().browse(employee_id)
                if not employee.exists():
                    return ResponseFormatter.error_response(
                        'Nhân viên không tồn tại',
                        ResponseFormatter.HTTP_NOT_FOUND, http_status_code=ResponseFormatter.HTTP_OK)

                # Get base URL for image
                base_url = env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069').rstrip(
                    '/')
                img_url = f"{base_url}/web/image/hr.employee/{employee.id}" if employee.image_1920 else False

                # Format date helper
                def format_date_vn(date_field):
                    if date_field:
                        return date_field.strftime('%d/%m/%Y')
                    return None

                # Helper to wrap field values
                def field_wrap(value, invisible=False):
                    return {'value': value, 'invisible': invisible}

                employee_data = {
                    'id': field_wrap(employee.id),
                    'code': field_wrap(employee.barcode or ''),
                    'name': field_wrap(employee.name),
                    'birthday': field_wrap(format_date_vn(employee.birthday)),
                    'position': field_wrap(employee.job_title or ''),
                    'mobile_phone': field_wrap(employee.mobile_phone or ''),
                    'work_phone': field_wrap(employee.work_phone or ''),
                    'work_email': field_wrap(employee.work_email or ''),
                    'img_url': field_wrap(img_url),
                    'tax_code': field_wrap(employee.identification_id or ''),
                    'insurance_code': field_wrap(employee.permit_no or ''),
                    'social_insurance_code': field_wrap(employee.ssnid or ''),
                    'phone_other': field_wrap(employee.private_phone or ''),
                    'current_address': '',
                    'default_address': False,
                    # Nested objects
                    'subsidiary': field_wrap({
                        'name': employee.company_id.name if employee.company_id else '',
                        'code': getattr(employee.company_id, 'code', '') or ''
                    }),
                    'company': field_wrap({
                        'name': employee.company_id.name if employee.company_id else ''
                    }),
                    'department': field_wrap({
                        'name': employee.department_id.name if employee.department_id else '',
                        'code': getattr(employee.department_id, 'code', '') or ''
                    }),
                    'department_parent': field_wrap({
                        'name': employee.department_id.parent_id.name if employee.department_id and employee.department_id.parent_id else '',
                        'code': getattr(employee.department_id.parent_id, 'code',
                                        '') or '' if employee.department_id and employee.department_id.parent_id else ''
                    }),
                    'job': field_wrap({
                        'name': employee.job_id.name if employee.job_id else '',
                        'code': getattr(employee.job_id, 'code', '') or ''
                    }),
                    'scale_area': field_wrap({
                        'name': '',
                        'code': ''
                    }),
                    'relation_family': field_wrap([]),
                    'training': field_wrap([]),
                    'salary': {'invisible': False},
                    'allowance': {'invisible': False},
                    'transfer': field_wrap([]),
                    'transfer_outer': field_wrap([]),
                }

                cr.commit()
                return ResponseFormatter.success_response('Thành công', {'app_data': employee_data},
                                                          ResponseFormatter.HTTP_OK)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)
