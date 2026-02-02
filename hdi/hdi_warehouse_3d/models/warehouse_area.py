# -*- coding: utf-8 -*-
from odoo import models, fields, api

class WarehouseArea(models.Model):
    _name = 'warehouse.area'
    _description = 'Warehouse Area (Zone)'
    _order = 'sequence, name'

    name = fields.Char(string='Area Name', required=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    
    # Layout properties
    position_x = fields.Float(string='Position X')
    position_y = fields.Float(string='Position Y')
    width = fields.Float(string='Width (m)')
    height = fields.Float(string='Height (m)')
    color = fields.Char(string='Display Color', default='#E8E8FF')
    
    # Temperature control
    temperature_controlled = fields.Boolean(string='Temperature Controlled')
    temperature_min = fields.Float(string='Min Temperature (°C)')
    temperature_max = fields.Float(string='Max Temperature (°C)')
    
    # Relations
    shelf_ids = fields.One2many('warehouse.shelf', 'area_id', string='Shelves')
    shelf_count = fields.Integer(string='Shelf Count', compute='_compute_shelf_count')
    
    active = fields.Boolean(default=True)
    description = fields.Text(string='Description')

    @api.depends('shelf_ids')
    def _compute_shelf_count(self):
        for area in self:
            area.shelf_count = len(area.shelf_ids)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code, warehouse_id)', 'Area code must be unique per warehouse!')
    ]
