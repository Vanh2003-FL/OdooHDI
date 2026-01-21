# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockQuantIntegration(models.Model):
    """Enhanced stock.quant with automatic map synchronization"""
    _inherit = 'stock.quant'
    
    # Auto-sync with location coordinates
    auto_sync_map_position = fields.Boolean(
        string='Auto-sync Map Position',
        default=True,
        help='Tự động đồng bộ vị trí với location coordinates'
    )
    
    map_sync_status = fields.Selection([
        ('synced', 'Synced'),
        ('manual', 'Manual Position'),
        ('not_set', 'Not Set'),
    ], string='Map Sync Status', compute='_compute_map_sync_status')
    
    @api.depends('posx', 'posy', 'location_id.coordinate_x', 'location_id.coordinate_y')
    def _compute_map_sync_status(self):
        """Check sync status between quant position and location coordinates"""
        for quant in self:
            if not quant.posx and not quant.posy:
                quant.map_sync_status = 'not_set'
            elif (quant.posx == quant.location_id.coordinate_x and 
                  quant.posy == quant.location_id.coordinate_y):
                quant.map_sync_status = 'synced'
            else:
                quant.map_sync_status = 'manual'
    
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-assign map position when creating quant"""
        quants = super().create(vals_list)
        
        for quant in quants:
            if quant.auto_sync_map_position and quant.location_id:
                # Auto-assign from location if not manually set
                if not quant.posx and not quant.posy:
                    if quant.location_id.coordinate_x or quant.location_id.coordinate_y:
                        quant.write({
                            'posx': quant.location_id.coordinate_x or 0,
                            'posy': quant.location_id.coordinate_y or 0,
                            'posz': quant.location_id.coordinate_z or 0,
                            'display_on_map': True,
                        })
        
        return quants
    
    def write(self, vals):
        """Auto-update map position when location changes"""
        result = super().write(vals)
        
        # If location changed and auto-sync enabled
        if 'location_id' in vals:
            for quant in self:
                if quant.auto_sync_map_position:
                    new_location = quant.location_id
                    if new_location.coordinate_x or new_location.coordinate_y:
                        quant.write({
                            'posx': new_location.coordinate_x or 0,
                            'posy': new_location.coordinate_y or 0,
                            'posz': new_location.coordinate_z or 0,
                            'display_on_map': True,
                        })
        
        return result
    
    def action_sync_with_location(self):
        """Manually sync map position with location coordinates"""
        for quant in self:
            if quant.location_id:
                quant.write({
                    'posx': quant.location_id.coordinate_x or 0,
                    'posy': quant.location_id.coordinate_y or 0,
                    'posz': quant.location_id.coordinate_z or 0,
                    'display_on_map': True,
                })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Synced'),
                'message': _('Map positions synced with location coordinates.'),
                'type': 'success',
            }
        }
    
    def action_set_custom_position(self):
        """Open wizard to set custom map position"""
        self.ensure_one()
        
        # Find warehouse map
        warehouse = self.env['stock.warehouse'].search([
            ('lot_stock_id', 'parent_of', self.location_id.id)
        ], limit=1)
        
        if not warehouse:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Warehouse'),
                    'message': _('Cannot find warehouse for this quant.'),
                    'type': 'warning',
                }
            }
        
        warehouse_map = self.env['warehouse.map'].search([
            ('warehouse_id', '=', warehouse.id)
        ], limit=1)
        
        if not warehouse_map:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Map'),
                    'message': _('No warehouse map configured.'),
                    'type': 'warning',
                }
            }
        
        return {
            'name': _('Set Map Position'),
            'type': 'ir.actions.act_window',
            'res_model': 'assign.lot.position.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_warehouse_map_id': warehouse_map.id,
                'default_quant_id': self.id,
                'default_posx': self.posx or 0,
                'default_posy': self.posy or 0,
                'default_posz': self.posz or 0,
            }
        }
