# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # ==================== THÔNG TIN THUẾ ====================
    tax_id = fields.Char('Mã số thuế', tracking=True)
    tax_registration_date = fields.Date('Ngày đăng ký thuế')
    
    # Người phụ thuộc
    dependent_ids = fields.One2many('hr.employee.dependent', 'employee_id', string='Người phụ thuộc')
    dependent_count = fields.Integer('Số người phụ thuộc', compute='_compute_dependent_count', store=True)
    
    # Giảm trừ thuế (theo quy định VN 2024)
    personal_deduction = fields.Monetary(
        'Giảm trừ bản thân',
        default=11000000,
        help='Giảm trừ gia cảnh cho bản thân (11tr/tháng theo 2024)'
    )
    dependent_deduction = fields.Monetary(
        'Giảm trừ mỗi người PT',
        default=4400000,
        help='Giảm trừ cho mỗi người phụ thuộc (4.4tr/tháng)'
    )
    total_deduction = fields.Monetary('Tổng giảm trừ', compute='_compute_total_deduction', store=True)
    
    # ==================== THÔNG TIN BẢO HIỂM ====================
    social_insurance_number = fields.Char('Số sổ BHXH', tracking=True)
    social_insurance_date = fields.Date('Ngày cấp sổ BHXH')
    health_insurance_number = fields.Char('Số thẻ BHYT')
    
    # ==================== KHOẢN VAY/TẠM ỨNG ====================
    loan_ids = fields.One2many('hr.loan', 'employee_id', string='Khoản vay/Tạm ứng')
    active_loan_count = fields.Integer('Số khoản vay đang trả', compute='_compute_loan_count')
    total_loan_balance = fields.Monetary('Tổng nợ còn lại', compute='_compute_loan_balance')
    
    # ==================== KHEN THƯỞNG/KỶ LUẬT ====================
    discipline_ids = fields.One2many('hr.discipline', 'employee_id', string='Kỷ luật')
    reward_ids = fields.One2many('hr.reward', 'employee_id', string='Khen thưởng')
    
    # ==================== PAYSLIP ====================
    payslip_ids = fields.One2many('hr.payslip', 'employee_id', string='Phiếu lương')
    payslip_count = fields.Integer('Số phiếu lương', compute='_compute_payslip_count')

    @api.depends('dependent_ids', 'dependent_ids.is_active')
    def _compute_dependent_count(self):
        for employee in self:
            employee.dependent_count = len(employee.dependent_ids.filtered('is_active'))

    @api.depends('personal_deduction', 'dependent_count', 'dependent_deduction')
    def _compute_total_deduction(self):
        for employee in self:
            employee.total_deduction = employee.personal_deduction + (employee.dependent_count * employee.dependent_deduction)

    def _compute_loan_count(self):
        for employee in self:
            employee.active_loan_count = len(employee.loan_ids.filtered(lambda l: l.state == 'approved' and l.balance > 0))

    def _compute_loan_balance(self):
        for employee in self:
            employee.total_loan_balance = sum(employee.loan_ids.filtered(lambda l: l.state == 'approved').mapped('balance'))

    def _compute_payslip_count(self):
        for employee in self:
            employee.payslip_count = len(employee.payslip_ids)

    def action_view_payslips(self):
        self.ensure_one()
        return {
            'name': _('Phiếu lương'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_create_payslip(self):
        """Tạo phiếu lương mới nhanh từ nhân viên"""
        self.ensure_one()
        
        # Tìm hợp đồng đang chạy
        contract = self.env['hr.contract'].search([
            ('employee_id', '=', self.id),
            ('state', '=', 'open')
        ], limit=1)
        
        if not contract:
            raise UserError(_('Nhân viên %s chưa có hợp đồng đang chạy. Vui lòng tạo hợp đồng trước.') % self.name)
        
        # Lấy tháng hiện tại
        import datetime
        today = fields.Date.today()
        date_from = today.replace(day=1)
        # Ngày cuối tháng
        if today.month == 12:
            date_to = today.replace(day=31)
        else:
            date_to = (today.replace(month=today.month + 1, day=1) - datetime.timedelta(days=1))
        
        # Tạo phiếu lương
        payslip = self.env['hr.payslip'].create({
            'employee_id': self.id,
            'contract_id': contract.id,
            'struct_id': contract.struct_id.id,
            'date_from': date_from,
            'date_to': date_to,
            'name': _('Lương tháng %s/%s - %s') % (today.month, today.year, self.name),
        })
        
        # Tính lương luôn
        payslip.compute_sheet()
        
        # Mở form phiếu lương vừa tạo
        return {
            'name': _('Phiếu lương mới'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'res_id': payslip.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_loans(self):
        self.ensure_one()
        return {
            'name': _('Khoản vay/Tạm ứng'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.loan',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_view_rewards(self):
        self.ensure_one()
        return {
            'name': _('Khen thưởng'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.reward',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_view_disciplines(self):
        self.ensure_one()
        return {
            'name': _('Kỷ luật'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.discipline',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_view_dependents(self):
        self.ensure_one()
        return {
            'name': _('Người phụ thuộc'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee.dependent',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
