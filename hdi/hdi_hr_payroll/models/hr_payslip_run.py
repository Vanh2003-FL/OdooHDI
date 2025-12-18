# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayslipRun(models.Model):
    _name = 'hr.payslip.run'
    _description = 'Batch tính lương'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name = fields.Char('Tên batch', required=True, tracking=True)
    
    date_start = fields.Date('Từ ngày', required=True, tracking=True)
    date_end = fields.Date('Đến ngày', required=True, tracking=True)
    
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('close', 'Đã đóng')
    ], 'Trạng thái', default='draft', tracking=True)
    
    slip_ids = fields.One2many('hr.payslip', 'payslip_run_id', 'Phiếu lương')
    payslip_count = fields.Integer('Số phiếu lương', compute='_compute_payslip_count')
    
    company_id = fields.Many2one('res.company', 'Công ty', default=lambda self: self.env.company, required=True)
    
    note = fields.Text('Ghi chú')

    @api.depends('slip_ids')
    def _compute_payslip_count(self):
        for run in self:
            run.payslip_count = len(run.slip_ids)

    def action_close(self):
        """Đóng batch"""
        return self.write({'state': 'close'})

    def action_draft(self):
        """Mở lại batch"""
        return self.write({'state': 'draft'})

    def action_open_payslips(self):
        """Xem danh sách phiếu lương trong batch"""
        self.ensure_one()
        return {
            'name': _('Phiếu lương'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_mode': 'tree,form',
            'domain': [('payslip_run_id', '=', self.id)],
            'context': {
                'default_payslip_run_id': self.id,
                'default_date_from': self.date_start,
                'default_date_to': self.date_end,
            }
        }

    def action_create_payslips(self):
        """Mở wizard tạo hàng loạt phiếu lương"""
        self.ensure_one()
        return {
            'name': _('Tạo phiếu lương hàng loạt'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.batch.create',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payslip_run_id': self.id,
                'default_date_from': self.date_start,
                'default_date_to': self.date_end,
            }
        }

    def action_compute_all_payslips(self):
        """Tính tất cả phiếu lương trong batch"""
        self.ensure_one()
        payslips = self.slip_ids.filtered(lambda p: p.state == 'draft')
        if not payslips:
            raise UserError(_('Không có phiếu lương nào ở trạng thái Nháp'))
        
        payslips.compute_sheet()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Thành công'),
                'message': _('Đã tính %s phiếu lương') % len(payslips),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_verify_all_payslips(self):
        """Gửi duyệt tất cả phiếu lương"""
        self.ensure_one()
        payslips = self.slip_ids.filtered(lambda p: p.state == 'draft')
        if payslips:
            payslips.action_payslip_verify()

    def action_done_all_payslips(self):
        """Duyệt tất cả phiếu lương"""
        self.ensure_one()
        payslips = self.slip_ids.filtered(lambda p: p.state == 'verify')
        if payslips:
            payslips.action_payslip_done()
