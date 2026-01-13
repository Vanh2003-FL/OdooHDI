from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import pytz

EXCUSE_TYPES = [
    ('late_or_early', 'Đi muộn/về sớm'),
    ('missing_checkin_out', 'Thiếu chấm công'),
]

EXCUSE_STATES = [
    ('draft', 'Nháp'),
    ('submitted', 'Đã gửi'),
    ('approved', 'Đã phê duyệt'),
    ('rejected', 'Bị từ chối'),
]

EDITABLE_FIELDS_AFTER_SUBMIT = {
    'state', 'approver_id', 'approval_date', 
    'rejection_reason', 'corrected_checkin', 'corrected_checkout'
}

DEFAULT_WORK_SCHEDULE = {
    'start_time': 8.5,
    'end_time': 18.0,
    'late_tolerance': 0.25,
}


class AttendanceExcuse(models.Model):
    _name = 'attendance.excuse'
    _description = 'Giải trình chấm công'
    _order = 'date desc, employee_id'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    display_name = fields.Char(
        string='Tên',
        compute='_compute_display_name',
        store=True
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        compute='_compute_employee_id',
        store=True,
        readonly=False,
        ondelete='cascade',
        index=True,
        tracking=True
    )

    date = fields.Date(
        string='Ngày',
        compute='_compute_date',
        store=True,
        readonly=False,
        index=True,
        tracking=True
    )

    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Bản ghi chấm công',
        ondelete='cascade',
        index=True,
        required=True
    )

    excuse_type = fields.Selection(
        EXCUSE_TYPES,
        string="Loại giải trình",
        compute='_compute_excuse_type',
        store=True,
        tracking=True
    )

    original_checkin = fields.Datetime(
        string='Check-in gốc',
        compute='_compute_original_times',
        store=True
    )

    original_checkout = fields.Datetime(
        string='Check-out gốc',
        compute='_compute_original_times',
        store=True
    )

    requested_checkin = fields.Datetime(
        string='Check-in yêu cầu sửa'
    )

    requested_checkout = fields.Datetime(
        string='Check-out yêu cầu sửa'
    )

    corrected_checkin = fields.Datetime(
        string='Check-in đã sửa',
        tracking=True
    )

    corrected_checkout = fields.Datetime(
        string='Check-out đã sửa',
        tracking=True
    )

    late_minutes = fields.Integer(
        string='Số phút đi muộn',
        default=0,
        readonly=True
    )

    early_minutes = fields.Integer(
        string='Số phút về sớm',
        default=0,
        readonly=True
    )

    reason = fields.Text(
        string='Lý do',
        help='Lý do chi tiết cho yêu cầu giải trình',
        tracking=True
    )

    notes = fields.Text(
        string='Ghi chú'
    )

    state = fields.Selection(
        EXCUSE_STATES,
        string='Trạng thái',
        default='draft',
        tracking=True,
        index=True
    )

    approver_id = fields.Many2one(
        'res.users',
        string='Người phê duyệt',
        readonly=True,
        tracking=True
    )

    approval_date = fields.Datetime(
        string='Ngày phê duyệt',
        readonly=True
    )

    rejection_reason = fields.Text(
        string='Lý do từ chối',
        tracking=True
    )

    can_approve = fields.Boolean(
        string='Có thể phê duyệt',
        compute='_compute_can_approve',
        store=False
    )

    can_reject = fields.Boolean(
        string='Có thể từ chối',
        compute='_compute_can_reject',
        store=False
    )

    is_approver = fields.Boolean(
        string='Là người phê duyệt',
        compute='_compute_is_approver',
        store=False
    )

    @api.depends('employee_id', 'date', 'excuse_type', 'state')
    def _compute_display_name(self):
        for record in self:
            if record.employee_id and record.date and record.excuse_type:
                excuse_label = dict(record._fields['excuse_type'].selection).get(
                    record.excuse_type, record.excuse_type)
                state_label = dict(record._fields['state'].selection).get(record.state, record.state)
                record.display_name = f"{record.employee_id.name} - {record.date} - {excuse_label} ({state_label})"
            else:
                record.display_name = "Giải trình chấm công"

    @api.depends('attendance_id')
    def _compute_employee_id(self):
        for record in self:
            if record.attendance_id:
                record.employee_id = record.attendance_id.employee_id

    @api.depends('attendance_id')
    def _compute_date(self):
        for record in self:
            if record.attendance_id and record.attendance_id.check_in:
                check_in_date = fields.Datetime.context_timestamp(record, record.attendance_id.check_in).date()
                record.date = check_in_date

    @api.depends('attendance_id', 'attendance_id.check_in', 'attendance_id.check_out')
    def _compute_original_times(self):
        for record in self:
            if record.attendance_id:
                record.original_checkin = record.attendance_id.check_in
                record.original_checkout = record.attendance_id.check_out
            else:
                record.original_checkin = False
                record.original_checkout = False

    @api.depends('original_checkin', 'original_checkout', 'attendance_id', 
                 'attendance_id.attendance_status', 'attendance_id.is_invalid_record')
    def _compute_excuse_type(self):
        for record in self:
            if not record.attendance_id:
                record.excuse_type = 'late_or_early'
                continue
            
            att = record.attendance_id
            if not record.original_checkout or not att.is_invalid_record:
                record.excuse_type = 'missing_checkin_out' if att.attendance_status == 'missing_checkin_out' else 'late_or_early'
            else:
                record.excuse_type = 'late_or_early'

    @api.depends('approver_id')
    def _compute_is_approver(self):
        for record in self:
            record.is_approver = record.approver_id and record.approver_id.id == self.env.user.id

    @api.depends('approver_id', 'state')
    def _compute_can_approve(self):
        for record in self:
            if record.state != 'submitted':
                record.can_approve = False
                continue

            if not record.approver_id:
                record.can_approve = self.env.user.has_group('hr.group_hr_manager')
            elif record.approver_id.id == self.env.user.id:
                record.can_approve = True
            else:
                record.can_approve = self.env.user.has_group('hr.group_hr_manager')

    @api.depends('approver_id', 'state')
    def _compute_can_reject(self):
        for record in self:
            if record.state != 'submitted':
                record.can_reject = False
                continue

            if not record.approver_id:
                record.can_reject = self.env.user.has_group('hr.group_hr_manager')
            elif record.approver_id.id == self.env.user.id:
                record.can_reject = True
            else:
                record.can_reject = self.env.user.has_group('hr.group_hr_manager')

    @api.onchange('excuse_type')
    def _onchange_excuse_type(self):
        if not self.attendance_id:
            return

        self.requested_checkin = False
        self.requested_checkout = False

        if self.excuse_type in ['late_or_early', 'missing_checkin_out']:
            self.requested_checkin = self.original_checkin
            self.requested_checkout = self.original_checkout

    def _build_excuse_response(self):
        return {
            'id': self.id,
            'attendance_id': self.attendance_id.id,
            'employee_id': self.employee_id.id,
            'employee_name': self.employee_id.name,
            'date': self.date.isoformat() if self.date else None,
            'excuse_type': self.excuse_type,
            'state': self.state,
            'reason': self.reason,
            'original_checkin': self.original_checkin.isoformat() if self.original_checkin else None,
            'original_checkout': self.original_checkout.isoformat() if self.original_checkout else None,
            'requested_checkin': self.requested_checkin.isoformat() if self.requested_checkin else None,
            'requested_checkout': self.requested_checkout.isoformat() if self.requested_checkout else None,
        }

    def _get_current_user_employee(self, user_id):
        current_user = self.env['res.users'].browse(user_id)
        if not current_user.exists():
            raise UserError('User không tồn tại')
        
        current_employee = current_user.employee_id
        if not current_employee:
            raise UserError('User không phải là nhân viên')
        
        return current_user, current_employee

    def _check_permission(self, user, employee_id, allow_admin=True, allow_manager=True, allow_owner=True):
        if allow_admin and user.has_group('base.group_system'):
            return True
        if allow_manager and user.has_group('hr.group_hr_manager'):
            return True
        if allow_owner and employee_id == self.employee_id.id:
            return True
        return False

    def _parse_datetime(self, dt_str):
        if not dt_str:
            return None
        if isinstance(dt_str, str):
            dt_str = dt_str.replace('T', ' ')
            try:
                return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    return datetime.strptime(dt_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    raise UserError(f'Định dạng datetime không hợp lệ: {dt_str}')
        return dt_str

    def _get_company_timezone(self):
        return pytz.timezone(self.env.user.tz or 'Asia/Ho_Chi_Minh')

    def _convert_to_local_time(self, dt):
        if not dt:
            return None
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        tz = self._get_company_timezone()
        return dt.astimezone(tz)

    def _get_work_schedule(self, employee):
        if not employee:
            return DEFAULT_WORK_SCHEDULE

        calendar = employee.resource_calendar_id or employee.company_id.resource_calendar_id
        if not calendar:
            return DEFAULT_WORK_SCHEDULE

        attendances = calendar.attendance_ids.filtered(lambda a: a.dayofweek == '0')
        if not attendances:
            attendances = calendar.attendance_ids
        
        if attendances:
            attendances = attendances.sorted(key=lambda a: a.hour_from)
            first, last = attendances[0], attendances[-1]
            return {
                'start_time': first.hour_from,
                'end_time': last.hour_to,
                'late_tolerance': 0.25,
            }
        
        return DEFAULT_WORK_SCHEDULE

    def _check_monthly_limit(self, employee, excuse_type, date):
        limit_config = self.env['attendance.excuse.limit'].search([
            ('excuse_type', '=', excuse_type),
            ('active', '=', True)
        ], limit=1)

        if not limit_config:
            return

        month_start = date.replace(day=1)
        if date.month == 12:
            month_end = month_start.replace(year=date.year + 1, month=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=date.month + 1) - timedelta(days=1)

        approved_count = self.search_count([
            ('employee_id', '=', employee.id),
            ('excuse_type', '=', excuse_type),
            ('state', '=', 'approved'),
            ('date', '>=', month_start),
            ('date', '<=', month_end)
        ])

        submitted_count = self.search_count([
            ('employee_id', '=', employee.id),
            ('excuse_type', '=', excuse_type),
            ('state', '=', 'submitted'),
            ('date', '>=', month_start),
            ('date', '<=', month_end)
        ])

        total_count = approved_count + submitted_count

        if total_count >= limit_config.monthly_limit:
            excuse_label = dict(self._fields['excuse_type'].selection).get(excuse_type, excuse_type)
            raise ValidationError(
                f"Nhân viên {employee.name} đã vượt quá giới hạn giải trình \"{excuse_label}\" "
                f"({limit_config.monthly_limit} lần/tháng) trong tháng {date.month}/{date.year}. "
                f"Hiện tại: {total_count}/{limit_config.monthly_limit}"
            )

    @api.model
    def detect_and_create_excuses(self, target_date=None):
        if target_date is None:
            target_date = fields.Date.context_today(self)

        self._detect_late_arrival(target_date)
        self._detect_missing_checkout(target_date)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': f'Đã phát hiện và tạo giải trình chấm công cho ngày {target_date}',
                'type': 'success',
                'sticky': False,
            }
        }

    def _detect_late_arrival(self, target_date):
        attendances = self.env['hr.attendance'].search([
            ('check_in', '>=', datetime.combine(target_date, datetime.min.time())),
            ('check_in', '<=', datetime.combine(target_date, datetime.max.time())),
            ('attendance_status', '=', 'late_or_early'),
            ('is_invalid_record', '=', False),
        ])

        for att in attendances:
            if not att.check_in or not att.check_out:
                continue

            if self.search_count([('attendance_id', '=', att.id), ('excuse_type', '=', 'late_or_early')]):
                continue

            local_checkin = self._convert_to_local_time(att.check_in)
            check_in_hour = local_checkin.hour + local_checkin.minute / 60.0
            schedule = self._get_work_schedule(att.employee_id)
            late_threshold = schedule['start_time'] + schedule['late_tolerance']

            if check_in_hour > late_threshold:
                late_minutes = int((check_in_hour - schedule['start_time']) * 60)
                self.create({
                    'attendance_id': att.id,
                    'late_minutes': late_minutes,
                    'state': 'draft',
                    'notes': f'Tự động phát hiện: Đi muộn {late_minutes} phút',
                })
            else:
                local_checkout = self._convert_to_local_time(att.check_out)
                check_out_hour = local_checkout.hour + local_checkout.minute / 60.0
                early_threshold = schedule['end_time']
                
                if check_out_hour < early_threshold:
                    early_minutes = int((early_threshold - check_out_hour) * 60)
                    self.create({
                        'attendance_id': att.id,
                        'early_minutes': early_minutes,
                        'state': 'draft',
                        'notes': f'Tự động phát hiện: Về sớm {early_minutes} phút',
                    })

    def _detect_missing_checkout(self, target_date):
        previous_date = target_date - timedelta(days=1)

        attendances = self.env['hr.attendance'].search([
            ('check_in', '>=', datetime.combine(previous_date, datetime.min.time())),
            ('check_in', '<=', datetime.combine(previous_date, datetime.max.time())),
            ('check_out', '=', False),
            ('is_invalid_record', '=', False),
        ])

        for att in attendances:
            if not self.search_count([('attendance_id', '=', att.id), ('excuse_type', '=', 'missing_checkin_out')]):
                self.create({
                    'attendance_id': att.id,
                    'state': 'draft',
                    'notes': 'Tự động phát hiện: Thiếu chấm công',
                })

    def _do_submit(self, user_id=None):
        if self.state != 'draft':
            raise UserError(f'Chỉ có thể gửi ở trạng thái draft, hiện tại là {self.state}')

        if self.employee_id and self.date and self.excuse_type:
            self._check_monthly_limit(self.employee_id, self.excuse_type, self.date)

        if not self.approver_id and self.employee_id:
            if self.employee_id.attendance_manager_id:
                self.approver_id = self.employee_id.attendance_manager_id.user_id.id
            elif self.employee_id.parent_id and self.employee_id.parent_id.user_id:
                self.approver_id = self.employee_id.parent_id.user_id.id

        self.state = 'submitted'
        self.message_post(body="Yêu cầu giải trình đã được gửi")

    def action_submit(self):
        for record in self:
            record._do_submit()

    def _do_approve(self, approver_id, corrected_checkin=None, corrected_checkout=None):
        approver = self.env['res.users'].browse(approver_id)
        if not approver.exists():
            raise UserError('User không tồn tại')

        if self.state != 'submitted':
            raise UserError(f'Chỉ có thể phê duyệt giải trình ở trạng thái submitted, hiện tại là {self.state}')

        can_approve = (approver.has_group('base.group_system') or
                      approver.has_group('hr.group_hr_manager') or
                      (self.approver_id and self.approver_id.id == approver_id))

        if not can_approve:
            raise UserError('Không có quyền phê duyệt giải trình này')

        update_values = {
            'state': 'approved',
            'approver_id': approver_id,
            'approval_date': fields.Datetime.now(),
        }

        if corrected_checkin:
            update_values['corrected_checkin'] = corrected_checkin
        
        if corrected_checkout:
            update_values['corrected_checkout'] = corrected_checkout

        self.write(update_values)

        if self.attendance_id:
            att_update = {}
            if self.corrected_checkin:
                att_update['check_in'] = self.corrected_checkin
            elif self.requested_checkin:
                att_update['check_in'] = self.requested_checkin
            
            if self.corrected_checkout:
                att_update['check_out'] = self.corrected_checkout
            elif self.requested_checkout:
                att_update['check_out'] = self.requested_checkout
            
            if att_update:
                self.attendance_id.write(att_update)
                if not self.corrected_checkin and self.requested_checkin:
                    self.corrected_checkin = self.requested_checkin
                if not self.corrected_checkout and self.requested_checkout:
                    self.corrected_checkout = self.requested_checkout

        self.message_post(body=f"Yêu cầu giải trình đã được phê duyệt bởi {approver.name}")

        return {
            'id': self.id,
            'state': self.state,
            'approver_id': self.approver_id.id,
            'approver_name': self.approver_id.name,
            'approval_date': self.approval_date.isoformat() if self.approval_date else None,
        }

    def action_approve(self):
        for record in self:
            record._do_approve(self.env.user.id)

    def _do_reject(self, rejector_id, rejection_reason=''):
        rejector = self.env['res.users'].browse(rejector_id)
        if not rejector.exists():
            raise UserError('User không tồn tại')

        if self.state != 'submitted':
            raise UserError(f'Chỉ có thể từ chối giải trình ở trạng thái submitted, hiện tại là {self.state}')

        can_reject = (rejector.has_group('base.group_system') or
                     rejector.has_group('hr.group_hr_manager') or
                     (self.approver_id and self.approver_id.id == rejector_id))

        if not can_reject:
            raise UserError('Không có quyền từ chối giải trình này')

        update_values = {
            'state': 'rejected',
            'approver_id': rejector_id,
            'approval_date': fields.Datetime.now(),
        }

        if rejection_reason:
            update_values['rejection_reason'] = rejection_reason

        self.write(update_values)
        self.message_post(body=f"Yêu cầu giải trình đã bị từ chối bởi {rejector.name}. Lý do: {rejection_reason if rejection_reason else 'Không cung cấp'}")

        return {
            'id': self.id,
            'state': self.state,
            'approver_id': self.approver_id.id,
            'approver_name': self.approver_id.name,
            'approval_date': self.approval_date.isoformat() if self.approval_date else None,
            'rejection_reason': self.rejection_reason,
        }

    def action_reject(self):
        for record in self:
            if record.state != 'submitted':
                continue
            record._do_reject(self.env.user.id)

    def _do_draft(self, user_id):
        current_user = self.env['res.users'].browse(user_id)
        if not current_user.exists():
            raise UserError('User không tồn tại')

        current_employee = current_user.employee_id

        if self.state != 'submitted':
            raise UserError(f'Chỉ có thể quay về nháp từ trạng thái submitted, hiện tại là {self.state}')

        can_reset = (current_user.has_group('base.group_system') or
                    current_user.has_group('hr.group_hr_manager') or
                    (current_employee and current_employee.id == self.employee_id.id) or
                    (self.employee_id.parent_id and self.employee_id.parent_id.user_id.id == current_user.id))

        if not can_reset:
            raise UserError('Không có quyền quay về nháp giải trình này')

        self.write({
            'state': 'draft',
            'approver_id': False,
            'approval_date': False,
        })
        
        self.message_post(body=f"Yêu cầu giải trình đã quay về trạng thái nháp bởi {current_user.name}")

        return {
            'id': self.id,
            'state': self.state,
            'approver_id': self.approver_id.id if self.approver_id else False,
            'approver_name': self.approver_id.name if self.approver_id else '',
        }

    def get_my_requests(self):
        return self.search([('employee_id.user_id', '=', self.env.user.id)], order='date desc')

    def get_pending_approvals(self):
        return self.search([('state', '=', 'submitted')], order='date desc')

    def write(self, values):
        for record in self:
            if record.state != 'draft':
                update_fields = set(values.keys())
                if not update_fields.issubset(EDITABLE_FIELDS_AFTER_SUBMIT):
                    raise UserError(f'Chỉ có thể sửa ở trạng thái draft, hiện tại là {record.state}')
        
        return super().write(values)

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(f'Chỉ có thể xóa ở trạng thái draft, hiện tại là {record.state}')
        
        return super().unlink()

    @api.model
    def api_create_excuse(self, data, user_id):
        for field in ['attendance_id', 'excuse_type']:
            if not data.get(field):
                raise UserError(f'{field} là bắt buộc')

        current_user, current_employee = self._get_current_user_employee(user_id)

        attendance = self.env['hr.attendance'].browse(data['attendance_id'])
        if not attendance.exists():
            raise UserError('Không tìm thấy bản ghi chấm công')

        if attendance.attendance_status == 'valid':
            raise UserError('Không thể tạo giải trình cho bản ghi chấm công hợp lệ')

        if not (current_user.has_group('base.group_system') or
                current_user.has_group('hr.group_hr_manager') or
                current_employee.id == attendance.employee_id.id):
            raise UserError('Không có quyền tạo giải trình cho nhân viên khác')

        if data['excuse_type'] not in dict(EXCUSE_TYPES):
            raise UserError('excuse_type không hợp lệ')

        excuse = self.create({
            'attendance_id': data['attendance_id'],
            'excuse_type': data['excuse_type'],
            'reason': data.get('reason', ''),
            'requested_checkin': self._parse_datetime(data.get('requested_checkin')),
            'requested_checkout': self._parse_datetime(data.get('requested_checkout')),
        })

        return {
            'id': excuse.id,
            'attendance_id': excuse.attendance_id.id,
            'employee_id': excuse.employee_id.id,
            'employee_name': excuse.employee_id.name,
            'excuse_type': excuse.excuse_type,
            'state': excuse.state,
            'reason': excuse.reason,
            'requested_checkin': excuse.requested_checkin.isoformat() if excuse.requested_checkin else None,
            'requested_checkout': excuse.requested_checkout.isoformat() if excuse.requested_checkout else None,
        }

    @api.model
    def api_get_my_excuse_list(self, user_id, limit=10, offset=0, state=None):
        current_user = self.env['res.users'].browse(user_id)
        if not current_user.exists():
            raise UserError('User không tồn tại')

        current_employee = current_user.employee_id
        if not current_employee:
            raise UserError('User không phải là nhân viên')

        domain = [('employee_id', '=', current_employee.id)]
        if state:
            domain.append(('state', '=', state))

        excuses = self.search(domain, limit=limit, offset=offset, order='date desc')
        total_count = self.search_count(domain)

        excuse_data = []
        for excuse in excuses:
            excuse_data.append({
                'id': excuse.id,
                'attendance_id': excuse.attendance_id.id,
                'employee_id': excuse.employee_id.id,
                'employee_name': excuse.employee_id.name,
                'date': excuse.date.isoformat() if excuse.date else None,
                'excuse_type': excuse.excuse_type,
                'state': excuse.state,
                'reason': excuse.reason,
                'original_checkin': excuse.original_checkin.isoformat() if excuse.original_checkin else None,
                'original_checkout': excuse.original_checkout.isoformat() if excuse.original_checkout else None,
                'requested_checkin': excuse.requested_checkin.isoformat() if excuse.requested_checkin else None,
                'requested_checkout': excuse.requested_checkout.isoformat() if excuse.requested_checkout else None,
            })

        return {
            'excuses': excuse_data,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
        }

    def api_get_excuse_detail(self, user_id):
        current_user, current_employee = self._get_current_user_employee(user_id)

        if not self._check_permission(current_user, current_employee.id):
            raise UserError('Không có quyền xem thông tin này')

        return self._build_excuse_response()

    def api_submit_excuse(self, user_id):
        current_user, current_employee = self._get_current_user_employee(user_id)

        if not self._check_permission(current_user, current_employee.id):
            raise UserError('Không có quyền submit giải trình này')

        self._do_submit(user_id)
        return {'id': self.id, 'state': self.state}

    def api_approve_excuse(self, user_id, corrected_checkin=None, corrected_checkout=None):
        return self._do_approve(user_id, corrected_checkin, corrected_checkout)

    def api_reject_excuse(self, user_id, rejection_reason=''):
        return self._do_reject(user_id, rejection_reason)

    def api_draft_excuse(self, user_id):
        return self._do_draft(user_id)

    @api.model
    def api_update_excuse(self, data, user_id):
        excuse_id = data.get('excuse_id')
        if not excuse_id:
            raise UserError('excuse_id là bắt buộc')

        current_user, current_employee = self._get_current_user_employee(user_id)

        excuse = self.browse(excuse_id)
        if not excuse.exists():
            raise UserError('Không tìm thấy giải trình')

        if not self._check_permission(current_user, current_employee.id):
            raise UserError('Không có quyền cập nhật giải trình này')

        update_data = {}
        if 'reason' in data:
            update_data['reason'] = data['reason']
        if 'requested_checkin' in data:
            update_data['requested_checkin'] = data['requested_checkin']
        if 'requested_checkout' in data:
            update_data['requested_checkout'] = data['requested_checkout']

        if update_data:
            excuse.write(update_data)

        return excuse._build_excuse_response()
