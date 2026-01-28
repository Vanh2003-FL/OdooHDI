# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockSerialItem(models.Model):
    _name = 'stock.serial.item'
    _description = 'Serial Item trong Lot'
    _order = 'sequence, id'

    lot_id = fields.Many2one('stock.lot', string='Lot', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Thứ tự', default=10)
    serial_number = fields.Char(string='Serial/Barcode', required=True)
    barcode = fields.Char(string='Barcode/QR', help='Barcode hoặc QR code trên sản phẩm')
    product_id = fields.Many2one('product.product', string='Sản phẩm', 
                                  related='lot_id.product_id', readonly=True)
    product_code = fields.Char(string='Mã sản phẩm', related='product_id.default_code', readonly=True)
    note = fields.Text(string='Ghi chú')
    is_picked = fields.Boolean(string='Đã xuất kho', default=False, 
                                help='Đánh dấu serial đã được xuất kho')
    
    _sql_constraints = [
        ('unique_serial_lot', 'UNIQUE(lot_id, serial_number)', 'Serial này đã tồn tại trong lot!'),
    ]
    
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.product_code} - {record.serial_number}" if record.product_code else record.serial_number
            result.append((record.id, name))
        return result
