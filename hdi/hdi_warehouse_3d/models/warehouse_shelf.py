# -*- coding: utf-8 -*-
from odoo import models, fields, api

class WarehouseShelf(models.Model):
    _name = 'warehouse.shelf'
    _description = 'Warehouse Shelf (Rack)'
    _order = 'sequence, name'

    name = fields.Char(string='Shelf Name', required=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Relationships (SKUsavvy: area_id is optional - shelves can be placed freely)
    # Area = zoning for cashier/checkout/office, NOT for containing shelves
    area_id = fields.Many2one('warehouse.area', string='Area', required=False, ondelete='set null',
                             help='Optional: For visual reference only. Areas mark zones like cashier, checkout, office. Shelves are independent.')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    
    # Physical dimensions
    width = fields.Float(string='Width (m)', default=1.2)
    depth = fields.Float(string='Depth (m)', default=1.0)
    height = fields.Float(string='Height (m)', default=2.5)
    max_weight = fields.Float(string='Max Weight (kg)', default=500)
    
    # Layout position
    position_x = fields.Float(string='Position X')
    position_y = fields.Float(string='Position Y')
    orientation = fields.Selection([
        ('horizontal', 'Horizontal'),
        ('vertical', 'Vertical'),
    ], string='Orientation', default='horizontal', required=True,
       help='Shelf orientation for 2D layout design')
    rotation = fields.Float(string='Rotation (degrees)', default=0.0,
                           help='Rotation angle for shelf placement')
    
    # Bin levels and grid
    level_count = fields.Integer(string='Number of Levels', default=4, required=True)
    level_height = fields.Float(string='Level Height (m)', default=0.5)
    bins_per_level = fields.Integer(string='Bins per Level', default=2, required=True,
                                    help='Number of bins per level (horizontal divisions)')
    
    # 🔴 DEPRECATED: bin_ids removed - now using stock.location with location_type='bin'
    # Kept for backward compatibility, but not used in new SKUSavvy implementation
    
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')

    @api.model
    def create(self, vals):
        shelf = super(WarehouseShelf, self).create(vals)
        # Auto-create bins for levels
        if shelf.level_count > 0:
            shelf._create_bins()
        return shelf

    def write(self, vals):
        """Override write to regenerate bins if configuration changes"""
        result = super(WarehouseShelf, self).write(vals)
        
        # Regenerate bins if level_count or bins_per_level changed
        if 'level_count' in vals or 'bins_per_level' in vals:
            for shelf in self:
                shelf._create_bins()
        
        return result

    def action_regenerate_bins(self):
        """Manual action to regenerate all bins for this shelf"""
        for shelf in self:
            shelf._create_bins()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Regenerated {self.bin_count} bins successfully!',
                'type': 'success',
                'sticky': False,
            }
        }

    def _create_bins(self):
        """🔴 DEPRECATED - Create bins via stock.location directly with location_type='bin'"""
        # Kept for backward compatibility only
        pass

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code, warehouse_id)', 'Shelf code must be unique per warehouse!')
    ]
