# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class LotHistory(models.Model):
    _name = 'lot.history'
    _description = 'Lot Movement History'
    _order = 'date desc'
    _rec_name = 'reference'
    
    date = fields.Datetime(string='Date', required=True, default=fields.Datetime.now, index=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial', required=True, ondelete='cascade', index=True)
    move_id = fields.Many2one('stock.move', string='Stock Move', ondelete='set null')
    
    product_id = fields.Many2one('product.product', related='lot_id.product_id', string='Product', store=True)
    
    location_from_id = fields.Many2one('stock.location', string='From Location')
    location_to_id = fields.Many2one('stock.location', string='To Location')
    
    bin_from_id = fields.Many2one('warehouse.bin', related='location_from_id.bin_id', 
                                   string='From Bin', store=True)
    bin_to_id = fields.Many2one('warehouse.bin', related='location_to_id.bin_id', 
                                 string='To Bin', store=True)
    
    quantity = fields.Float(string='Quantity', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    
    operation_type = fields.Selection([
        ('in', 'Incoming'),
        ('out', 'Outgoing'),
        ('internal', 'Internal Transfer'),
        ('adjustment', 'Inventory Adjustment'),
    ], string='Operation Type', required=True, index=True)
    
    reference = fields.Char(string='Reference', index=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    
    notes = fields.Text(string='Notes')
