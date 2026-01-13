from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    @api.model
    def api_get_leave_types(self):
        """API method để lấy danh sách loại nghỉ"""
        leave_types = self.env['hr.leave.type'].search([
            ('active', '=', True)
        ], order='name')

        types_data = []
        for leave_type in leave_types:
            types_data.append({
                'id': leave_type.id,
                'name': leave_type.name,
            })
        
        return types_data

    @api.model
    def api_get_remaining_days(self, user_id):
        """API method để lấy số ngày phép còn lại của user"""
        current_user = self.env['res.users'].browse(user_id)
        if not current_user.exists():
            raise UserError('User không tồn tại')

        employee = current_user.employee_id
        if not employee:
            raise UserError('User không phải là nhân viên')

        leave_types = self.env['hr.leave.type'].search([('active', '=', True)])
        remaining_days = []

        for leave_type in leave_types:
            # Sử dụng allocation data như Odoo base
            try:
                allocation_data = leave_type.get_allocation_data([employee], fields.Date.today())
                if employee in allocation_data and allocation_data[employee]:
                    remaining = allocation_data[employee][0][1].get('virtual_remaining_leaves', 0)
                else:
                    remaining = 0
            except:
                # Fallback nếu method không tồn tại
                allocation = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', employee.id),
                    ('holiday_status_id', '=', leave_type.id),
                    ('state', '=', 'validate'),
                    '|',
                    ('date_to', '=', False),
                    ('date_to', '>=', fields.Date.today()),
                ], order='date_from desc', limit=1)

                if allocation:
                    used_leaves = self.search_count([
                        ('employee_id', '=', employee.id),
                        ('holiday_status_id', '=', leave_type.id),
                        ('state', '=', 'validate'),
                        ('date_from', '>=', allocation.date_from),
                    ])
                    remaining = max(0, allocation.number_of_days - used_leaves)
                else:
                    remaining = 0

            remaining_days.append({
                'leave_type_id': leave_type.id,
                'leave_type_name': leave_type.name,
                'remaining_days': remaining,
                'allocation_type': leave_type.requires_allocation,
            })

        return {
            'employee_id': employee.id,
            'employee_name': employee.name,
            'remaining_days': remaining_days
        }

    @api.model
    def api_get_leave_list(self, user_id, limit=10, offset=0, state=None):
        """API method để lấy danh sách đơn xin nghỉ"""
        current_user = self.env['res.users'].browse(user_id)
        if not current_user.exists():
            raise UserError('User không tồn tại')

        current_employee = current_user.employee_id

        # Build domain
        domain = []

        # Permission check theo Odoo business rules
        is_hr_user = current_user.has_group('hr_holidays.group_hr_holidays_user')
        is_hr_manager = current_user.has_group('hr_holidays.group_hr_holidays_manager')
        is_system = current_user.has_group('base.group_system')

        if not (is_system or is_hr_manager or is_hr_user):
            # Regular employee - chỉ xem được của mình
            if current_employee:
                domain.append(('employee_id', '=', current_employee.id))
            else:
                raise UserError('User không phải là nhân viên')
        elif is_hr_user and not (is_hr_manager or is_system):
            # HR User có thể xem leaves của team/department mình manage
            if current_employee:
                managed_employees = self.env['hr.employee'].search([
                    '|',
                    ('leave_manager_id', '=', current_user.id),
                    ('parent_id.user_id', '=', current_user.id)
                ])
                if managed_employees:
                    domain.append(('employee_id', 'in', [current_employee.id] + managed_employees.ids))
                else:
                    domain.append(('employee_id', '=', current_employee.id))
        # HR Manager và System có thể xem tất cả

        if state:
            domain.append(('state', '=', state))

        # Lấy danh sách leave
        leaves = self.search(domain, limit=limit, offset=offset, order='date_from desc')
        total_count = self.search_count(domain)

        leaves_data = []
        for leave in leaves:
            leaves_data.append({
                'id': leave.id,
                'employee_id': leave.employee_id.id,
                'employee_name': leave.employee_id.name,
                'leave_type': leave.holiday_status_id.name,
                'date_from': leave.date_from.isoformat() if leave.date_from else None,
                'date_to': leave.date_to.isoformat() if leave.date_to else None,
                'number_of_days': leave.number_of_days,
                'state': leave.state,
            })

        return {
            'leaves': leaves_data,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
        }

    @api.model
    def api_get_leave_detail(self, leave_id, user_id):
        """API method để lấy chi tiết đơn xin nghỉ"""
        current_user = self.env['res.users'].browse(user_id)
        if not current_user.exists():
            raise UserError('User không tồn tại')

        # Lấy leave
        leave = self.browse(leave_id)
        if not leave.exists():
            raise UserError('Không tìm thấy đơn xin nghỉ')

        # Kiểm tra quyền - chỉ xem được của chính mình hoặc nếu là HR/Admin
        current_employee = current_user.employee_id
        can_view = (current_user.has_group('base.group_system') or
                   current_user.has_group('hr.group_hr_manager') or
                   (current_employee and current_employee.id == leave.employee_id.id))

        if not can_view:
            raise UserError('Không có quyền xem thông tin này')

        # Format dữ liệu
        return {
            'id': leave.id,
            'employee_id': leave.employee_id.id,
            'employee_name': leave.employee_id.name,
            'leave_type': leave.holiday_status_id.name,
            'date_from': leave.date_from.isoformat() if leave.date_from else None,
            'date_to': leave.date_to.isoformat() if leave.date_to else None,
            'number_of_days': leave.number_of_days,
            'state': leave.state,
            'name': leave.name or '',
        }

    @api.model
    def api_create_leave(self, data, user_id):
        """API method để tạo đơn xin nghỉ"""
        # Kiểm tra dữ liệu bắt buộc
        required_fields = ['holiday_status_id', 'date_from', 'date_to']
        for field in required_fields:
            if field not in data or not data[field]:
                raise UserError(f'{field} là bắt buộc')

        current_user = self.env['res.users'].browse(user_id)
        if not current_user.exists():
            raise UserError('User không tồn tại')

        current_employee = current_user.employee_id
        if not current_employee:
            raise UserError('User không phải là nhân viên')

        # Kiểm tra employee_id - cho phép tạo cho chính mình hoặc nếu là HR/Admin
        employee_id = data.get('employee_id', current_employee.id)
        if employee_id != current_employee.id:
            if not (current_user.has_group('base.group_system') or current_user.has_group('hr.group_hr_manager')):
                raise UserError('Không có quyền tạo đơn cho nhân viên khác')

        # Validate employee
        employee = self.env['hr.employee'].browse(employee_id)
        if not employee.exists():
            raise UserError('Không tìm thấy nhân viên')

        # Validate leave type
        leave_type = self.env['hr.leave.type'].browse(data['holiday_status_id'])
        if not leave_type.exists():
            raise UserError('Không tìm thấy loại nghỉ')

        # Validate date format và parse datetime
        try:
            if isinstance(data['date_from'], str):
                date_from = datetime.fromisoformat(data['date_from'].replace('Z', '+00:00'))
            else:
                date_from = data['date_from']
                
            if isinstance(data['date_to'], str):
                date_to = datetime.fromisoformat(data['date_to'].replace('Z', '+00:00'))
            else:
                date_to = data['date_to']
        except (ValueError, TypeError):
            raise UserError('Định dạng ngày giờ không hợp lệ')

        # Kiểm tra date_from <= date_to
        if date_from >= date_to:
            raise UserError('Ngày bắt đầu phải trước ngày kết thúc')

        # Tạo leave với context để trigger validation
        leave = self.with_context(leave_api_create=True).create({
            'employee_id': employee_id,
            'holiday_status_id': data['holiday_status_id'],
            'request_date_from': date_from.date() if hasattr(date_from, 'date') else date_from,
            'request_date_to': date_to.date() if hasattr(date_to, 'date') else date_to,
            'name': data.get('name', ''),
        })

        return {
            'id': leave.id,
            'employee_id': leave.employee_id.id,
            'leave_type': leave.holiday_status_id.name,
            'date_from': leave.date_from.isoformat() if leave.date_from else None,
            'date_to': leave.date_to.isoformat() if leave.date_to else None,
            'state': leave.state,
        }

    def api_update_leave(self, data, user_id):
        """API method để cập nhật đơn xin nghỉ"""
        current_user = self.env['res.users'].browse(user_id)
        if not current_user.exists():
            raise UserError('User không tồn tại')

        current_employee = current_user.employee_id

        # Kiểm tra quyền - chỉ sửa được của chính mình hoặc nếu là HR/Admin
        can_edit = (current_user.has_group('base.group_system') or
                   current_user.has_group('hr.group_hr_manager') or
                   (current_employee and current_employee.id == self.employee_id.id))

        if not can_edit:
            raise UserError('Không có quyền sửa đơn này')

        # Chỉ cho sửa khi trạng thái là draft
        if self.state != 'draft':
            raise UserError('Chỉ có thể sửa đơn ở trạng thái nháp')

        # Chuẩn bị dữ liệu update
        update_data = {}
        if 'date_from' in data:
            update_data['date_from'] = data['date_from']
        if 'date_to' in data:
            update_data['date_to'] = data['date_to']
        if 'holiday_status_id' in data:
            update_data['holiday_status_id'] = data['holiday_status_id']
        if 'name' in data:
            update_data['name'] = data['name']

        if not update_data:
            raise UserError('Không có dữ liệu để sửa')

        # Cập nhật leave
        self.write(update_data)

        return {
            'id': self.id,
            'employee_id': self.employee_id.id,
            'leave_type': self.holiday_status_id.name,
            'date_from': self.date_from.isoformat() if self.date_from else None,
            'date_to': self.date_to.isoformat() if self.date_to else None,
            'state': self.state,
        }

    def write(self, values):
        """Override write để implement business validation như Odoo base"""
        # Nếu là API call, skip một số validation
        if not self.env.context.get('leave_api_create'):
            # Implement validation tương tự Odoo base
            is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user') or self.env.is_superuser()
            
            # Check nếu không phải HR Officer và đang sửa field quan trọng
            if not is_officer and values.keys() - {'name', 'private_name'}:
                for record in self:
                    # Không cho sửa leave đã bắt đầu
                    if (record.date_from and record.date_from.date() < fields.Date.today() and 
                        record.employee_id.leave_manager_id != self.env.user and 
                        record.state not in ('confirm', 'draft')):
                        raise UserError('Bạn phải có quyền manager để sửa/validate đơn nghỉ đã bắt đầu')
                    
                    # Không cho sửa leave đã cancel
                    if record.state == 'cancel':
                        raise UserError('Chỉ có manager mới có thể sửa đơn nghỉ đã hủy')
            
            # Validate state changes
            if values.get('state'):
                for record in self:
                    try:
                        record._check_approval_update(values['state'])
                    except AttributeError:
                        # Nếu method không tồn tại, implement logic cơ bản
                        if not (self.env.user.has_group('hr_holidays.group_hr_holidays_user') or 
                                self.env.user.has_group('hr_holidays.group_hr_holidays_manager')):
                            if record.employee_id.user_id != self.env.user:
                                raise UserError('Không có quyền thay đổi trạng thái đơn này')
        
        return super().write(values)