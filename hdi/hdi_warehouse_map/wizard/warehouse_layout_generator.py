# -*- coding: utf-8 -*-
from odoo import models, fields, api

class WarehouseLayoutGenerator(models.TransientModel):
    _name = 'warehouse.layout.generator'
    _description = 'Auto-generate warehouse layout from existing locations'
    
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    location_domain = fields.Selection([
        ('all', 'All Internal Locations'),
        ('empty_only', 'Locations without Layout'),
        ('with_stock', 'Locations with Stock'),
    ], string='Generate for', default='empty_only', required=True)
    
    grid_width = fields.Integer(string='Grid Width (px)', default=80)
    grid_height = fields.Integer(string='Grid Height (px)', default=60)
    columns = fields.Integer(string='Columns per Row', default=10)
    auto_arrange = fields.Boolean(string='Auto Arrange in Grid', default=True)
    
    def action_generate_layout(self):
        """Generate layout records for locations"""
        self.ensure_one()
        
        # Get warehouse locations
        domain = [
            ('usage', '=', 'internal'),
            ('company_id', '=', self.warehouse_id.company_id.id),
        ]
        
        # Filter based on selection
        if self.location_domain == 'empty_only':
            existing_layouts = self.env['stock.location.layout'].search([
                ('warehouse_id', '=', self.warehouse_id.id)
            ]).mapped('location_id')
            domain.append(('id', 'not in', existing_layouts.ids))
        elif self.location_domain == 'with_stock':
            locations_with_stock = self.env['stock.quant'].search([
                ('location_id.usage', '=', 'internal'),
                ('quantity', '>', 0)
            ]).mapped('location_id')
            domain.append(('id', 'in', locations_with_stock.ids))
        
        locations = self.env['stock.location'].search(domain)
        
        if not locations:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Locations Found',
                    'message': 'No locations to generate layout for',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Generate layout records
        created_count = 0
        x, y = 50, 50  # Starting position
        col = 0
        
        for location in locations:
            # Determine location type from name/structure
            location_type = 'bin'
            if 'zone' in location.name.lower() or location.location_id.usage == 'view':
                location_type = 'zone'
            elif 'rack' in location.name.lower() or 'shelf' in location.name.lower():
                location_type = 'rack'
            
            # Auto-arrange in grid
            if self.auto_arrange:
                if col >= self.columns:
                    col = 0
                    y += self.grid_height + 20
                x = 50 + (col * (self.grid_width + 10))
                col += 1
            
            # Create layout record
            self.env['stock.location.layout'].create({
                'warehouse_id': self.warehouse_id.id,
                'location_id': location.id,
                'location_type': location_type,
                'x': x,
                'y': y,
                'z_level': 0,
                'width': self.grid_width,
                'height': self.grid_height,
                'view_type': 'both',
                'color': '#3498db' if location_type == 'bin' else '#e74c3c',
            })
            created_count += 1
        
        # Show result and open layouts
        return {
            'type': 'ir.actions.act_window',
            'name': f'Generated Layouts ({created_count})',
            'res_model': 'stock.location.layout',
            'view_mode': 'list,form',
            'domain': [('warehouse_id', '=', self.warehouse_id.id)],
            'context': {'create': False},
        }
