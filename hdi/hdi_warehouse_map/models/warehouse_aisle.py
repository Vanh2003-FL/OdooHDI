# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class WarehouseAisle(models.Model):
    _name = 'warehouse.aisle'
    _description = 'Warehouse Aisle'
    _order = 'zone_id, sequence, name'

    name = fields.Char(string='Aisle Name', required=True, index=True)
    code = fields.Char(string='Aisle Code', required=True, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    zone_id = fields.Many2one('warehouse.zone', string='Zone', required=True, ondelete='cascade', index=True)
    warehouse_id = fields.Many2one('stock.warehouse', related='zone_id.warehouse_id', string='Warehouse', store=True, index=True)
    
    # Structure
    rack_ids = fields.One2many('warehouse.rack', 'aisle_id', string='Racks')
    rack_count = fields.Integer(string='Rack Count', compute='_compute_rack_count', store=True)
    
    # Capacity
    total_capacity = fields.Float(string='Total Capacity (m³)', compute='_compute_capacity', store=True)
    used_capacity = fields.Float(string='Used Capacity (m³)', compute='_compute_capacity')
    capacity_utilization = fields.Float(string='Utilization (%)', compute='_compute_capacity')
    
    # Visualization
    position_x = fields.Float(string='Position X')
    position_y = fields.Float(string='Position Y')
    width = fields.Float(string='Width (m)')
    length = fields.Float(string='Length (m)')
    
    description = fields.Text(string='Description')
    
    _sql_constraints = [
        ('code_unique', 'unique(code, zone_id)', 'Aisle code must be unique per zone!'),
    ]
    
    @api.depends('rack_ids')
    def _compute_rack_count(self):
        for aisle in self:
            aisle.rack_count = len(aisle.rack_ids)
    
    @api.depends('rack_ids.total_capacity', 'rack_ids.used_capacity')
    def _compute_capacity(self):
        for aisle in self:
            aisle.total_capacity = sum(aisle.rack_ids.mapped('total_capacity'))
            aisle.used_capacity = sum(aisle.rack_ids.mapped('used_capacity'))
            aisle.capacity_utilization = (aisle.used_capacity / aisle.total_capacity * 100) if aisle.total_capacity else 0
    
    def name_get(self):
        result = []
        for aisle in self:
            name = f'[{aisle.zone_id.code}/{aisle.code}] {aisle.name}'
            result.append((aisle.id, name))
        return result
