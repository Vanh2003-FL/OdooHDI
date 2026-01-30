# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class WarehouseZone(models.Model):
    _name = 'warehouse.zone'
    _description = 'Warehouse Zone'
    _order = 'sequence, name'

    name = fields.Char(string='Zone Name', required=True, index=True)
    code = fields.Char(string='Zone Code', required=True, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, ondelete='cascade')
    location_id = fields.Many2one('stock.location', string='Parent Location', required=True, 
                                   domain="[('usage', '=', 'internal')]")
    
    # Structure
    aisle_ids = fields.One2many('warehouse.aisle', 'zone_id', string='Aisles')
    aisle_count = fields.Integer(string='Aisle Count', compute='_compute_aisle_count', store=True)
    
    # Configuration
    allowed_category_ids = fields.Many2many('product.category', string='Allowed Product Categories',
                                             help='Nếu để trống, cho phép tất cả danh mục')
    temperature_controlled = fields.Boolean(string='Temperature Controlled')
    temperature_min = fields.Float(string='Min Temperature (°C)')
    temperature_max = fields.Float(string='Max Temperature (°C)')
    
    # Capacity
    total_capacity = fields.Float(string='Total Capacity (m³)', compute='_compute_capacity', store=True)
    used_capacity = fields.Float(string='Used Capacity (m³)', compute='_compute_capacity')
    capacity_utilization = fields.Float(string='Utilization (%)', compute='_compute_capacity')
    
    # Visualization
    color = fields.Char(string='Color', default='#3498db', help='Màu hiển thị trên sơ đồ')
    position_x = fields.Float(string='Position X')
    position_y = fields.Float(string='Position Y')
    width = fields.Float(string='Width (m)')
    height = fields.Float(string='Height (m)')
    
    description = fields.Text(string='Description')
    
    _sql_constraints = [
        ('code_unique', 'unique(code, warehouse_id)', 'Zone code must be unique per warehouse!'),
    ]
    
    @api.depends('aisle_ids')
    def _compute_aisle_count(self):
        for zone in self:
            zone.aisle_count = len(zone.aisle_ids)
    
    @api.depends('aisle_ids.total_capacity', 'aisle_ids.used_capacity')
    def _compute_capacity(self):
        for zone in self:
            zone.total_capacity = sum(zone.aisle_ids.mapped('total_capacity'))
            zone.used_capacity = sum(zone.aisle_ids.mapped('used_capacity'))
            zone.capacity_utilization = (zone.used_capacity / zone.total_capacity * 100) if zone.total_capacity else 0
    
    def name_get(self):
        result = []
        for zone in self:
            name = f'[{zone.code}] {zone.name}'
            result.append((zone.id, name))
        return result
    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            args = ['|', ('name', operator, name), ('code', operator, name)] + args
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)
