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
    area_id = fields.Many2one('warehouse.area', string='Area', required=False, ondelete='set null',
                             help='Optional: Visual grouping only. Shelves are independent entities.')
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
        """Auto-create stock.location bins for each level using grid division"""
        Location = self.env['stock.location']
        
        # Get warehouse location (try area first, fallback to warehouse)
        if self.area_id and self.area_id.warehouse_id:
            warehouse_location = self.area_id.warehouse_id.lot_stock_id
        elif self.warehouse_id:
            warehouse_location = self.warehouse_id.lot_stock_id
        else:
            # Fallback to first available warehouse
            warehouse = self.env['stock.warehouse'].search([], limit=1)
            warehouse_location = warehouse.lot_stock_id if warehouse else False
            
        if not warehouse_location:
            return
        
        # Calculate bin dimensions based on shelf division
        bin_width = self.width / self.bins_per_level
        
        for level in range(1, self.level_count + 1):
            for bin_num in range(1, self.bins_per_level + 1):
                bin_code = f"{self.code}-L{level:02d}-B{bin_num:02d}"
                bin_name = f"{self.name} Level {level} Bin {bin_num}"
                
                # Calculate position based on orientation
                if self.orientation == 'horizontal':
                    bin_x = self.position_x + (bin_num - 1) * bin_width
                    bin_y = self.position_y
                else:  # vertical
                    bin_x = self.position_x
                    bin_y = self.position_y + (bin_num - 1) * bin_width
                
                Location.create({
                    'name': bin_name,
                    'location_id': warehouse_location.id,
                    'usage': 'internal',
                    'barcode': bin_code,
                    'shelf_id': self.id,
                    'area_id': self.area_id.id if self.area_id else False,
                    'level_number': level,
                    'bin_number': bin_num,
                    'coordinate_x': bin_x,
                    'coordinate_y': bin_y,
                    'coordinate_z': (level - 1) * self.level_height,
                    'bin_width': bin_width,
                    'bin_depth': self.depth,
                    'bin_height': self.level_height,
                })

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code, area_id)', 'Shelf code must be unique per area!')
    ]
