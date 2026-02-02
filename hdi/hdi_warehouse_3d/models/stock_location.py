# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockLocation(models.Model):
    _inherit = 'stock.location'

    # Link to 3D warehouse structure
    shelf_id = fields.Many2one('warehouse.shelf', string='Shelf', ondelete='set null')
    area_id = fields.Many2one('warehouse.area', related='shelf_id.area_id', store=True, string='Area')
    
    # 3D coordinates
    coordinate_x = fields.Float(string='X Coordinate', help='X position in warehouse grid')
    coordinate_y = fields.Float(string='Y Coordinate', help='Y position in warehouse grid')
    coordinate_z = fields.Float(string='Z Coordinate (Height)', help='Height from ground')
    
    # Bin properties
    level_number = fields.Integer(string='Level Number', help='Shelf level (1=bottom)')
    bin_number = fields.Integer(string='Bin Number', help='Bin position on level')
    
    # Physical dimensions
    bin_width = fields.Float(string='Width (m)', default=1.0)
    bin_depth = fields.Float(string='Depth (m)', default=0.8)
    bin_height = fields.Float(string='Height (m)', default=0.5)
    max_capacity = fields.Float(string='Max Capacity', default=50)
    max_weight = fields.Float(string='Max Weight (kg)', default=100)
    
    # Visual properties
    display_color = fields.Char(string='Display Color', compute='_compute_display_color')
    bin_state = fields.Selection([
        ('empty', 'Empty'),
        ('available', 'Available'),
        ('full', 'Full'),
        ('blocked', 'Blocked')
    ], string='Bin State', compute='_compute_bin_state')
    
    # Blocking
    is_blocked = fields.Boolean(string='Blocked', default=False)
    block_reason = fields.Text(string='Block Reason')

    @api.depends('quant_ids', 'quant_ids.quantity', 'is_blocked')
    def _compute_bin_state(self):
        for location in self:
            if location.usage != 'internal' or not location.shelf_id:
                location.bin_state = False
                continue
                
            if location.is_blocked:
                location.bin_state = 'blocked'
            elif not location.quant_ids or sum(location.quant_ids.mapped('quantity')) == 0:
                location.bin_state = 'empty'
            elif sum(location.quant_ids.mapped('quantity')) >= location.max_capacity:
                location.bin_state = 'full'
            else:
                location.bin_state = 'available'

    @api.depends('bin_state')
    def _compute_display_color(self):
        color_map = {
            'empty': '#E8E8FF',      # Light purple
            'available': '#B3B3FF',  # Medium purple
            'full': '#6666FF',       # Dark purple
            'blocked': '#87CEEB',    # Sky blue
        }
        for location in self:
            location.display_color = color_map.get(location.bin_state, '#CCCCCC')

    def action_block_bin(self):
        """Block this bin from receiving inventory"""
        self.write({'is_blocked': True})

    def action_unblock_bin(self):
        """Unblock this bin"""
        self.write({'is_blocked': False, 'block_reason': False})

    def get_bin_details(self):
        """Return bin details for 3D visualization"""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'barcode': self.barcode,
            'state': self.bin_state,
            'color': self.display_color,
            'coordinates': {
                'x': self.coordinate_x,
                'y': self.coordinate_y,
                'z': self.coordinate_z,
            },
            'dimensions': {
                'width': self.bin_width,
                'depth': self.bin_depth,
                'height': self.bin_height,
            },
            'inventory': [{
                'product_id': quant.product_id.id,
                'product_name': quant.product_id.name,
                'product_code': quant.product_id.default_code,
                'lot_id': quant.lot_id.id if quant.lot_id else False,
                'lot_name': quant.lot_id.name if quant.lot_id else '',
                'quantity': quant.quantity,
                'reserved_quantity': quant.reserved_quantity,
                'available_quantity': quant.available_quantity,
            } for quant in self.quant_ids],
            'is_blocked': self.is_blocked,
            'block_reason': self.block_reason,
        }
