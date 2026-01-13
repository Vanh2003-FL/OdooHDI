import json
from datetime import datetime
from odoo import http
from odoo.http import request

from .auth_controller import _verify_token_http, _get_json_data
from ..utils.response_formatter import ResponseFormatter
from ..utils.env_helper import get_env


class ApprovalController(http.Controller):

    def _can_approve_leave(self, leave, user, user_id):
        """
        Kiểm tra xem user có quyền approve leave không
        Theo logic của Odoo hr.leave
        """
        validation_type = leave.holiday_status_id.leave_validation_type if leave.holiday_status_id else 'no_validation'
        employee = leave.employee_id
        
        # Admin hoặc HR Manager luôn có quyền
        if user.has_group('base.group_system') or user.has_group('hr_holidays.group_hr_holidays_manager'):
            return True
        
        # Không thể approve đơn của chính mình (trừ khi là admin/manager)
        if employee.user_id.id == user_id:
            return False
        
        is_hr_officer = user.has_group('hr_holidays.group_hr_holidays_user')
        is_leave_manager = employee.leave_manager_id and employee.leave_manager_id.user_id.id == user_id
        is_parent_manager = employee.parent_id and employee.parent_id.user_id.id == user_id
        is_dept_manager = employee.department_id and employee.department_id.manager_id and employee.department_id.manager_id.user_id.id == user_id
        
        # Lấy department của user hiện tại
        user_employee = user.env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
        same_department = user_employee and employee.department_id and user_employee.department_id.id == employee.department_id.id
        
        # Employee không có manager và không có department manager
        no_manager = not employee.leave_manager_id and not employee.parent_id and not is_dept_manager
        
        # Kiểm tra theo validation_type
        if leave.state == 'confirm':
            # First approval
            if validation_type == 'hr':
                # HR Officer có thể approve nếu:
                if is_hr_officer and (is_leave_manager or is_dept_manager or same_department or no_manager):
                    return True
            
            elif validation_type == 'manager':
                # Manager hoặc HR Officer (trong điều kiện nhất định)
                if is_leave_manager or is_parent_manager or is_dept_manager:
                    return True
                if is_hr_officer and no_manager:
                    return True
            
            elif validation_type == 'both':
                # Lần approve đầu: giống như HR validation
                if is_leave_manager or is_parent_manager or is_dept_manager:
                    return True
                if is_hr_officer and (is_dept_manager or same_department or no_manager):
                    return True
        
        elif leave.state == 'validate1':
            # Second approval (chỉ cho 'both' validation)
            if validation_type == 'both' and is_hr_officer:
                return True
        
        return False

    def _can_refuse_leave(self, leave, user, user_id):
        """
        Kiểm tra xem user có quyền refuse leave không
        HR Officer có thể refuse tất cả leaves (theo docstring)
        """
        # Admin hoặc HR Manager luôn có quyền
        if user.has_group('base.group_system') or user.has_group('hr_holidays.group_hr_holidays_manager'):
            return True
        
        # HR Officer có thể refuse tất cả
        if user.has_group('hr_holidays.group_hr_holidays_user'):
            return True
        
        # Manager cũng có thể refuse
        employee = leave.employee_id
        is_leave_manager = employee.leave_manager_id and employee.leave_manager_id.user_id.id == user_id
        is_parent_manager = employee.parent_id and employee.parent_id.user_id.id == user_id
        is_dept_manager = employee.department_id and employee.department_id.manager_id and employee.department_id.manager_id.user_id.id == user_id
        
        if is_leave_manager or is_parent_manager or is_dept_manager:
            return True
        
        return False

    @http.route('/api/v1/approval/get_approved', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_approved(self):
        """
        API lấy danh sách các đơn từ đã phê duyệt
        - Leaves ở state 'validate' (Approved)
        - Timesheet excuses ở state approved
        - Filtered by date range
        """
        try:
            data = _get_json_data()
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                from_date = data.get('from_date', '')
                to_date = data.get('to_date', '')
                approval_type = data.get('type', 'all')

                # Parse dates
                from_datetime = None
                to_datetime = None

                if from_date:
                    try:
                        from_datetime = datetime.strptime(from_date, '%Y-%m-%d')
                    except ValueError:
                        return ResponseFormatter.error_response(
                            'Định dạng from_date không hợp lệ (yyyy-mm-dd)',
                            ResponseFormatter.HTTP_BAD_REQUEST,
                            http_status_code=ResponseFormatter.HTTP_OK)

                if to_date:
                    try:
                        to_datetime = datetime.strptime(to_date, '%Y-%m-%d')
                    except ValueError:
                        return ResponseFormatter.error_response(
                            'Định dạng to_date không hợp lệ (yyyy-mm-dd)',
                            ResponseFormatter.HTTP_BAD_REQUEST,
                            http_status_code=ResponseFormatter.HTTP_OK)

                # Validate approval_type
                if approval_type not in ['leave', 'Timesheet', 'all']:
                    return ResponseFormatter.error_response(
                        'type phải là: leave, Timesheet hoặc all',
                        ResponseFormatter.HTTP_BAD_REQUEST,
                        http_status_code=ResponseFormatter.HTTP_OK)

                # Get user
                user = env['res.users'].browse(user_id)
                if not user.exists():
                    return ResponseFormatter.error_response(
                        'Không tìm thấy thông tin người dùng',
                        ResponseFormatter.HTTP_NOT_FOUND,
                        http_status_code=ResponseFormatter.HTTP_OK)

                approved_list = []

                # Fetch Approved Leaves (state = 'validate')
                if approval_type in ['leave', 'all']:
                    leave_domain = [
                        ('state', '=', 'validate'),
                    ]

                    # Add date range filter if provided
                    if from_datetime:
                        leave_domain.append(('request_date_from', '>=', from_datetime))
                    if to_datetime:
                        leave_domain.append(('request_date_to', '<=', to_datetime))

                    leaves = env['hr.leave'].search(leave_domain, order='create_date desc')

                    for leave in leaves:
                        validation_type = leave.holiday_status_id.leave_validation_type if leave.holiday_status_id else 'no_validation'
                        
                        approved_list.append({
                            'id': leave.id,
                            'name': leave.name,
                            'type': 'leave',
                            'employee_name': leave.employee_id.name,
                            'employee_id': leave.employee_id.id,
                            'request_date_from': leave.request_date_from.isoformat() if leave.request_date_from else None,
                            'request_date_to': leave.request_date_to.isoformat() if leave.request_date_to else None,
                            'leave_type_id': leave.holiday_status_id.id if leave.holiday_status_id else False,
                            'leave_type': leave.holiday_status_id.name if leave.holiday_status_id else '',
                            'number_of_days': leave.number_of_days,
                            'state': leave.state,
                            'validation_type': validation_type,
                            'first_approver_id': leave.first_approver_id.id if leave.first_approver_id else None,
                            'first_approver_name': leave.first_approver_id.name if leave.first_approver_id else None,
                            'second_approver_id': leave.second_approver_id.id if leave.second_approver_id else None,
                            'second_approver_name': leave.second_approver_id.name if leave.second_approver_id else None,
                            'create_date': leave.create_date.isoformat() if leave.create_date else None,
                        })

                # Fetch Approved Timesheet (Attendance Excuse)
                if approval_type in ['Timesheet', 'all']:
                    excuse_domain = [
                        ('state', '=', 'approved'),
                    ]

                    if from_datetime:
                        excuse_domain.append(('date', '>=', from_datetime.date()))
                    if to_datetime:
                        excuse_domain.append(('date', '<=', to_datetime.date()))

                    excuses = env['attendance.excuse'].search(excuse_domain, order='create_date desc')

                    for excuse in excuses:
                        approved_list.append({
                            'id': excuse.id,
                            'name': excuse.display_name,
                            'type': 'Timesheet',
                            'employee_name': excuse.employee_id.name,
                            'employee_id': excuse.employee_id.id,
                            'date': excuse.date.isoformat() if excuse.date else None,
                            'reason': excuse.reason,
                            'requested_checkin': excuse.requested_checkin.isoformat() if excuse.requested_checkin else None,
                            'requested_checkout': excuse.requested_checkout.isoformat() if excuse.requested_checkout else None,
                            'original_checkin': excuse.original_checkin.isoformat() if excuse.original_checkin else None,
                            'original_checkout': excuse.original_checkout.isoformat() if excuse.original_checkout else None,
                            'state': excuse.state,
                            'create_date': excuse.create_date.isoformat() if excuse.create_date else None,
                        })

                # Sort by creation date descending
                approved_list.sort(key=lambda x: x['create_date'] or '', reverse=True)

                result = {
                    'approved': approved_list,
                    'total_count': len(approved_list),
                    'type_filter': approval_type,
                    'from_date': from_date,
                    'to_date': to_date,
                }

                cr.commit()
                return ResponseFormatter.success_response(
                    'Lấy danh sách đơn đã phê duyệt thành công',
                    result,
                    ResponseFormatter.HTTP_OK
                )

            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(
                f'Lỗi: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR,
                http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/approval/get_approvals_single', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_approvals_single(self):
        try:
            data = _get_json_data()
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                from_date = data.get('from_date', '')
                to_date = data.get('to_date', '')
                approval_type = data.get('type', 'all')

                from_datetime = None
                to_datetime = None

                if from_date:
                    try:
                        from_datetime = datetime.strptime(from_date, '%Y-%m-%d')
                    except ValueError:
                        return ResponseFormatter.error_response(
                            'Định dạng from_date không hợp lệ (yyyy-mm-dd)',
                            ResponseFormatter.HTTP_BAD_REQUEST,
                            http_status_code=ResponseFormatter.HTTP_OK)

                if to_date:
                    try:
                        to_datetime = datetime.strptime(to_date, '%Y-%m-%d')
                    except ValueError:
                        return ResponseFormatter.error_response(
                            'Định dạng to_date không hợp lệ (yyyy-mm-dd)',
                            ResponseFormatter.HTTP_BAD_REQUEST,
                            http_status_code=ResponseFormatter.HTTP_OK)

                if approval_type not in ['leave', 'Timesheet', 'all']:
                    return ResponseFormatter.error_response(
                        'type phải là: leave, Timesheet hoặc all',
                        ResponseFormatter.HTTP_BAD_REQUEST,
                        http_status_code=ResponseFormatter.HTTP_OK)

                user = env['res.users'].browse(user_id)
                if not user.exists():
                    return ResponseFormatter.error_response(
                        'Không tìm thấy thông tin người dùng',
                        ResponseFormatter.HTTP_NOT_FOUND,
                        http_status_code=ResponseFormatter.HTTP_OK)

                is_admin = user.has_group('base.group_system')

                approvals_list = []

                if approval_type in ['leave', 'all']:
                    leave_domain = [
                        ('state', 'in', ['confirm', 'validate1']),
                    ]

                    if from_datetime:
                        leave_domain.append(('request_date_from', '>=', from_datetime))
                    if to_datetime:
                        leave_domain.append(('request_date_to', '<=', to_datetime))

                    leaves = env['hr.leave'].search(leave_domain)

                    for leave in leaves:
                        can_view = is_admin or self._can_approve_leave(leave, user, user_id)
                        
                        if can_view:
                            validation_type = leave.holiday_status_id.leave_validation_type if leave.holiday_status_id else 'no_validation'
                            
                            approvals_list.append({
                                'id': leave.id,
                                'name': leave.name,
                                'type': 'leave',
                                'employee_name': leave.employee_id.name,
                                'employee_id': leave.employee_id.id,
                                'request_date_from': leave.request_date_from.isoformat() if leave.request_date_from else None,
                                'request_date_to': leave.request_date_to.isoformat() if leave.request_date_to else None,
                                'leave_type_id': leave.holiday_status_id.id if leave.holiday_status_id else False,
                                'leave_type': leave.holiday_status_id.name if leave.holiday_status_id else '',
                                'number_of_days': leave.number_of_days,
                                'state': leave.state,
                                'validation_type': validation_type,
                                'create_date': leave.create_date.isoformat() if leave.create_date else None,
                            })

                if approval_type in ['Timesheet', 'all']:
                    excuse_domain = [
                        ('state', '=', 'submitted'),
                    ]

                    if from_datetime:
                        excuse_domain.append(('date', '>=', from_datetime.date()))
                    if to_datetime:
                        excuse_domain.append(('date', '<=', to_datetime.date()))

                    excuses = env['attendance.excuse'].search(excuse_domain)

                    for excuse in excuses:
                        can_view = is_admin or (excuse.employee_id.parent_id and excuse.employee_id.parent_id.user_id.id == user_id)
                        
                        if can_view:
                            approvals_list.append({
                                'id': excuse.id,
                                'name': excuse.display_name,
                                'type': 'Timesheet',
                                'employee_name': excuse.employee_id.name,
                                'employee_id': excuse.employee_id.id,
                                'date': excuse.date.isoformat() if excuse.date else None,
                                'reason': excuse.reason,
                                'requested_checkin': excuse.requested_checkin.isoformat() if excuse.requested_checkin else None,
                                'requested_checkout': excuse.requested_checkout.isoformat() if excuse.requested_checkout else None,
                                'original_checkin': excuse.original_checkin.isoformat() if excuse.original_checkin else None,
                                'original_checkout': excuse.original_checkout.isoformat() if excuse.original_checkout else None,
                                'state': excuse.state,
                                'create_date': excuse.create_date.isoformat() if excuse.create_date else None,
                            })

                approvals_list.sort(key=lambda x: x['create_date'] or '', reverse=True)

                result = {
                    'approvals': approvals_list,
                    'total_count': len(approvals_list),
                    'type_filter': approval_type,
                    'is_admin': is_admin,
                }

                cr.commit()
                return ResponseFormatter.success_response(
                    'Lấy danh sách đơn cần phê duyệt thành công',
                    result,
                    ResponseFormatter.HTTP_OK
                )

            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(
                f'Lỗi: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR,
                http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/approval/action', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def action_approval(self):
        try:
            data = _get_json_data()
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                model_name = data.get('model')
                record_id = data.get('id')
                action = data.get('action')
                note = data.get('note', '')

                # Validate required fields
                if not model_name:
                    return ResponseFormatter.error_response(
                        'model là bắt buộc',
                        ResponseFormatter.HTTP_BAD_REQUEST,
                        http_status_code=ResponseFormatter.HTTP_OK)

                if not record_id:
                    return ResponseFormatter.error_response(
                        'id là bắt buộc',
                        ResponseFormatter.HTTP_BAD_REQUEST,
                        http_status_code=ResponseFormatter.HTTP_OK)

                if not action:
                    return ResponseFormatter.error_response(
                        'action là bắt buộc',
                        ResponseFormatter.HTTP_BAD_REQUEST,
                        http_status_code=ResponseFormatter.HTTP_OK)

                # Validate model
                if model_name not in ['attendance.excuse', 'hr.leave']:
                    return ResponseFormatter.error_response(
                        'model phải là: attendance.excuse hoặc hr.leave',
                        ResponseFormatter.HTTP_BAD_REQUEST,
                        http_status_code=ResponseFormatter.HTTP_OK)

                # Validate action
                if action not in ['accept', 'reject', 'draft']:
                    return ResponseFormatter.error_response(
                        'action phải là: accept, reject hoặc draft',
                        ResponseFormatter.HTTP_BAD_REQUEST,
                        http_status_code=ResponseFormatter.HTTP_OK)

                # Reject action requires note
                if action == 'reject' and not note:
                    return ResponseFormatter.error_response(
                        'note là bắt buộc cho hành động reject',
                        ResponseFormatter.HTTP_BAD_REQUEST,
                        http_status_code=ResponseFormatter.HTTP_OK)

                # Get record
                record = env[model_name].browse(record_id)
                if not record.exists():
                    return ResponseFormatter.error_response(
                        f'Không tìm thấy {model_name} với id {record_id}',
                        ResponseFormatter.HTTP_NOT_FOUND,
                        http_status_code=ResponseFormatter.HTTP_OK)

                # Get user and employee
                user = env['res.users'].browse(user_id)
                employee = env['hr.employee'].search([('user_id', '=', user_id)], limit=1)

                result = {}

                # Handle attendance.excuse
                if model_name == 'attendance.excuse':
                    if action == 'accept':
                        result = record.api_approve_excuse(user_id)
                        result['message'] = 'Phê duyệt thành công'

                    elif action == 'reject':
                        result = record.api_reject_excuse(user_id, note)
                        result['message'] = 'Từ chối thành công'

                    elif action == 'draft':
                        result = record.api_draft_excuse(user_id)
                        result['message'] = 'Quay về nháp thành công'

                # Handle hr.leave
                elif model_name == 'hr.leave':
                    if action == 'accept':
                        # Validate state - theo Odoo có thể approve từ 'confirm' hoặc 'validate1'
                        if record.state not in ['confirm', 'validate1']:
                            return ResponseFormatter.error_response(
                                f'Chỉ có thể phê duyệt đơn ở trạng thái confirm hoặc validate1, hiện tại: {record.state}',
                                ResponseFormatter.HTTP_BAD_REQUEST,
                                http_status_code=ResponseFormatter.HTTP_OK)
                        
                        # Kiểm tra quyền phê duyệt
                        if not self._can_approve_leave(record, user, user_id):
                            return ResponseFormatter.error_response(
                                'Bạn không có quyền phê duyệt đơn này',
                                ResponseFormatter.HTTP_FORBIDDEN,
                                http_status_code=ResponseFormatter.HTTP_OK)
                        
                        # Determine next state
                        validation_type = record.holiday_status_id.leave_validation_type if record.holiday_status_id else 'no_validation'
                        write_vals = {}
                        
                        if record.state == 'confirm':
                            if validation_type == 'both':
                                # First approval → validate1
                                write_vals['state'] = 'validate1'
                                write_vals['first_approver_id'] = employee.id if employee else False
                            else:
                                # Single approval → validate
                                write_vals['state'] = 'validate'
                                write_vals['first_approver_id'] = employee.id if employee else False
                        
                        elif record.state == 'validate1':
                            # Second approval → validate
                            write_vals['state'] = 'validate'
                            write_vals['second_approver_id'] = employee.id if employee else False
                        
                        record.write(write_vals)
                        
                        # Nếu state = validate, cần tạo calendar entries
                        if write_vals.get('state') == 'validate':
                            record._validate_leave_request()
                        
                        # Update activities
                        record.activity_update()
                        
                        result = {
                            'id': record.id,
                            'name': record.name,
                            'state': record.state,
                            'validation_type': validation_type,
                            'message': 'Phê duyệt thành công'
                        }

                    elif action == 'reject':
                        # Validate state - theo Odoo có thể refuse từ 'confirm', 'validate1', hoặc 'validate'
                        if record.state not in ['confirm', 'validate1', 'validate']:
                            return ResponseFormatter.error_response(
                                f'Chỉ có thể từ chối đơn ở trạng thái confirm, validate1 hoặc validate, hiện tại: {record.state}',
                                ResponseFormatter.HTTP_BAD_REQUEST,
                                http_status_code=ResponseFormatter.HTTP_OK)
                        
                        # Kiểm tra quyền từ chối
                        if not self._can_refuse_leave(record, user, user_id):
                            return ResponseFormatter.error_response(
                                'Bạn không có quyền từ chối đơn này',
                                ResponseFormatter.HTTP_FORBIDDEN,
                                http_status_code=ResponseFormatter.HTTP_OK)
                        
                        validation_type = record.holiday_status_id.leave_validation_type if record.holiday_status_id else 'no_validation'
                        
                        # Determine approver ID based on current state
                        write_vals = {'state': 'refuse'}
                        if record.state == 'validate1':
                            write_vals['first_approver_id'] = employee.id if employee else False
                        else:
                            # confirm or validate
                            if validation_type == 'both' and record.state == 'validate1':
                                write_vals['second_approver_id'] = employee.id if employee else False
                            else:
                                write_vals['first_approver_id'] = employee.id if employee else False
                        
                        record.write(write_vals)
                        
                        # Gửi thông báo với lý do
                        if note:
                            record.message_post(body=f"Lý do từ chối: {note}")
                        
                        # Delete meeting nếu có
                        if record.meeting_id:
                            record.meeting_id.write({'active': False})
                        
                        record.activity_update()
                        
                        result = {
                            'id': record.id,
                            'name': record.name,
                            'state': record.state,
                            'validation_type': validation_type,
                            'message': 'Từ chối thành công'
                        }

                    elif action == 'draft':
                        # Chỉ có thể reset từ state 'cancel' hoặc 'refuse' về 'confirm'
                        # Theo Odoo method action_reset_confirm
                        if record.state not in ['cancel', 'refuse']:
                            return ResponseFormatter.error_response(
                                f'Chỉ có thể reset từ trạng thái cancel hoặc refuse, hiện tại: {record.state}',
                                ResponseFormatter.HTTP_BAD_REQUEST,
                                http_status_code=ResponseFormatter.HTTP_OK)
                        
                        # Check permissions
                        can_reset = False
                        if user.has_group('base.group_system') or user.has_group('hr_holidays.group_hr_holidays_manager'):
                            can_reset = True
                        elif user.has_group('hr_holidays.group_hr_holidays_user'):
                            can_reset = True
                        elif employee and employee.id == record.employee_id.id:
                            can_reset = True
                        
                        if not can_reset:
                            return ResponseFormatter.error_response(
                                'Bạn không có quyền reset đơn này',
                                ResponseFormatter.HTTP_FORBIDDEN,
                                http_status_code=ResponseFormatter.HTTP_OK)
                        
                        # Reset về confirm
                        record.write({
                            'state': 'confirm',
                            'first_approver_id': False,
                            'second_approver_id': False,
                        })
                        record.activity_update()
                        
                        result = {
                            'id': record.id,
                            'name': record.name,
                            'state': record.state,
                            'message': 'Reset về confirm thành công'
                        }

                cr.commit()
                return ResponseFormatter.success_response(
                    'Thực hiện hành động thành công',
                    result,
                    ResponseFormatter.HTTP_OK
                )

            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            return ResponseFormatter.error_response(
                f'Lỗi: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR,
                http_status_code=ResponseFormatter.HTTP_OK)