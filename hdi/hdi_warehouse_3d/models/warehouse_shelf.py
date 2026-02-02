# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class WarehouseShelf(models.Model):
    _name = 'warehouse.shelf'
    _description = 'Warehouse Shelf (Rack) - Physical Container'
    _order = 'sequence, name'

    # ============================================================================
    # 1️⃣ BẮTBUỘC - Thông tin cơ bản
    # ============================================================================
    name = fields.Char(string='Shelf Name', required=True)
    code = fields.Char(string='Shelf Code', required=True)
    
    area_id = fields.Many2one('warehouse.area', string='Parent Area', required=True, ondelete='cascade',
                             help='Select the area (zone) where this shelf is located')
    
    # Usage = view (shelves do NOT hold inventory directly, BINs do)
    usage = fields.Selection([('view', 'View')], default='view', required=True, readonly=True,
                            help='Shelves are view-only locations. Inventory goes in BINs.')
    
    # Shelf Type - for categorization
    shelf_type = fields.Selection([
        ('selective', 'Selective'),
        ('pallet', 'Pallet'),
        ('flow', 'Flow'),
    ], string='Shelf Type', required=True, default='selective',
       help='Type of shelving: Selective (standard), Pallet (heavy), Flow (dynamic)')
    
    # ============================================================================
    # 2️⃣ BẮT BUỘC - Layout 2D
    # ============================================================================
    position_x = fields.Float(string='Position X (m)', required=True, default=0.0,
                             help='X coordinate in warehouse')
    position_y = fields.Float(string='Position Y (m)', required=True, default=0.0,
                             help='Y coordinate in warehouse')
    
    width = fields.Float(string='Length (m)', required=True, default=1.2,
                        help='Length of shelf (X dimension)')
    depth = fields.Float(string='Depth (m)', required=True, default=1.0,
                        help='Depth of shelf (Y dimension)')
    
    rotation = fields.Float(string='Rotation (degrees)', default=0.0,
                           help='Rotation angle: 0 or 90 degrees')
    
    # ============================================================================
    # Relationships
    # ============================================================================
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True,
                                  compute='_compute_warehouse_id', store=True, readonly=True)
    
    # ============================================================================
    # Status
    # ============================================================================
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
    
    # ============================================================================
    # 🔴 DEPRECATED FIELDS - Kept for backward compatibility
    # (Not used in SKUSavvy but kept to avoid DB errors)
    # ============================================================================
    height = fields.Float(string='Height (m) [DEPRECATED]', default=2.5, help='🔴 No longer used')
    max_weight = fields.Float(string='Max Weight (kg) [DEPRECATED]', default=500, help='🔴 No longer used')
    level_count = fields.Integer(string='Number of Levels [DEPRECATED]', default=4, help='🔴 No longer used')
    level_height = fields.Float(string='Level Height (m) [DEPRECATED]', default=0.5, help='🔴 No longer used')
    bins_per_level = fields.Integer(string='Bins per Level [DEPRECATED]', default=2, help='🔴 No longer used')
    orientation = fields.Selection([('horizontal', 'Horizontal'), ('vertical', 'Vertical')],
                                  string='Orientation [DEPRECATED]', default='horizontal', help='🔴 No longer used')
    notes = fields.Text(string='Notes')

    # ============================================================================
    # Computed Fields
    # ============================================================================
    @api.depends('area_id.warehouse_id')
    def _compute_warehouse_id(self):
        """Get warehouse from parent area"""
        for shelf in self:
            shelf.warehouse_id = shelf.area_id.warehouse_id if shelf.area_id else False

    @api.constrains('shelf_type')
    def _check_shelf_type(self):
        """Validate shelf type"""
        for shelf in self:
            if shelf.shelf_type not in ['selective', 'pallet', 'flow']:
                raise ValidationError("Invalid shelf type. Must be Selective, Pallet, or Flow.")

    # ============================================================================
    # Deprecated Methods (kept for backward compatibility)
    # ============================================================================
    def _create_bins(self):
        """🔴 DEPRECATED - Use stock.location with location_type='bin' instead"""
        pass

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code, warehouse_id)', 'Shelf code must be unique per warehouse!')
    ]
