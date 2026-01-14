import json
from datetime import datetime
from odoo import http
from odoo.http import request

from ..decorators.auth import verify_token
from ..utils.request_helper import get_json_data
from ..utils.response_formatter import ResponseFormatter
from ..utils.env_helper import get_env


class ApprovalController(http.Controller):

    @http.route('/api/v1/approval/get_approved', type='http', auth='none', methods=['POST'], csrf=False)
    @verify_token
    def get_approved(self):
        try:
            data = get_json_data()
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                from_date = data.get('from_date', '')
                to_date = data.get('to_date', '')
                approval_type = data.get('type', 'all')

                if approval_type not in ['leave', 'Timesheet', 'all']:
                    return ResponseFormatter.error_response(
                        'type phải là: leave, Timesheet hoặc all',
                        ResponseFormatter.HTTP_BAD_REQUEST,
                        http_status_code=ResponseFormatter.HTTP_OK)

                approved_list = []

                if approval_type in ['leave', 'all']:
                    leaves = env['hr.leave'].sudo().api_get_approved_leaves(user_id, from_date, to_date)
                    approved_list.extend(leaves)

                if approval_type in ['Timesheet', 'all']:
                    excuses = env['attendance.excuse'].sudo().api_get_approved_excuses(user_id, from_date, to_date)
                    approved_list.extend(excuses)

                approved_list.sort(key=lambda x: x.get('create_date') or '', reverse=True)

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
    @verify_token
    def get_approvals_single(self):
        try:
            data = get_json_data()
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                from_date = data.get('from_date', '')
                to_date = data.get('to_date', '')
                approval_type = data.get('type', 'all')

                if approval_type not in ['leave', 'Timesheet', 'all']:
                    return ResponseFormatter.error_response(
                        'type phải là: leave, Timesheet hoặc all',
                        ResponseFormatter.HTTP_BAD_REQUEST,
                        http_status_code=ResponseFormatter.HTTP_OK)

                approvals_list = []

                if approval_type in ['leave', 'all']:
                    leaves = env['hr.leave'].sudo().api_get_pending_leaves(user_id, from_date, to_date)
                    approvals_list.extend(leaves)

                # Fetch Pending Timesheet (Attendance Excuse)
                if approval_type in ['Timesheet', 'all']:
                    excuses = env['attendance.excuse'].sudo().api_get_pending_excuses(user_id, from_date, to_date)
                    approvals_list.extend(excuses)

                # Sort by creation date descending
                approvals_list.sort(key=lambda x: x.get('create_date') or '', reverse=True)

                user = env['res.users'].browse(user_id)
                is_admin = user.has_group('base.group_system')

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
    @verify_token
    def action_approval(self):
        try:
            data = get_json_data()
            user_id = request.jwt_payload.get('user_id')
            env, cr = get_env()

            try:
                model_name = data.get('model')
                record_id = data.get('id')
                action = data.get('action')
                note = data.get('note', '')

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

                if model_name not in ['attendance.excuse', 'hr.leave']:
                    return ResponseFormatter.error_response(
                        'model phải là: attendance.excuse hoặc hr.leave',
                        ResponseFormatter.HTTP_BAD_REQUEST,
                        http_status_code=ResponseFormatter.HTTP_OK)

                if action not in ['accept', 'reject', 'draft']:
                    return ResponseFormatter.error_response(
                        'action phải là: accept, reject hoặc draft',
                        ResponseFormatter.HTTP_BAD_REQUEST,
                        http_status_code=ResponseFormatter.HTTP_OK)

                if action == 'reject' and not note:
                    return ResponseFormatter.error_response(
                        'note là bắt buộc cho hành động reject',
                        ResponseFormatter.HTTP_BAD_REQUEST,
                        http_status_code=ResponseFormatter.HTTP_OK)

                result = {}

                if model_name == 'attendance.excuse':
                    if action == 'accept':
                        result = env['attendance.excuse'].browse(record_id).api_approve_excuse(user_id, data.get('corrected_checkin'), data.get('corrected_checkout'))

                    elif action == 'reject':
                        result = env['attendance.excuse'].browse(record_id).api_reject_excuse(user_id, note)

                    elif action == 'draft':
                        result = env['attendance.excuse'].browse(record_id).api_draft_excuse(user_id)

                elif model_name == 'hr.leave':
                    if action == 'accept':
                        result = env['hr.leave'].sudo().api_approve_leave(user_id, record_id)

                    elif action == 'reject':
                        result = env['hr.leave'].sudo().api_refuse_leave(user_id, record_id, note)

                    elif action == 'draft':
                        result = env['hr.leave'].sudo().api_reset_leave(user_id, record_id)

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


