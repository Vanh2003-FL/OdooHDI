# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PayslipBatchCreate(models.TransientModel):
    _name = 'hr.payslip.batch.create'
    _description = 'Wizard tạo hàng loạt phiếu lương'

    payslip_run_id = fields.Many2one('hr.payslip.run', 'Batch lương', required=True)
    date_from = fields.Date('Từ ngày', required=True)
    date_to = fields.Date('Đến ngày', required=True)
    
    employee_ids = fields.Many2many('hr.employee', string='Nhân viên')
    department_ids = fields.Many2many('hr.department', string='Phòng ban')
    
    # Filters
    only_active = fields.Boolean('Chỉ nhân viên đang làm', default=True)
    only_with_contract = fields.Boolean('Chỉ NV có hợp đồng', default=True)

    def action_create_payslips(self):
        """Tạo phiếu lương hàng loạt"""
        self.ensure_one()
        
        # Xác định danh sách nhân viên
        domain = []
        
        if self.only_active:
            domain.append(('active', '=', True))
        
        if self.employee_ids:
            domain.append(('id', 'in', self.employee_ids.ids))
        elif self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))
        
        employees = self.env['hr.employee'].search(domain)
        
        if not employees:
            raise UserError(_('Không tìm thấy nhân viên nào phù hợp!'))
        
        # Tạo payslips
        payslips = self.env['hr.payslip']
        errors = []
        
        for employee in employees:
            # Tìm contract đang active
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'open'),
                ('date_start', '<=', self.date_to),
                '|',
                ('date_end', '=', False),
                ('date_end', '>=', self.date_from)
            ], limit=1)
            
            if not contract and self.only_with_contract:
                errors.append(f"{employee.name}: Không có hợp đồng")
                continue
            
            # Kiểm tra đã có payslip chưa
            existing = self.env['hr.payslip'].search([
                ('employee_id', '=', employee.id),
                ('date_from', '=', self.date_from),
                ('date_to', '=', self.date_to),
                ('company_id', '=', self.env.company.id)
            ])
            
            if existing:
                errors.append(f"{employee.name}: Đã có phiếu lương")
                continue
            
            # Tạo payslip
            vals = {
                'employee_id': employee.id,
                'contract_id': contract.id if contract else False,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'payslip_run_id': self.payslip_run_id.id,
                'name': f"Lương {employee.name} - {self.date_from.strftime('%m/%Y')}",
            }
            
            if contract and contract.structure_type_id:
                # Tìm structure tương ứng
                struct = self.env['hr.payroll.structure'].search([
                    ('type_id', '=', contract.structure_type_id.id)
                ], limit=1)
                if not struct:
                    # Dùng structure mặc định
                    struct = self.env['hr.payroll.structure'].search([], limit=1)
                vals['struct_id'] = struct.id if struct else False
            
            payslip = self.env['hr.payslip'].create(vals)
            payslips |= payslip
        
        # Thông báo kết quả
        message = _('Đã tạo %s phiếu lương') % len(payslips)
        if errors:
            message += '\n\nLỗi:\n' + '\n'.join(errors)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Hoàn tất'),
                'message': message,
                'type': 'success' if not errors else 'warning',
                'sticky': True,
            }
        }
