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
    
    # Area type (SKUSavvy: Areas are for marking zones, NOT for containing shelves)
    # Examples: cashier desk, checkout counter, office, receiving dock
    area_type = fields.Selection([
        ('cashier', 'Cashier Desk'),
        ('checkout', 'Checkout Counter'),
        ('office', 'Office Area'),
        ('inbound', 'Receiving Dock'),
        ('outbound', 'Shipping Dock'),
        ('staging', 'Staging Zone'),
        ('quality', 'Quality Check'),
        ('storage', 'Storage Zone (reference only)'),
    ], string='Area Type', required=True, default='storage',
       help='Area marks zones for operations. Shelves are placed independently.')
    
    # Layout properties (boundary marking on 2D canvas)
    position_x = fields.Float(string='Position X')
    position_y = fields.Float(string='Position Y')
    width = fields.Float(string='Width (m)')
    height = fields.Float(string='Height (m)')
    boundary = fields.Text(string='Boundary Polygon', help='JSON array of [x,y] coordinates defining area boundary')
    color = fields.Char(string='Display Color', default='#E8E8FF')
    
    # Temperature control (for storage zones)
    temperature_controlled = fields.Boolean(string='Temperature Controlled')
    temperature_min = fields.Float(string='Min Temperature (°C)')
    temperature_max = fields.Float(string='Max Temperature (°C)')
    
    # Relations (informational only - shelves are NOT contained by area)
    shelf_ids = fields.One2many('warehouse.shelf', 'area_id', string='Shelves (Reference)',
                               help='Shelves that reference this area (informational only)')
    
    active = fields.Boolean(default=True)
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code, warehouse_id)', 'Area code must be unique per warehouse!')
    ]
