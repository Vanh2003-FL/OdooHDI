# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    # ===== INVENTORY CHECK TYPE (2 workflows) =====
    check_type = fields.Selection([
        ('batch', 'KK_NV_01 - Kiểm kê theo Batch'),
        ('barcode', 'KK_NV_02 - Kiểm kê theo Barcode')
    ], string='Loại kiểm kê', default='batch',
       help="Chọn luồng kiểm kê: Batch (theo lô) hoặc Barcode (quét từng mã)")
    
    # ===== BATCH LINK =====
    batch_id = fields.Many2one(
        'hdi.batch',
        string='Batch/LPN',
        index=True,
        help="Batch containing this inventory quant"
    )
    
    is_batched = fields.Boolean(
        compute='_compute_is_batched',
        store=True,
        string='Is Batched',
    )
    
    # ===== BARCODE SCANNING FIELDS =====
    scan_mode = fields.Boolean(
        string='Chế độ quét',
        default=False,
        help="Bật để quét barcode liên tục (chỉ dùng cho KK_NV_02)"
    )
    
    last_scanned_code = fields.Char(
        string='Mã vừa quét',
        readonly=True,
        help="Barcode cuối cùng được quét"
    )
    
    scanned_count = fields.Integer(
        string='Số lần quét',
        default=0,
        help="Đếm số lần quét barcode"
    )
    
    @api.depends('batch_id')
    def _compute_is_batched(self):
        """Check if quant is part of a batch"""
        for quant in self:
            quant.is_batched = bool(quant.batch_id)
    
    def write(self, vals):
        result = super().write(vals)
        
        # If location changed, update batch location
        if 'location_id' in vals:
            for quant in self:
                if quant.batch_id and quant.batch_id.location_id != quant.location_id:
                    # Sync batch location with quant location
                    quant.batch_id.location_id = quant.location_id
        
        # Recompute batch quantities if quantity changed
        if 'quantity' in vals or 'reserved_quantity' in vals:
            batches = self.mapped('batch_id').filtered(lambda b: b)
            batches._compute_quantities()
        
        return result

    @api.onchange('check_type')
    def _onchange_check_type(self):
        """Reset barcode fields when switching check type"""
        if self.check_type != 'barcode':
            self.scan_mode = False
            self.last_scanned_code = False
            self.scanned_count = 0
    
    def action_toggle_scan_mode(self):
        """Toggle barcode scanning mode (for KK_NV_02)"""
        self.ensure_one()
        self.scan_mode = not self.scan_mode
        if self.scan_mode:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Chế độ quét Barcode',
                    'message': 'Đã bật chế độ quét. Vui lòng quét barcode sản phẩm.',
                    'type': 'success',
                    'sticky': False,
                }
            }
    
    def on_barcode_scanned(self, barcode):
        """Handle barcode scanning for KK_NV_02 workflow"""
        self.ensure_one()
        
        if not self.scan_mode:
            return {
                'warning': {
                    'title': 'Lỗi',
                    'message': 'Vui lòng bật chế độ quét trước!'
                }
            }
        
        # Update scanned info
        self.last_scanned_code = barcode
        self.scanned_count += 1
        
        # Try to find product by barcode
        product = self.env['product.product'].search([
            '|', ('barcode', '=', barcode),
            ('default_code', '=', barcode)
        ], limit=1)
        
        if product:
            # Update inventory quantity for this product
            self.product_id = product
            self.inventory_quantity += 1  # Increment counted quantity
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Đã quét',
                    'message': f'Sản phẩm: {product.name} | Tổng: {self.inventory_quantity}',
                    'type': 'info',
                    'sticky': False,
                }
            }
        else:
            return {
                'warning': {
                    'title': 'Không tìm thấy',
                    'message': f'Không tìm thấy sản phẩm với barcode: {barcode}'
                }
            }

