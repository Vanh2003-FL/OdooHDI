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
    # 3️⃣ BẮTBUỘC - Cấu trúc BIN (để generate BINs)
    # ============================================================================
    level_count = fields.Integer(string='Number of Levels', required=True, default=4,
                                help='Number of shelf levels (tầng)')
    bins_per_level = fields.Integer(string='Bins per Level', required=True, default=2,
                                   help='Number of bins per level (ô/tầng)')
    
    # ============================================================================
    # ❌ BIN Dimensions (for 3D visualization only - NOT for manual input)
    # ============================================================================
    # These are calculated from SHELF dimensions divided by grid
    level_height = fields.Float(string='Level Height (m)', compute='_compute_level_height',
                               help='🔴 Auto-calculated: depth / level_count')
    
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
    # 🔴 DEPRECATED FIELDS - Kept for backward compatibility only
    # ============================================================================
    height = fields.Float(string='Height (m) [DEPRECATED]', default=2.5, help='🔴 No longer used - use level_count instead')
    max_weight = fields.Float(string='Max Weight (kg) [DEPRECATED]', default=500, help='🔴 No longer used')
    orientation = fields.Selection([('horizontal', 'Horizontal'), ('vertical', 'Vertical')],
                                  string='Orientation [DEPRECATED]', default='horizontal', help='🔴 No longer used')
    notes = fields.Text(string='Notes')

    # ============================================================================
    # Computed Fields
    # ============================================================================
    @api.depends('depth', 'level_count')
    def _compute_level_height(self):
        """Auto-calculate level height: depth / level_count"""
        for shelf in self:
            if shelf.level_count > 0:
                shelf.level_height = shelf.depth / shelf.level_count
            else:
                shelf.level_height = 0.0
    
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
    # BIN Generation
    # ============================================================================
    @api.model
    def create(self, vals):
        """Create shelf and auto-generate BINs"""
        shelf = super(WarehouseShelf, self).create(vals)
        # Auto-create bins for the shelf's grid
        if shelf.level_count > 0 and shelf.bins_per_level > 0:
            shelf._create_bins()
        return shelf

    def write(self, vals):
        """Regenerate bins if level_count or bins_per_level changes"""
        result = super(WarehouseShelf, self).write(vals)
        
        # Regenerate bins if grid configuration changed
        if 'level_count' in vals or 'bins_per_level' in vals:
            for shelf in self:
                # Delete old bins first
                old_bins = self.env['stock.location'].search([
                    ('location_id', '=', shelf.id),
                    ('location_type', '=', 'bin')
                ])
                old_bins.unlink()
                # Create new bins with updated grid
                shelf._create_bins()
        
        return result

    def _create_bins(self):
        """Generate BIN grid from SHELF configuration
        
        BINs created per SKUSavvy spec:
        - Grid: level_count (height) × bins_per_level (width)
        - Each BIN:
          - location_type = 'bin'
          - location_id = shelf (parent)
          - bin_level = 1 to level_count
          - bin_col = 1 to bins_per_level
          - bin_row = 0 (not used in this grid)
          - bin_width = width / bins_per_level
          - bin_depth = level_height (calculated)
          - bin_height = level_height (calculated)
          - pos_x, pos_y auto-calculated based on position
        """
        Location = self.env['stock.location']
        
        bin_width = self.width / self.bins_per_level if self.bins_per_level > 0 else 0.5
        bin_depth = self.level_height if self.level_height > 0 else 0.5
        
        total_bins_created = 0
        
        for level in range(1, self.level_count + 1):
            for col in range(1, self.bins_per_level + 1):
                # Calculate position
                pos_x = self.position_x + ((col - 1) * bin_width)
                pos_y = self.position_y + ((level - 1) * bin_depth)
                
                # Create BIN
                bin_name = f"{self.code}-L{level}-C{col}"
                
                try:
                    Location.create({
                        'name': bin_name,
                        'location_id': self.id,  # Parent SHELF
                        'location_type': 'bin',
                        'usage': 'internal',  # BINs hold inventory
                        'bin_level': level,
                        'bin_row': 0,
                        'bin_col': col,
                        'pos_x': pos_x,
                        'pos_y': pos_y,
                        'bin_width': bin_width,
                        'bin_depth': bin_depth,
                        'bin_height': bin_depth,  # Use level_height for height
                        'max_capacity': 100.0,  # Default capacity
                        'max_weight': 50.0,  # Default max weight
                    })
                    total_bins_created += 1
                except Exception as e:
                    self.env.cr.rollback()
                    raise ValidationError(f"Failed to create BIN {bin_name}: {str(e)}")
        
        return total_bins_created

    def unlink(self):
        """🔴 CRITICAL: Prevent deleting SHELF if it has BINs with inventory"""
        for shelf in self:
            # Find all BINs that belong to this SHELF
            bins = self.env['stock.location'].search([
                ('location_id', '=', shelf.id),
                ('location_type', '=', 'bin')
            ])
            
            if bins:
                # Check if any BIN has inventory
                quants = self.env['stock.quant'].search([
                    ('location_id', 'in', bins.ids),
                    ('quantity', '>', 0)
                ])
                
                if quants:
                    bin_names = ', '.join(bins.mapped('name'))
                    raise ValidationError(
                        f"🚫 CANNOT DELETE SHELF '{shelf.name}'!\n\n"
                        f"This shelf has {len(quants)} units of inventory in bins:\n{bin_names}\n\n"
                        f"✅ You can:\n"
                        f"  1. Move all inventory OUT of these bins first\n"
                        f"  2. Then delete the shelf\n\n"
                        f"Or, delete individual empty bins from Bins list."
                    )
        
        return super(WarehouseShelf, self).unlink()

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code, warehouse_id)', 'Shelf code must be unique per warehouse!')
    ]
