# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class StockLocation(models.Model):
    _inherit = 'stock.location'

    # 🟦 SKUSavvy Hierarchy: AREA → SHELF → BIN
    # Type of location in warehouse hierarchy
    location_type = fields.Selection([
        ('area', 'Area (Zone)'),
        ('shelf', 'Shelf (Rack)'),
        ('bin', 'Bin (Slot/Cell)'),
    ], string='Location Type', default='bin', index=True, required=True,
       help='AREA=zone marker, SHELF=container with grid, BIN=location where goods stored')
    
    # Parent relationship (enforces hierarchy)
    parent_warehouse_id = fields.Many2one(
        'stock.warehouse', 
        string='Warehouse',
        help='Warehouse this location belongs to'
    )
    
    # 2D Layout Properties (for both AREA and SHELF)
    pos_x = fields.Float(string='X Position', default=0)
    pos_y = fields.Float(string='Y Position', default=0)
    width = fields.Float(string='Width (m)', default=1.0)
    height = fields.Float(string='Height (m)', default=1.0)
    rotation = fields.Float(string='Rotation (degrees)', default=0.0)
    color = fields.Char(string='Display Color', default='#E8E8FF')
    
    # Grid Configuration (for SHELF only)
    # Defines how shelf is divided into bins
    rows = fields.Integer(string='Rows (Y divisions)', default=2, help='Number of bins vertically')
    cols = fields.Integer(string='Columns (X divisions)', default=2, help='Number of bins horizontally')
    levels = fields.Integer(string='Levels (Z divisions)', default=4, help='Number of shelf levels')
    
    # Grid Cell Properties (for BIN only)
    # Position in the parent shelf's grid
    bin_row = fields.Integer(string='Bin Row', help='Row position in parent shelf grid')
    bin_col = fields.Integer(string='Bin Column', help='Column position in parent shelf grid')
    bin_level = fields.Integer(string='Bin Level', help='Level in parent shelf (1=bottom)')
    
    # Physical dimensions
    bin_width = fields.Float(string='Bin Width (m)', default=1.0)
    bin_depth = fields.Float(string='Bin Depth (m)', default=0.8)
    bin_height = fields.Float(string='Bin Height (m)', default=0.5)
    max_capacity = fields.Float(string='Max Capacity', default=50)
    max_weight = fields.Float(string='Max Weight (kg)', default=100)
    
    # Visual & State Properties
    display_color_code = fields.Char(string='Color Code', compute='_compute_display_color')
    bin_state = fields.Selection([
        ('empty', 'Empty'),
        ('available', 'Available'),
        ('full', 'Full'),
        ('blocked', 'Blocked')
    ], string='Bin State', compute='_compute_bin_state')
    
    # Blocking & Lock Status (BIN only)
    is_blocked = fields.Boolean(string='Blocked', default=False)
    block_reason = fields.Text(string='Block Reason')
    is_locked = fields.Boolean(string='Locked (has inventory)', compute='_compute_is_locked', store=True,
                               help='Bin is locked if it has stock.quant (inventory) assigned')

    # ============================================================================
    # HIERARCHY ENFORCEMENT
    # ============================================================================
    
    @api.constrains('location_type', 'usage')
    def _check_location_type_usage(self):
        """Enforce mapping: AREA/SHELF=view, BIN=internal"""
        for location in self:
            if location.location_type in ('area', 'shelf') and location.usage != 'view':
                raise ValidationError(f"{location.location_type.upper()} must have usage='view'")
            if location.location_type == 'bin' and location.usage != 'internal':
                raise ValidationError("BIN must have usage='internal' (to hold inventory)")

    @api.constrains('location_type', 'pos_x', 'pos_y', 'location_id')
    def _check_bin_position_within_shelf(self):
        """🟦 SKUSavvy Rule: BIN position must be within parent SHELF boundaries"""
        for location in self:
            if location.location_type != 'bin':
                continue
                
            # BIN must have parent SHELF
            if not location.location_id:
                raise ValidationError(
                    "🚫 BIN must have a parent SHELF!\n\n"
                    "Cannot create standalone bin. Bin must be placed inside a SHELF.\n"
                    "Each bin belongs to exactly one shelf in the warehouse hierarchy."
                )
            
            parent = location.location_id
            if parent.location_type != 'shelf':
                raise ValidationError(
                    f"🚫 BIN parent must be a SHELF, not {parent.location_type.upper()}!\n\n"
                    "Hierarchy: WAREHOUSE → AREA → SHELF → BIN\n"
                    f"'{parent.name}' is {parent.location_type}, cannot contain bins."
                )
            
            # Check if BIN position is within SHELF boundaries
            # SHELF bounds: [pos_x, pos_x + width] × [pos_y, pos_y + height]
            shelf = parent
            bin_pos_x = location.pos_x
            bin_pos_y = location.pos_y
            bin_width = location.bin_width or 0.5
            bin_height = location.bin_depth or 0.5
            
            shelf_x_min = shelf.pos_x
            shelf_x_max = shelf.pos_x + shelf.width
            shelf_y_min = shelf.pos_y
            shelf_y_max = shelf.pos_y + shelf.height
            
            # Check if BIN bounds fit inside SHELF bounds
            if not (bin_pos_x >= shelf_x_min and (bin_pos_x + bin_width) <= shelf_x_max):
                raise ValidationError(
                    f"❌ BIN X position out of bounds!\n\n"
                    f"SHELF '{shelf.name}' X range: {shelf_x_min} to {shelf_x_max}m\n"
                    f"BIN X range: {bin_pos_x} to {bin_pos_x + bin_width}m\n\n"
                    f"BIN must fit completely within SHELF boundaries."
                )
            
            if not (bin_pos_y >= shelf_y_min and (bin_pos_y + bin_height) <= shelf_y_max):
                raise ValidationError(
                    f"❌ BIN Y position out of bounds!\n\n"
                    f"SHELF '{shelf.name}' Y range: {shelf_y_min} to {shelf_y_max}m\n"
                    f"BIN Y range: {bin_pos_y} to {bin_pos_y + bin_height}m\n\n"
                    f"BIN must fit completely within SHELF boundaries."
                )

    # ============================================================================
    # COMPUTED FIELDS
    # ============================================================================

    @api.depends('quant_ids', 'quant_ids.quantity')
    def _compute_is_locked(self):
        """A BIN is locked if it has inventory (stock.quant)"""
        for location in self:
            # Only BINs (usage=internal) can be locked
            has_inventory = location.usage == 'internal' and location.quant_ids and any(
                q.quantity > 0 for q in location.quant_ids
            )
            location.is_locked = has_inventory

    @api.depends('quant_ids', 'quant_ids.quantity', 'is_blocked')
    def _compute_bin_state(self):
        """Compute BIN state: empty/available/full/blocked"""
        for location in self:
            if location.location_type != 'bin':
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
        """Map BIN state to display color"""
        color_map = {
            'empty': '#E8E8FF',      # Light purple - DRAFT, no inventory
            'available': '#B3B3FF',  # Medium purple - has inventory, LOCKED
            'full': '#6666FF',       # Dark purple - full, LOCKED
            'blocked': '#FF9999',    # Light red - blocked
        }
        for location in self:
            if location.location_type == 'area':
                location.display_color_code = location.color or '#E8E8FF'
            elif location.location_type == 'shelf':
                location.display_color_code = location.color or '#D4D4FF'
            else:  # BIN
                location.display_color_code = color_map.get(location.bin_state, '#CCCCCC')

    # ============================================================================
    # CREATE / WRITE OVERRIDES
    # ============================================================================

    @api.model
    def create(self, vals):
        """Create new location (AREA/SHELF/BIN)"""
        # Set usage based on location_type
        location_type = vals.get('location_type', 'bin')
        if location_type in ('area', 'shelf'):
            vals['usage'] = 'view'
        else:  # bin
            vals['usage'] = 'internal'
        
        location = super(StockLocation, self).create(vals)
        
        # For BINs: auto-generate code if not provided
        if location.location_type == 'bin' and not location.name:
            location.name = f"{location.location_id.name or 'SHELF'}-R{location.bin_row or 1}-C{location.bin_col or 1}-L{location.bin_level or 1}"
        
        return location

    def write(self, vals):
        """Prevent moving/resizing BINs that have inventory (locked)"""
        # For locked BINs: only allow block/unblock
        if self.filtered('is_locked'):
            allowed_fields = {'is_blocked', 'block_reason'}
            modifying_fields = set(vals.keys()) - allowed_fields
            
            if modifying_fields:
                locked_bins = self.filtered(lambda l: l.location_type == 'bin' and l.is_locked)
                if locked_bins:
                    raise ValidationError(
                        f"❌ Cannot modify LOCKED BINs!\n\n"
                        f"BINs: {', '.join(locked_bins.mapped('name'))}\n\n"
                        f"These bins have inventory and are LOCKED.\n"
                        f"✅ Allowed: Block/Unblock\n"
                        f"❌ Not Allowed: Move, Resize, Delete, Config\n\n"
                        f"To restructure: Remove all stock.quant first"
                    )
        
        return super(StockLocation, self).write(vals)

    def action_block_bin(self):
        """Block BIN from receiving inventory"""
        self.filtered(lambda l: l.location_type == 'bin').write({'is_blocked': True})

    def action_unblock_bin(self):
        """Unblock BIN"""
        self.filtered(lambda l: l.location_type == 'bin').write({'is_blocked': False, 'block_reason': False})

    def get_bin_details(self):
        """Return BIN details for 3D visualization"""
        self.ensure_one()
        if self.location_type != 'bin':
            raise ValidationError("Only BINs have details")
        
        return {
            'id': self.id,
            'name': self.name,
            'code': self.name,
            'state': self.bin_state,
            'color': self.display_color,
            'grid': {
                'row': self.bin_row,
                'col': self.bin_col,
                'level': self.bin_level,
            },
            'dimensions': {
                'width': self.bin_width,
                'depth': self.bin_depth,
                'height': self.bin_height,
            },
            'inventory': [{
                'product_id': q.product_id.id,
                'product_name': q.product_id.name,
                'lot_id': q.lot_id.id if q.lot_id else False,
                'quantity': q.quantity,
            } for q in self.quant_ids if q.quantity > 0],
            'is_blocked': self.is_blocked,
            'is_locked': self.is_locked,
        }