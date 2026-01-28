# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockLocation(models.Model):
    _inherit = 'stock.location'

    display_on_map = fields.Boolean(string='Hiển thị trên sơ đồ', default=True)
    color_code = fields.Char(string='Mã màu', help='Mã màu hiển thị trên sơ đồ (hex color)')
    warehouse_map_id = fields.Many2one('warehouse.map', string='Sơ đồ kho',
                                       help='Sơ đồ kho tương ứng với vị trí này')


class StockLot(models.Model):
    _inherit = 'stock.lot'
    
    barcode = fields.Char(string='Barcode Lô', unique=True, help='Barcode duy nhất cho lô')
    serial_ids = fields.One2many('stock.serial.item', 'lot_id', string='Danh sách Serial')
    serial_count = fields.Integer(string='Số serial', compute='_compute_serial_count', store=True)
    
    @api.depends('serial_ids')
    def _compute_serial_count(self):
        """Tính số serial trong lot"""
        for lot in self:
            lot.serial_count = len(lot.serial_ids)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
    
    posx = fields.Integer(string='Vị trí X (Cột)', help='Vị trí cột trong sơ đồ kho')
    posy = fields.Integer(string='Vị trí Y (Hàng)', help='Vị trí hàng trong sơ đồ kho')
    posz = fields.Integer(string='Vị trí Z (Tầng)', default=0, help='Tầng/kệ trong sơ đồ kho')
    position_assigned = fields.Boolean(string='Đã gán vị trí', default=False, help='Đánh dấu khi user gán vị trí thủ công')
    
    def action_assign_warehouse_map_position(self):
        """Mở wizard gán vị trí từ sơ đồ kho"""
        self.ensure_one()
        
        return {
            'name': 'Gán vị trí trên sơ đồ kho',
            'type': 'ir.actions.act_window',
            'res_model': 'move.line.warehouse.map.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_line_id': self.id,
                'default_picking_id': self.picking_id.id,
            }
        }


class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    posx = fields.Integer(string='Vị trí X (Cột)', help='Vị trí cột trong sơ đồ kho')
    posy = fields.Integer(string='Vị trí Y (Hàng)', help='Vị trí hàng trong sơ đồ kho')
    posz = fields.Integer(string='Vị trí Z (Tầng)', default=0, help='Tầng/kệ trong sơ đồ kho')
    display_on_map = fields.Boolean(string='Hiển thị trên sơ đồ', default=False)
    
    days_in_stock = fields.Integer(string='Số ngày trong kho', compute='_compute_days_in_stock', store=False)
    
    @api.depends('in_date')
    def _compute_days_in_stock(self):
        """Tính số ngày từ khi nhập kho đến hiện tại"""
        from datetime import datetime
        today = datetime.now()
        
        for quant in self:
            if quant.in_date:
                delta = today - quant.in_date
                quant.days_in_stock = delta.days
            else:
                quant.days_in_stock = 0
    
    def action_pick_products(self):
        """Action lấy hàng từ vị trí"""
        self.ensure_one()
        return {
            'name': 'Lấy hàng',
            'type': 'ir.actions.act_window',
            'res_model': 'location.action.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_location_id': self.location_id.id,
                'default_product_id': self.product_id.id,
                'default_lot_id': self.lot_id.id if self.lot_id else False,
                'default_quantity': self.quantity - self.reserved_quantity,
                'default_action_type': 'pick',
            }
        }
    
    def action_outgoing_lot_picking(self):
        """Action xuất kho với quét barcode từ sơ đồ"""
        self.ensure_one()
        
        # Kiểm tra quant có lot không
        if not self.lot_id:
            raise UserError(_('Sản phẩm này không có Lot! Vui lòng chọn vị trí khác.'))
        
        # Mở wizard xuất kho
        return {
            'name': _('Xuất Kho Theo Lot'),
            'type': 'ir.actions.act_window',
            'res_model': 'outgoing.lot.picking.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_quant_id': self.id,
                'default_warehouse_map_id': self.location_id.warehouse_map_id.id if self.location_id.warehouse_map_id else False,
            }
        }
    
    def action_move_location(self):
        """Action chuyển vị trí"""
        self.ensure_one()
        return {
            'name': 'Chuyển vị trí',
            'type': 'ir.actions.act_window',
            'res_model': 'location.action.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_location_id': self.location_id.id,
                'default_product_id': self.product_id.id,
                'default_lot_id': self.lot_id.id if self.lot_id else False,
                'default_quantity': self.quantity - self.reserved_quantity,
                'default_action_type': 'move',
            }
        }
    
    def action_transfer_warehouse(self):
        """Action chuyển kho"""
        self.ensure_one()
        return {
            'name': 'Chuyển kho',
            'type': 'ir.actions.act_window',
            'res_model': 'location.action.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_location_id': self.location_id.id,
                'default_product_id': self.product_id.id,
                'default_lot_id': self.lot_id.id if self.lot_id else False,
                'default_quantity': self.quantity - self.reserved_quantity,
                'default_action_type': 'transfer',
            }
        }
    
    def action_view_stock(self):
        """Xem chi tiết quant"""
        self.ensure_one()
        return {
            'name': f'Chi tiết - {self.product_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

