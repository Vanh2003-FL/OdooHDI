# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class WarehouseRack(models.Model):
    _name = 'warehouse.rack'
    _description = 'Warehouse Rack'
    _order = 'aisle_id, sequence, name'

    name = fields.Char(string='Rack Name', required=True, index=True)
    code = fields.Char(string='Rack Code', required=True, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    aisle_id = fields.Many2one('warehouse.aisle', string='Aisle', required=True, ondelete='cascade', index=True)
    zone_id = fields.Many2one('warehouse.zone', related='aisle_id.zone_id', string='Zone', store=True, index=True)
    warehouse_id = fields.Many2one('stock.warehouse', related='aisle_id.warehouse_id', string='Warehouse', store=True, index=True)
    
    # Structure
    level_ids = fields.One2many('warehouse.level', 'rack_id', string='Levels')
    level_count = fields.Integer(string='Level Count', compute='_compute_level_count', store=True)
    
    # Physical Dimensions
    width = fields.Float(string='Width (m)', required=True, default=1.2)
    depth = fields.Float(string='Depth (m)', required=True, default=0.8)
    height = fields.Float(string='Height (m)', required=True, default=4.0)
    
    # Capacity
    max_weight = fields.Float(string='Max Weight (kg)', help='Maximum weight capacity per rack')
    total_capacity = fields.Float(string='Total Capacity (m³)', compute='_compute_capacity', store=True)
    used_capacity = fields.Float(string='Used Capacity (m³)', compute='_compute_capacity')
    capacity_utilization = fields.Float(string='Utilization (%)', compute='_compute_capacity')
    
    # Visualization
    position_x = fields.Float(string='Position X')
    position_y = fields.Float(string='Position Y')
    position_z = fields.Float(string='Position Z', default=0)
    
    description = fields.Text(string='Description')
    
    _sql_constraints = [
        ('code_unique', 'unique(code, aisle_id)', 'Rack code must be unique per aisle!'),
        ('dimensions_positive', 'check(width > 0 AND depth > 0 AND height > 0)', 
         'Dimensions must be positive!'),
    ]
    
    @api.depends('level_ids')
    def _compute_level_count(self):
        for rack in self:
            rack.level_count = len(rack.level_ids)
    
    @api.depends('level_ids.total_capacity', 'level_ids.used_capacity')
    def _compute_capacity(self):
        for rack in self:
            rack.total_capacity = sum(rack.level_ids.mapped('total_capacity'))
            rack.used_capacity = sum(rack.level_ids.mapped('used_capacity'))
            rack.capacity_utilization = (rack.used_capacity / rack.total_capacity * 100) if rack.total_capacity else 0
    
    def name_get(self):
        result = []
        for rack in self:
            name = f'[{rack.zone_id.code}/{rack.aisle_id.code}/{rack.code}] {rack.name}'
            result.append((rack.id, name))
        return result
