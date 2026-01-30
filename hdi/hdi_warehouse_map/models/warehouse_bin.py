# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class WarehouseBin(models.Model):
    _name = 'warehouse.bin'
    _description = 'Warehouse Bin (Storage Location)'
    _order = 'level_id, bin_number'
    _rec_name = 'complete_name'

    name = fields.Char(string='Bin Name', required=True, index=True)
    code = fields.Char(string='Bin Code', required=True, index=True)
    complete_name = fields.Char(string='Complete Name', compute='_compute_complete_name', store=True, index=True)
    bin_number = fields.Integer(string='Bin Number', required=True)
    active = fields.Boolean(string='Active', default=True)
    
    # FR-2: Mỗi Bin tương ứng duy nhất với một stock.location
    location_id = fields.Many2one('stock.location', string='Stock Location', required=True, 
                                   ondelete='restrict', index=True)
    
    level_id = fields.Many2one('warehouse.level', string='Level', required=True, ondelete='cascade', index=True)
    rack_id = fields.Many2one('warehouse.rack', related='level_id.rack_id', string='Rack', store=True, index=True)
    aisle_id = fields.Many2one('warehouse.aisle', related='level_id.aisle_id', string='Aisle', store=True, index=True)
    zone_id = fields.Many2one('warehouse.zone', related='level_id.zone_id', string='Zone', store=True, index=True)
    warehouse_id = fields.Many2one('stock.warehouse', related='level_id.warehouse_id', string='Warehouse', store=True, index=True)
    
    # FR-3: Tọa độ không gian
    coordinate_x = fields.Float(string='Coordinate X', required=True)
    coordinate_y = fields.Float(string='Coordinate Y', required=True)
    coordinate_z = fields.Float(string='Coordinate Z', compute='_compute_coordinate_z', store=True)
    
    # Physical Dimensions
    width = fields.Float(string='Width (m)', default=0.4)
    depth = fields.Float(string='Depth (m)', default=0.4)
    height = fields.Float(string='Height (m)', default=0.4)
    capacity = fields.Float(string='Capacity (m³)', compute='_compute_capacity', store=True)
    max_weight = fields.Float(string='Max Weight (kg)', default=100)
    
    # FR-15, FR-16: Block Bin
    is_blocked = fields.Boolean(string='Blocked', default=False, tracking=True)
    block_reason = fields.Text(string='Block Reason')
    blocked_date = fields.Datetime(string='Blocked Date')
    blocked_by = fields.Many2one('res.users', string='Blocked By')
    
    # Status & Content
    state = fields.Selection([
        ('empty', 'Empty'),
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('full', 'Full'),
        ('blocked', 'Blocked'),
    ], string='Status', compute='_compute_state', store=True)
    
    # FR-4: SKU constraint
    current_product_id = fields.Many2one('product.product', string='Current Product', 
                                          compute='_compute_current_content', store=True)
    current_sku = fields.Char(string='Current SKU', related='current_product_id.default_code', store=True)
    
    # FR-5: Lot constraint (optional)
    enforce_single_lot = fields.Boolean(string='Enforce Single Lot', default=False,
                                         help='Nếu bật, Bin này chỉ chứa một Lot tại một thời điểm')
    current_lot_id = fields.Many2one('stock.lot', string='Current Lot', 
                                      compute='_compute_current_content', store=True)
    
    # Quant information
    quant_ids = fields.One2many('stock.quant', 'bin_id', string='Quants')
    total_quantity = fields.Float(string='Total Quantity', compute='_compute_current_content', store=True)
    used_capacity = fields.Float(string='Used Capacity (m³)', compute='_compute_current_content', store=True)
    capacity_utilization = fields.Float(string='Utilization (%)', compute='_compute_current_content', store=True)
    
    # Visualization - FR-13: Màu sắc thể hiện trạng thái
    display_color = fields.Char(string='Display Color', compute='_compute_display_color')
    
    # History tracking
    last_movement_date = fields.Datetime(string='Last Movement Date')
    history_ids = fields.One2many('bin.history', 'bin_id', string='Movement History')
    
    description = fields.Text(string='Description')
    
    _sql_constraints = [
        ('code_unique', 'unique(code, level_id)', 'Bin code must be unique per level!'),
        ('location_unique', 'unique(location_id)', 'Each Bin must have a unique stock location!'),
        ('bin_number_unique', 'unique(bin_number, level_id)', 'Bin number must be unique per level!'),
        ('dimensions_positive', 'check(width > 0 AND depth > 0 AND height > 0)', 
         'Dimensions must be positive!'),
    ]
    
    @api.depends('zone_id.code', 'aisle_id.code', 'rack_id.code', 'level_id.level_number', 'code')
    def _compute_complete_name(self):
        for bin in self:
            if bin.zone_id and bin.aisle_id and bin.rack_id and bin.level_id:
                bin.complete_name = f'{bin.zone_id.code}-{bin.aisle_id.code}-{bin.rack_id.code}-L{bin.level_id.level_number}-{bin.code}'
            else:
                bin.complete_name = bin.name or ''
    
    @api.depends('level_id.height_from_ground', 'bin_number', 'height')
    def _compute_coordinate_z(self):
        for bin in self:
            bin.coordinate_z = bin.level_id.height_from_ground if bin.level_id else 0
    
    @api.depends('width', 'depth', 'height')
    def _compute_capacity(self):
        for bin in self:
            bin.capacity = bin.width * bin.depth * bin.height
    
    @api.depends('quant_ids', 'quant_ids.quantity', 'quant_ids.product_id', 'quant_ids.lot_id', 'is_blocked')
    def _compute_current_content(self):
        for bin in self:
            quants = bin.quant_ids.filtered(lambda q: q.quantity > 0)
            
            if quants:
                # Get unique products
                products = quants.mapped('product_id')
                bin.current_product_id = products[0] if len(products) == 1 else False
                
                # Get unique lots
                lots = quants.mapped('lot_id').filtered(lambda l: l)
                bin.current_lot_id = lots[0] if len(lots) == 1 else False
                
                bin.total_quantity = sum(quants.mapped('quantity'))
                
                # Estimate used capacity (simplified)
                if bin.current_product_id and bin.current_product_id.volume:
                    bin.used_capacity = bin.total_quantity * bin.current_product_id.volume
                else:
                    bin.used_capacity = 0
            else:
                bin.current_product_id = False
                bin.current_lot_id = False
                bin.total_quantity = 0
                bin.used_capacity = 0
            
            bin.capacity_utilization = (bin.used_capacity / bin.capacity * 100) if bin.capacity else 0
    
    @api.depends('is_blocked', 'total_quantity', 'capacity_utilization')
    def _compute_state(self):
        for bin in self:
            if bin.is_blocked:
                bin.state = 'blocked'
            elif bin.total_quantity == 0:
                bin.state = 'empty'
            elif bin.capacity_utilization >= 95:
                bin.state = 'full'
            elif bin.capacity_utilization > 0:
                bin.state = 'available'
            else:
                bin.state = 'empty'
    
    @api.depends('state')
    def _compute_display_color(self):
        color_map = {
            'empty': '#95a5a6',      # Gray
            'available': '#2ecc71',   # Green
            'reserved': '#f39c12',    # Orange
            'full': '#e74c3c',        # Red
            'blocked': '#34495e',     # Dark gray
        }
        for bin in self:
            bin.display_color = color_map.get(bin.state, '#bdc3c7')
    
    def action_block_bin(self):
        """FR-15: Block Bin"""
        self.ensure_one()
        return {
            'name': _('Block Bin'),
            'type': 'ir.actions.act_window',
            'res_model': 'bin.block.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_bin_id': self.id,
                'default_action': 'block',
            }
        }
    
    def action_unblock_bin(self):
        """FR-15: Unblock Bin"""
        self.ensure_one()
        self.write({
            'is_blocked': False,
            'block_reason': False,
            'blocked_date': False,
            'blocked_by': False,
        })
        return True
    
    def action_view_history(self):
        """FR-18: Xem lịch sử di chuyển theo Bin"""
        self.ensure_one()
        return {
            'name': _('Bin Movement History'),
            'type': 'ir.actions.act_window',
            'res_model': 'bin.history',
            'view_mode': 'tree,form',
            'domain': [('bin_id', '=', self.id)],
            'context': {'default_bin_id': self.id}
        }
    
    def action_view_quants(self):
        """FR-14: Click Bin để xem SKU, Lot, số lượng"""
        self.ensure_one()
        return {
            'name': _('Bin Content'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant',
            'view_mode': 'tree,form',
            'domain': [('location_id', '=', self.location_id.id)],
            'context': {'default_location_id': self.location_id.id}
        }
    
    # FR-4, FR-5, FR-6: Validation constraints
    @api.constrains('quant_ids')
    def _check_sku_constraint(self):
        """FR-4: Một Bin chỉ được chứa một SKU tại một thời điểm"""
        for bin in self:
            products = bin.quant_ids.filtered(lambda q: q.quantity > 0).mapped('product_id')
            if len(products) > 1:
                raise ValidationError(_(
                    'Bin %s can only contain one SKU at a time!\n'
                    'Current products: %s'
                ) % (bin.complete_name, ', '.join(products.mapped('display_name'))))
    
    @api.constrains('quant_ids', 'enforce_single_lot')
    def _check_lot_constraint(self):
        """FR-5: Cấu hình tùy chọn: một Bin chỉ chứa một Lot"""
        for bin in self:
            if bin.enforce_single_lot:
                lots = bin.quant_ids.filtered(lambda q: q.quantity > 0 and q.lot_id).mapped('lot_id')
                if len(lots) > 1:
                    raise ValidationError(_(
                        'Bin %s is configured to contain only one Lot at a time!\n'
                        'Current lots: %s'
                    ) % (bin.complete_name, ', '.join(lots.mapped('name'))))
    
    def name_get(self):
        result = []
        for bin in self:
            result.append((bin.id, bin.complete_name or bin.name))
        return result
    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            args = ['|', '|', ('name', operator, name), ('code', operator, name), ('complete_name', operator, name)] + args
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)
