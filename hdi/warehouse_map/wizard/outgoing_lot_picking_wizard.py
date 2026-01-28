# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from collections import defaultdict


class OutgoingLotPickingWizard(models.TransientModel):
    """Wizard xuất kho từ sơ đồ: Chọn Lot → Quét Sản Phẩm → Tạo Phiếu Xuất"""
    _name = 'outgoing.lot.picking.wizard'
    _description = 'Wizard Xuất Kho Theo Lot'

    # Bước 1: Chọn Lot
    warehouse_map_id = fields.Many2one('warehouse.map', string='Sơ đồ kho', required=True, readonly=True)
    quant_id = fields.Many2one('stock.quant', string='Chọn Lot/Quant', required=True,
                               domain="[('display_on_map', '=', True), ('quantity', '>', 0)]")
    
    lot_id = fields.Many2one('stock.lot', string='Lot', readonly=True, related='quant_id.lot_id')
    product_id = fields.Many2one('product.product', string='Sản phẩm', readonly=True, related='quant_id.product_id')
    location_id = fields.Many2one('stock.location', string='Vị trí', readonly=True, related='quant_id.location_id')
    quantity_available = fields.Float(string='Số lượng có sẵn', readonly=True, related='quant_id.quantity')
    
    # Danh sách serial trong lot (chỉ đọc)
    serial_item_ids = fields.One2many('stock.serial.item', compute='_compute_serial_items',
                                      string='Danh sách Serial trong Lot')
    
    # Bước 2: Quét Sản Phẩm (nhập barcode)
    scanned_barcode = fields.Char(string='Quét Barcode Sản Phẩm',
                                  help='Quét từng barcode sản phẩm/serial từ lot')
    scanned_product_ids = fields.Many2many('stock.wizard.outgoing.product', 'outgoing_wizard_scanned_rel',
                                           string='Sản phẩm đã quét')
    
    # Tổng số lượng cần xuất
    total_quantity = fields.Float(string='Tổng số lượng xuất', compute='_compute_total_quantity')
    
    # Thông tin phiếu xuất
    destination_location_id = fields.Many2one('stock.location', string='Vị trí đích (Khách)',
                                              domain="[('usage', '=', 'customer')]")
    picking_type_id = fields.Many2one('stock.picking.type', string='Loại phiếu xuất',
                                      domain="[('code', '=', 'outgoing')]")
    
    @api.depends('lot_id')
    def _compute_serial_items(self):
        """Lấy danh sách serial từ lot"""
        for wizard in self:
            if wizard.lot_id:
                wizard.serial_item_ids = self.env['stock.serial.item'].search([
                    ('lot_id', '=', wizard.lot_id.id)
                ], order='sequence asc')
            else:
                wizard.serial_item_ids = False
    
    @api.depends('scanned_product_ids')
    def _compute_total_quantity(self):
        """Tính tổng số lượng quét được"""
        for wizard in self:
            wizard.total_quantity = len(wizard.scanned_product_ids)
    
    @api.model
    def default_get(self, fields_list):
        """Load dữ liệu từ context"""
        result = super().default_get(fields_list)
        
        # Lấy warehouse_map_id từ context
        if self._context.get('default_warehouse_map_id'):
            result['warehouse_map_id'] = self._context.get('default_warehouse_map_id')
        
        # Lấy quant_id từ context (quant được chọn từ sơ đồ)
        if self._context.get('default_quant_id'):
            result['quant_id'] = self._context.get('default_quant_id')
        
        # Auto-set destination location
        quant_id = self._context.get('default_quant_id')
        if quant_id:
            quant = self.env['stock.quant'].browse(quant_id)
            warehouse = quant.location_id.warehouse_id
            if warehouse:
                # Lấy customer location mặc định
                customer_location = self.env['stock.location'].search([
                    ('usage', '=', 'customer')
                ], limit=1)
                if customer_location:
                    result['destination_location_id'] = customer_location.id
                
                # Lấy picking type
                if warehouse.out_type_id:
                    result['picking_type_id'] = warehouse.out_type_id.id
        
        return result
    
    def action_scan_product(self):
        """Quét barcode sản phẩm và thêm vào danh sách"""
        self.ensure_one()
        
        if not self.scanned_barcode:
            raise UserError(_('Vui lòng quét barcode sản phẩm!'))
        
        if not self.lot_id:
            raise UserError(_('Vui lòng chọn lot trước!'))
        
        barcode = self.scanned_barcode.strip()
        
        # Tìm serial_item trong lot khớp với barcode
        serial_item = self.env['stock.serial.item'].search([
            ('lot_id', '=', self.lot_id.id),
            ('serial_number', '=', barcode)
        ], limit=1)
        
        if not serial_item:
            raise UserError(_(
                f'❌ Barcode "{barcode}" không tồn tại trong Lot {self.lot_id.name}!\n'
                f'Danh sách serial có sẵn:\n' +
                '\n'.join([f'- {s.serial_number}' for s in self.serial_item_ids[:10]])
            ))
        
        # Kiểm tra không quét trùng
        existing = self.scanned_product_ids.filtered(
            lambda x: x.serial_item_id.id == serial_item.id
        )
        if existing:
            raise UserError(_(f'Barcode "{barcode}" đã được quét rồi!'))
        
        # Thêm vào danh sách
        wizard_product = self.env['stock.wizard.outgoing.product'].create({
            'wizard_id': self.id,
            'serial_item_id': serial_item.id,
            'product_id': self.product_id.id,
            'serial_number': barcode,
            'sequence': len(self.scanned_product_ids) + 1,
        })
        
        self.scanned_product_ids = [(4, wizard_product.id)]
        
        # Clear input
        self.scanned_barcode = ''
        
        # Thông báo
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('✅ Thành công'),
                'message': _(f'Đã quét: {barcode}'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_remove_scanned(self):
        """Xoá sản phẩm khỏi danh sách quét"""
        self.ensure_one()
        
        # Xoá sản phẩm quét cuối cùng
        if self.scanned_product_ids:
            last_product = self.scanned_product_ids[-1]
            self.scanned_product_ids = [(3, last_product.id)]
    
    def action_clear_all(self):
        """Xoá tất cả sản phẩm đã quét"""
        self.ensure_one()
        self.scanned_product_ids = [(5, 0)]  # Clear all
    
    def action_create_picking(self):
        """Tạo phiếu xuất kho từ danh sách quét"""
        self.ensure_one()
        
        if not self.scanned_product_ids:
            raise UserError(_('Vui lòng quét ít nhất 1 sản phẩm!'))
        
        if not self.picking_type_id:
            raise UserError(_('Vui lòng chọn loại phiếu xuất!'))
        
        if not self.destination_location_id:
            raise UserError(_('Vui lòng chọn vị trí đích!'))
        
        # Tạo picking
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.destination_location_id.id,
            'origin': f'Xuất từ Lot: {self.lot_id.name}',
        })
        
        # Tạo stock.move (1 move cho tất cả sản phẩm)
        move = self.env['stock.move'].create({
            'name': self.product_id.name,
            'product_id': self.product_id.id,
            'product_uom_qty': self.total_quantity,
            'product_uom': self.product_id.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.destination_location_id.id,
        })
        
        # Tạo move_line cho từng serial quét được
        move_lines = []
        for idx, scanned_product in enumerate(self.scanned_product_ids, 1):
            move_line = self.env['stock.move.line'].create({
                'move_id': move.id,
                'product_id': self.product_id.id,
                'lot_id': self.lot_id.id,  # ← Lot có barcode
                'serial_number': scanned_product.serial_number,  # ← Barcode sản phẩm để track
                'quantity': 1,  # 1 serial = 1 sản phẩm
                'product_uom_id': self.product_id.uom_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.destination_location_id.id,
                'picking_id': picking.id,
            })
            move_lines.append(move_line)
        
        # Confirm picking
        picking.action_confirm()
        
        # Navigate to picking form
        return {
            'type': 'ir.actions.act_window',
            'name': _('Phiếu Xuất Kho'),
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'view_mode': 'form',
            'target': 'current',
            'views': [[False, 'form']],
        }


class StockWizardOutgoingProduct(models.TransientModel):
    """Sản phẩm quét được trong wizard xuất kho"""
    _name = 'stock.wizard.outgoing.product'
    _description = 'Sản phẩm Quét trong Wizard Xuất Kho'
    _order = 'sequence'
    
    wizard_id = fields.Many2one('outgoing.lot.picking.wizard', string='Wizard', ondelete='cascade')
    serial_item_id = fields.Many2one('stock.serial.item', string='Serial Item')
    product_id = fields.Many2one('product.product', string='Sản phẩm')
    serial_number = fields.Char(string='Barcode Quét')
    sequence = fields.Integer(string='Thứ tự')
    
    def name_get(self):
        """Hiển thị serial_number trong list"""
        result = []
        for record in self:
            name = f"{record.sequence}. {record.serial_number}"
            result.append((record.id, name))
        return result
