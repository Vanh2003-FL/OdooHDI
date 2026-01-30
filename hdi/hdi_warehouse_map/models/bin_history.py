# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BinHistory(models.Model):
    _name = 'bin.history'
    _description = 'Bin Movement History'
    _order = 'date desc'
    _rec_name = 'reference'
    
    date = fields.Datetime(string='Date', required=True, default=fields.Datetime.now, index=True)
    bin_id = fields.Many2one('warehouse.bin', string='Bin', required=True, ondelete='cascade', index=True)
    move_id = fields.Many2one('stock.move', string='Stock Move', ondelete='set null')
    
    product_id = fields.Many2one('product.product', string='Product', required=True, index=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial', index=True)
    
    quantity = fields.Float(string='Quantity', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    
    operation_type = fields.Selection([
        ('in', 'Incoming'),
        ('out', 'Outgoing'),
        ('adjustment', 'Inventory Adjustment'),
    ], string='Operation Type', required=True, index=True)
    
    reference = fields.Char(string='Reference', index=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    
    notes = fields.Text(string='Notes')
