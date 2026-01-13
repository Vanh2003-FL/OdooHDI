import json
from datetime import datetime, timedelta
from odoo import http
from odoo.http import request

from .auth_controller import _verify_token
from ..utils.response_formatter import ResponseFormatter


class AttendanceAPI(http.Controller):
    def _get_env(self):
        db_name = request.jwt_payload.get('db')
        import odoo
        from odoo.modules.registry import Registry

        registry = Registry(db_name)
        cr = registry.cursor()
        return odoo.api.Environment(cr, odoo.SUPERUSER_ID, {}), cr

    def _get_request_data(self):
        try:
            body = request.httprequest.get_data(as_text=True)
            if body:
                data = json.loads(body)
                return data
        except Exception as e:
            pass

        form_data = request.httprequest.form.to_dict()
        return form_data

    @http.route('/api/v1/attendance/check-in', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def check_in(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()

            try:
                data = self._get_request_data()
                in_latitude = data.get('in_latitude')
                in_longitude = data.get('in_longitude')

                employee = env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
                result = env['hr.attendance'].api_check_in(employee.id, in_latitude, in_longitude)
                cr.commit()

                return ResponseFormatter.success_response('Chấm công vào thành công', result, ResponseFormatter.HTTP_OK)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/attendance/check-out', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def check_out(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()

            try:
                data = self._get_request_data()
                out_latitude = data.get('out_latitude')
                out_longitude = data.get('out_longitude')

                employee = env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
                result = env['hr.attendance'].api_check_out(employee.id, out_latitude, out_longitude)
                cr.commit()

                return ResponseFormatter.success_response('Chấm công ra thành công', result, ResponseFormatter.HTTP_OK)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/attendance/status', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def get_status(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()

            try:
                employee = env['hr.employee'].search([('user_id', '=', user_id)], limit=1)

                current_attendance = env['hr.attendance'].search([
                    ('employee_id', '=', employee.id),
                    ('check_out', '=', False)
                ], limit=1)

                if current_attendance:
                    result = {
                        'is_checked_in': True,
                        'attendance_id': current_attendance.id,
                        'check_in': current_attendance.check_in.isoformat() if current_attendance.check_in else None,
                        'in_latitude': current_attendance.in_latitude,
                        'in_longitude': current_attendance.in_longitude,
                        'employee_name': employee.name,
                    }
                else:
                    result = {
                        'is_checked_in': False,
                        'employee_name': employee.name,
                    }

                cr.commit()
                return ResponseFormatter.success_response('Trạng thái chấm công', result, ResponseFormatter.HTTP_OK)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/attendance/history', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def get_history(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()

            try:
                data = self._get_request_data()
                limit = int(data.get('limit', 30))
                offset = int(data.get('offset', 0))
                from_date = data.get('from_date')
                to_date = data.get('to_date')

                employee = env['hr.employee'].search([('user_id', '=', user_id)], limit=1)

                domain = [('employee_id', '=', employee.id)]

                if from_date:
                    from_datetime = datetime.strptime(from_date, '%Y-%m-%d')
                    domain.append(('check_in', '>=', from_datetime))

                if to_date:
                    to_datetime = datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1)
                    domain.append(('check_in', '<', to_datetime))

                attendances = env['hr.attendance'].search(domain, limit=limit, offset=offset, order='check_in desc')
                total_count = env['hr.attendance'].search_count(domain)

                attendance_list = []
                for att in attendances:
                    worked_hours = att.worked_hours if hasattr(att, 'worked_hours') else 0
                    attendance_list.append({
                        'id': att.id,
                        'check_in': att.check_in.isoformat() if att.check_in else None,
                        'check_out': att.check_out.isoformat() if att.check_out else None,
                        'in_latitude': att.in_latitude,
                        'in_longitude': att.in_longitude,
                        'out_latitude': att.out_latitude,
                        'out_longitude': att.out_longitude,
                        'worked_hours': worked_hours,
                    })

                result = {
                    'employee_name': employee.name,
                    'attendances': attendance_list,
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset,
                }

                cr.commit()
                return ResponseFormatter.success_response('Lịch sử chấm công', result, ResponseFormatter.HTTP_OK)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/attendance/summary', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def get_summary(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()

            try:
                data = self._get_request_data()
                month = data.get('month', datetime.now().strftime('%Y-%m'))

                year, month_num = map(int, month.split('-'))
                from_date = datetime(year, month_num, 1)

                if month_num == 12:
                    to_date = datetime(year + 1, 1, 1)
                else:
                    to_date = datetime(year, month_num + 1, 1)

                employee = env['hr.employee'].search([('user_id', '=', user_id)], limit=1)

                attendances = env['hr.attendance'].search([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', from_date),
                    ('check_in', '<', to_date),
                ])

                total_days = 0
                total_hours = 0
                incomplete_days = 0

                for att in attendances:
                    if att.check_in:
                        total_days += 1
                        if att.check_out:
                            worked_hours = att.worked_hours if hasattr(att, 'worked_hours') else 0
                            total_hours += worked_hours
                        else:
                            incomplete_days += 1

                result = {
                    'employee_name': employee.name,
                    'month': month,
                    'total_days': total_days,
                    'total_hours': round(total_hours, 2),
                    'incomplete_days': incomplete_days,
                    'average_hours_per_day': round(total_hours / total_days, 2) if total_days > 0 else 0,
                }

                cr.commit()
                return ResponseFormatter.success_response('Tổng hợp chấm công', result, ResponseFormatter.HTTP_OK)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)
