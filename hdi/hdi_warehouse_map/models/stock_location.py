# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class StockLocation(models.Model):
    _inherit = 'stock.location'
    
    # Link to Bin
    bin_id = fields.Many2one('warehouse.bin', string='Warehouse Bin', ondelete='restrict', index=True)
    
    # Bin information
    is_bin_location = fields.Boolean(string='Is Bin Location', compute='_compute_is_bin_location', store=True)
    zone_id = fields.Many2one('warehouse.zone', related='bin_id.zone_id', string='Zone', store=True)
    aisle_id = fields.Many2one('warehouse.aisle', related='bin_id.aisle_id', string='Aisle', store=True)
    rack_id = fields.Many2one('warehouse.rack', related='bin_id.rack_id', string='Rack', store=True)
    level_id = fields.Many2one('warehouse.level', related='bin_id.level_id', string='Level', store=True)
    
    @api.depends('bin_id')
    def _compute_is_bin_location(self):
        for location in self:
            location.is_bin_location = bool(location.bin_id)
    
    def action_view_bin_map(self):
        """Open warehouse map focused on this bin"""
        self.ensure_one()
        if not self.bin_id:
            return
        
        return {
            'name': _('Warehouse Map'),
            'type': 'ir.actions.client',
            'tag': 'warehouse_map_view',
            'context': {
                'default_warehouse_id': self.warehouse_id.id,
                'highlight_bin_id': self.bin_id.id,
            }
        }
