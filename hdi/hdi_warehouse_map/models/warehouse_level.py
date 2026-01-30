# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class WarehouseLevel(models.Model):
    _name = 'warehouse.level'
    _description = 'Warehouse Level (Shelf)'
    _order = 'rack_id, level_number'

    name = fields.Char(string='Level Name', required=True, index=True)
    code = fields.Char(string='Level Code', required=True, index=True)
    level_number = fields.Integer(string='Level Number', required=True, help='1 = ground level, 2 = first shelf, etc.')
    active = fields.Boolean(string='Active', default=True)
    
    rack_id = fields.Many2one('warehouse.rack', string='Rack', required=True, ondelete='cascade', index=True)
    aisle_id = fields.Many2one('warehouse.aisle', related='rack_id.aisle_id', string='Aisle', store=True, index=True)
    zone_id = fields.Many2one('warehouse.zone', related='rack_id.zone_id', string='Zone', store=True, index=True)
    warehouse_id = fields.Many2one('stock.warehouse', related='rack_id.warehouse_id', string='Warehouse', store=True, index=True)
    
    # Structure
    bin_ids = fields.One2many('warehouse.bin', 'level_id', string='Bins')
    bin_count = fields.Integer(string='Bin Count', compute='_compute_bin_count', store=True)
    
    # Physical Dimensions
    height_from_ground = fields.Float(string='Height from Ground (m)', compute='_compute_height', store=True)
    shelf_height = fields.Float(string='Shelf Height (m)', default=0.4)
    max_weight_per_bin = fields.Float(string='Max Weight per Bin (kg)')
    
    # Capacity
    total_capacity = fields.Float(string='Total Capacity (m³)', compute='_compute_capacity', store=True)
    used_capacity = fields.Float(string='Used Capacity (m³)', compute='_compute_capacity')
    capacity_utilization = fields.Float(string='Utilization (%)', compute='_compute_capacity')
    
    description = fields.Text(string='Description')
    
    _sql_constraints = [
        ('code_unique', 'unique(code, rack_id)', 'Level code must be unique per rack!'),
        ('level_number_unique', 'unique(level_number, rack_id)', 'Level number must be unique per rack!'),
        ('level_number_positive', 'check(level_number > 0)', 'Level number must be positive!'),
    ]
    
    @api.depends('level_number', 'shelf_height')
    def _compute_height(self):
        for level in self:
            # Level 1 is at 0m, Level 2 at shelf_height, etc.
            level.height_from_ground = (level.level_number - 1) * level.shelf_height
    
    @api.depends('bin_ids')
    def _compute_bin_count(self):
        for level in self:
            level.bin_count = len(level.bin_ids)
    
    @api.depends('bin_ids.capacity', 'bin_ids.used_capacity')
    def _compute_capacity(self):
        for level in self:
            level.total_capacity = sum(level.bin_ids.mapped('capacity'))
            level.used_capacity = sum(level.bin_ids.mapped('used_capacity'))
            level.capacity_utilization = (level.used_capacity / level.total_capacity * 100) if level.total_capacity else 0
    
    def name_get(self):
        result = []
        for level in self:
            name = f'[{level.zone_id.code}/{level.aisle_id.code}/{level.rack_id.code}/L{level.level_number}] {level.name}'
            result.append((level.id, name))
        return result
