# -*- coding: utf-8 -*-
"""
Extend stock.location to support warehouse map hierarchy
"""

from odoo import models, fields, api


class StockLocation(models.Model):
    _inherit = 'stock.location'
    
    location_layout_ids = fields.One2many(
        'stock.location.layout',
        'location_id',
        string='Layout Configurations'
    )
    
    location_type = fields.Selection([
        ('zone', 'Zone'),
        ('rack', 'Rack'),
        ('bin', 'Bin'),
        ('other', 'Other'),
    ], string='Location Type', default='other', help='Type for warehouse mapping')
    
    parent_location_type = fields.Selection(
        related='location_id.location_type',
        string='Parent Type',
        store=True
    )
    
    def action_configure_layout(self):
        """Open layout configuration wizard"""
        self.ensure_one()
        
        # Create layout if not exists
        layout = self.env['stock.location.layout'].search([
            ('location_id', '=', self.id)
        ], limit=1)
        
        if not layout:
            warehouse = self.get_warehouse()
            layout = self.env['stock.location.layout'].create({
                'location_id': self.id,
                'warehouse_id': warehouse.id if warehouse else False,
                'location_type': self.location_type if self.location_type != 'other' else 'bin',
            })
        
        return {
            'name': 'Configure Location Layout',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.location.layout',
            'res_id': layout.id,
            'view_mode': 'form',
            'target': 'new',
        }
