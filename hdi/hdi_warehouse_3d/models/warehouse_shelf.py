# -*- coding: utf-8 -*-
from odoo import models, fields, api

class WarehouseShelf(models.Model):
    _name = 'warehouse.shelf'
    _description = 'Warehouse Shelf (Rack)'
    _order = 'sequence, name'

    name = fields.Char(string='Shelf Name', required=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Relationships
    area_id = fields.Many2one('warehouse.area', string='Area', required=True, ondelete='cascade')
    warehouse_id = fields.Many2one('stock.warehouse', related='area_id.warehouse_id', store=True)
    
    # Physical dimensions
    width = fields.Float(string='Width (m)', default=1.2)
    depth = fields.Float(string='Depth (m)', default=1.0)
    height = fields.Float(string='Height (m)', default=2.5)
    max_weight = fields.Float(string='Max Weight (kg)', default=500)
    
    # Layout position
    position_x = fields.Float(string='Position X')
    position_y = fields.Float(string='Position Y')
    
    # Bin levels
    level_count = fields.Integer(string='Number of Levels', default=4, required=True)
    level_height = fields.Float(string='Level Height (m)', default=0.5)
    
    # Relations
    bin_ids = fields.One2many('stock.location', 'shelf_id', string='Bins', 
                              domain=[('usage', '=', 'internal')])
    bin_count = fields.Integer(string='Bin Count', compute='_compute_bin_count')
    
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')

    @api.depends('bin_ids')
    def _compute_bin_count(self):
        for shelf in self:
            shelf.bin_count = len(shelf.bin_ids)

    @api.model
    def create(self, vals):
        shelf = super(WarehouseShelf, self).create(vals)
        # Auto-create bins for levels
        if shelf.level_count > 0:
            shelf._create_bins()
        return shelf

    def _create_bins(self):
        """Auto-create stock.location bins for each level"""
        Location = self.env['stock.location']
        
        # Get warehouse location
        warehouse_location = self.area_id.warehouse_id.lot_stock_id
        
        for level in range(1, self.level_count + 1):
            for bin_num in range(1, 3):  # 2 bins per level by default
                bin_code = f"{self.code}-L{level}-B{bin_num}"
                bin_name = f"{self.name} Level {level} Bin {bin_num}"
                
                Location.create({
                    'name': bin_name,
                    'location_id': warehouse_location.id,
                    'usage': 'internal',
                    'barcode': bin_code,
                    'shelf_id': self.id,
                    'level_number': level,
                    'bin_number': bin_num,
                    'coordinate_x': self.position_x + (bin_num - 1) * 1.0,
                    'coordinate_y': self.position_y,
                    'coordinate_z': (level - 1) * self.level_height,
                })

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code, area_id)', 'Shelf code must be unique per area!')
    ]
