# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PutawayMapBridge(models.Model):
    """Bridge giữa putaway suggestions (hdi_wms) và warehouse map"""
    _inherit = 'hdi.putaway.suggestion'
    
    # Map position of suggested location
    map_posx = fields.Integer(
        related='suggested_location_id.coordinate_x',
        string='Map Position X',
        readonly=True
    )
    
    map_posy = fields.Integer(
        related='suggested_location_id.coordinate_y',
        string='Map Position Y',
        readonly=True
    )
    
    map_posz = fields.Integer(
        related='suggested_location_id.coordinate_z',
        string='Map Position Z',
        readonly=True
    )
    
    display_on_map = fields.Boolean(
        related='suggested_location_id.display_on_map',
        string='Visible on Map',
        readonly=True
    )
    
    warehouse_map_id = fields.Many2one(
        'warehouse.map',
        compute='_compute_warehouse_map',
        string='Warehouse Map',
        help='Warehouse map chứa vị trí này'
    )
    
    @api.depends('suggested_location_id', 'suggested_location_id.location_id')
    def _compute_warehouse_map(self):
        """Find warehouse map for this putaway suggestion"""
        for putaway in self:
            if putaway.suggested_location_id:
                # Find warehouse
                warehouse = self.env['stock.warehouse'].search([
                    ('lot_stock_id', 'parent_of', putaway.suggested_location_id.id)
                ], limit=1)
                
                if warehouse:
                    warehouse_map = self.env['warehouse.map'].search([
                        ('warehouse_id', '=', warehouse.id)
                    ], limit=1)
                    putaway.warehouse_map_id = warehouse_map.id if warehouse_map else False
                else:
                    putaway.warehouse_map_id = False
            else:
                putaway.warehouse_map_id = False
    
    def action_show_on_map(self):
        """Hiển thị vị trí putaway trên warehouse map"""
        self.ensure_one()
        
        if not self.warehouse_map_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Map Available'),
                    'message': _('No warehouse map found for this location.'),
                    'type': 'warning',
                }
            }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'warehouse_map_view',
            'name': f'Putaway Location - {self.suggested_location_id.name}',
            'context': {
                'active_id': self.warehouse_map_id.id,
                'highlight_location_ids': [self.suggested_location_id.id],
                'center_on_location': self.suggested_location_id.id,
            }
        }


class HdiBatchMapIntegration(models.Model):
    """Tích hợp Batch với warehouse map"""
    _inherit = 'hdi.batch'
    
    # Map position
    map_posx = fields.Integer(
        related='location_id.coordinate_x',
        string='Map X',
        readonly=True
    )
    
    map_posy = fields.Integer(
        related='location_id.coordinate_y',
        string='Map Y',
        readonly=True
    )
    
    map_posz = fields.Integer(
        related='location_id.coordinate_z',
        string='Map Z',
        readonly=True
    )
    
    warehouse_map_id = fields.Many2one(
        'warehouse.map',
        compute='_compute_warehouse_map',
        string='Warehouse Map'
    )
    
    @api.depends('location_id')
    def _compute_warehouse_map(self):
        """Find warehouse map"""
        for batch in self:
            if batch.location_id:
                warehouse = self.env['stock.warehouse'].search([
                    ('lot_stock_id', 'parent_of', batch.location_id.id)
                ], limit=1)
                
                if warehouse:
                    warehouse_map = self.env['warehouse.map'].search([
                        ('warehouse_id', '=', warehouse.id)
                    ], limit=1)
                    batch.warehouse_map_id = warehouse_map.id if warehouse_map else False
                else:
                    batch.warehouse_map_id = False
            else:
                batch.warehouse_map_id = False
    
    def action_show_on_map(self):
        """Show batch location on warehouse map"""
        self.ensure_one()
        
        if not self.warehouse_map_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Map Available'),
                    'message': _('No warehouse map found for this batch location.'),
                    'type': 'warning',
                }
            }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'warehouse_map_view',
            'name': f'Batch Location - {self.name}',
            'context': {
                'active_id': self.warehouse_map_id.id,
                'highlight_location_ids': [self.location_id.id],
                'highlight_batch_id': self.id,
            }
        }
