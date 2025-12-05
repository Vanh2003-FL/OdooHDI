# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HdiInventoryCheck(models.Model):
    """Kiểm kê WMS - 2 loại: Batch và Barcode"""
    _name = 'hdi.inventory.check'
    _description = 'Kiểm kê WMS'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(
        string='Số phiếu kiểm kê',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
        tracking=True,
    )

    # ===== LOẠI KIỂM KÊ =====
    check_type = fields.Selection([
        ('batch', 'KK_NV_01: Kiểm kê Batch'),
        ('barcode', 'KK_NV_02: Kiểm kê Barcode'),
    ], string='Loại kiểm kê',
       required=True,
       default='batch',
       tracking=True,
       help="Chọn phương thức kiểm kê")

    state = fields.Selection([
        ('draft', 'Nháp'),
        ('in_progress', 'Đang kiểm kê'),
        ('review', 'Chờ duyệt'),
        ('done', 'Hoàn thành'),
        ('cancel', 'Đã hủy'),
    ], string='Trạng thái',
       default='draft',
       required=True,
       tracking=True)

    # ===== THÔNG TIN CƠ BẢN =====
    location_id = fields.Many2one(
        'stock.location',
        string='Vị trí kiểm kê',
        required=True,
        domain=[('usage', '=', 'internal')],
        tracking=True,
    )

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Kho',
        related='location_id.warehouse_id',
        store=True,
    )

    responsible_id = fields.Many2one(
        'res.users',
        string='Người phụ trách',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )

    scheduled_date = fields.Datetime(
        string='Ngày kiểm kê dự kiến',
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )

    actual_start_date = fields.Datetime(
        string='Thời gian bắt đầu thực tế',
        readonly=True,
        tracking=True,
    )

    actual_end_date = fields.Datetime(
        string='Thời gian kết thúc thực tế',
        readonly=True,
        tracking=True,
    )

    # ===== CHI TIẾT KIỂM KÊ =====
    line_ids = fields.One2many(
        'hdi.inventory.check.line',
        'check_id',
        string='Chi tiết kiểm kê',
    )

    # ===== QR/BARCODE SCAN (cho KK_NV_02) =====
    scan_mode = fields.Selection([
        ('batch', 'Quét Batch'),
        ('product', 'Quét Sản phẩm'),
        ('location', 'Quét Vị trí'),
    ], string='Chế độ quét',
       default='batch',
       help="Chế độ quét cho kiểm kê barcode")

    last_scanned_code = fields.Char(
        string='Mã vừa quét',
        readonly=True,
    )

    scanned_count = fields.Integer(
        string='Số lần quét',
        compute='_compute_scan_count',
        store=True,
    )

    # ===== THỐNG KÊ =====
    total_lines = fields.Integer(
        string='Tổng số dòng',
        compute='_compute_statistics',
        store=True,
    )

    checked_lines = fields.Integer(
        string='Đã kiểm',
        compute='_compute_statistics',
        store=True,
    )

    discrepancy_lines = fields.Integer(
        string='Có chênh lệch',
        compute='_compute_statistics',
        store=True,
    )

    notes = fields.Text(string='Ghi chú')

    # ===== APPROVAL =====
    approved_by = fields.Many2one(
        'res.users',
        string='Người duyệt',
        readonly=True,
    )

    approval_date = fields.Datetime(
        string='Ngày duyệt',
        readonly=True,
    )

    @api.depends('line_ids', 'line_ids.is_checked', 'line_ids.has_discrepancy')
    def _compute_statistics(self):
        for check in self:
            check.total_lines = len(check.line_ids)
            check.checked_lines = len(check.line_ids.filtered('is_checked'))
            check.discrepancy_lines = len(check.line_ids.filtered('has_discrepancy'))

    @api.depends('line_ids', 'line_ids.scanned_qty')
    def _compute_scan_count(self):
        for check in self:
            check.scanned_count = sum(check.line_ids.mapped('scanned_qty'))

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            check_type = vals.get('check_type', 'batch')
            if check_type == 'batch':
                vals['name'] = self.env['ir.sequence'].next_by_code('hdi.inventory.check.batch') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('hdi.inventory.check.barcode') or _('New')
        return super().create(vals)

    # ===== ACTIONS =====
    def action_start_check(self):
        """Bắt đầu kiểm kê"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Chỉ có thể bắt đầu kiểm kê từ trạng thái Nháp.'))
        
        self.state = 'in_progress'
        self.actual_start_date = fields.Datetime.now()
        
        # Generate lines based on check type
        if self.check_type == 'batch':
            self._generate_batch_lines()
        else:
            self._generate_barcode_lines()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Bắt đầu kiểm kê'),
                'message': _('Đã bắt đầu kiểm kê %s') % self.name,
                'type': 'success',
            }
        }

    def _generate_batch_lines(self):
        """Generate lines for Batch check - KK_NV_01"""
        self.ensure_one()
        
        # Tìm tất cả batch tại vị trí này
        batches = self.env['hdi.batch'].search([
            ('location_id', '=', self.location_id.id),
            ('state', '=', 'stored'),
        ])
        
        lines_vals = []
        for batch in batches:
            lines_vals.append({
                'check_id': self.id,
                'batch_id': batch.id,
                'product_id': batch.product_id.id,
                'location_id': self.location_id.id,
                'system_qty': batch.quantity,
            })
        
        self.line_ids = [(0, 0, vals) for vals in lines_vals]

    def _generate_barcode_lines(self):
        """Generate lines for Barcode check - KK_NV_02"""
        self.ensure_one()
        
        # Tìm tất cả quants tại vị trí này
        quants = self.env['stock.quant'].search([
            ('location_id', '=', self.location_id.id),
            ('quantity', '>', 0),
        ])
        
        lines_vals = []
        for quant in quants:
            lines_vals.append({
                'check_id': self.id,
                'product_id': quant.product_id.id,
                'location_id': quant.location_id.id,
                'batch_id': quant.batch_id.id if quant.batch_id else False,
                'system_qty': quant.quantity,
            })
        
        self.line_ids = [(0, 0, vals) for vals in lines_vals]

    def action_complete_check(self):
        """Hoàn thành kiểm kê"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_('Chỉ có thể hoàn thành từ trạng thái Đang kiểm kê.'))
        
        # Check all lines are checked
        unchecked = self.line_ids.filtered(lambda l: not l.is_checked)
        if unchecked:
            raise UserError(_('Còn %d dòng chưa kiểm. Vui lòng kiểm tra đầy đủ.') % len(unchecked))
        
        self.state = 'review'
        self.actual_end_date = fields.Datetime.now()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Hoàn thành kiểm kê'),
                'message': _('Kiểm kê hoàn thành, chờ duyệt'),
                'type': 'success',
            }
        }

    def action_approve(self):
        """Duyệt kiểm kê"""
        self.ensure_one()
        if self.state != 'review':
            raise UserError(_('Chỉ có thể duyệt từ trạng thái Chờ duyệt.'))
        
        self.state = 'done'
        self.approved_by = self.env.user
        self.approval_date = fields.Datetime.now()
        
        # Create adjustment moves for discrepancies
        self._create_adjustment_moves()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã duyệt'),
                'message': _('Phiếu kiểm kê đã được duyệt'),
                'type': 'success',
            }
        }

    def _create_adjustment_moves(self):
        """Tạo phiếu điều chỉnh cho chênh lệch"""
        self.ensure_one()
        
        discrepancy_lines = self.line_ids.filtered('has_discrepancy')
        if not discrepancy_lines:
            return
        
        # TODO: Tạo stock moves để điều chỉnh tồn kho
        # Sẽ implement chi tiết sau
        pass

    def action_cancel(self):
        """Hủy kiểm kê"""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_('Không thể hủy phiếu kiểm kê đã duyệt.'))
        
        self.state = 'cancel'

    def on_barcode_scanned(self, barcode):
        """Xử lý khi quét barcode - cho KK_NV_02"""
        self.ensure_one()
        if self.check_type != 'barcode':
            raise UserError(_('Quét barcode chỉ áp dụng cho Kiểm kê Barcode.'))
        
        self.last_scanned_code = barcode
        
        # Tìm line tương ứng và update
        if self.scan_mode == 'batch':
            batch = self.env['hdi.batch'].search([('barcode', '=', barcode)], limit=1)
            if batch:
                line = self.line_ids.filtered(lambda l: l.batch_id == batch)
                if line:
                    line.actual_qty += 1
                    line.scanned_qty += 1
                    return True
        
        elif self.scan_mode == 'product':
            product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1)
            if product:
                line = self.line_ids.filtered(lambda l: l.product_id == product and not l.is_checked)
                if line:
                    line = line[0]
                    line.actual_qty += 1
                    line.scanned_qty += 1
                    return True
        
        return False


class HdiInventoryCheckLine(models.Model):
    """Chi tiết kiểm kê"""
    _name = 'hdi.inventory.check.line'
    _description = 'Chi tiết kiểm kê WMS'
    _order = 'sequence, id'

    check_id = fields.Many2one(
        'hdi.inventory.check',
        string='Phiếu kiểm kê',
        required=True,
        ondelete='cascade',
        index=True,
    )

    sequence = fields.Integer(string='Thứ tự', default=10)

    product_id = fields.Many2one(
        'product.product',
        string='Sản phẩm',
        required=True,
    )

    location_id = fields.Many2one(
        'stock.location',
        string='Vị trí',
        required=True,
    )

    batch_id = fields.Many2one(
        'hdi.batch',
        string='Batch/LPN',
    )

    # ===== SỐ LƯỢNG =====
    system_qty = fields.Float(
        string='SL hệ thống',
        digits='Product Unit of Measure',
        default=0.0,
    )

    actual_qty = fields.Float(
        string='SL thực tế',
        digits='Product Unit of Measure',
        default=0.0,
    )

    scanned_qty = fields.Float(
        string='SL đã quét',
        digits='Product Unit of Measure',
        default=0.0,
        readonly=True,
    )

    discrepancy_qty = fields.Float(
        string='Chênh lệch',
        compute='_compute_discrepancy',
        store=True,
        digits='Product Unit of Measure',
    )

    # ===== TRẠNG THÁI =====
    is_checked = fields.Boolean(
        string='Đã kiểm',
        default=False,
    )

    has_discrepancy = fields.Boolean(
        string='Có chênh lệch',
        compute='_compute_discrepancy',
        store=True,
    )

    notes = fields.Text(string='Ghi chú')

    @api.depends('system_qty', 'actual_qty')
    def _compute_discrepancy(self):
        for line in self:
            line.discrepancy_qty = line.actual_qty - line.system_qty
            line.has_discrepancy = abs(line.discrepancy_qty) > 0.01

    def action_confirm_check(self):
        """Xác nhận đã kiểm dòng này"""
        for line in self:
            line.is_checked = True
