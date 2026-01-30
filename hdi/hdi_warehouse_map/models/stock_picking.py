# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    # Bin visualization
    highlight_bins = fields.Boolean(string='Highlight Bins on Map', default=True,
                                     help='FR-8, FR-10: Highlight bins on warehouse map')
    
    def action_view_warehouse_map(self):
        """FR-8, FR-10: Open warehouse map with highlighted bins"""
        self.ensure_one()
        
        bin_ids = []
        for move in self.move_ids:
            if move.source_bin_id:
                bin_ids.append(move.source_bin_id.id)
            if move.dest_bin_id:
                bin_ids.append(move.dest_bin_id.id)
            if move.suggested_bin_id:
                bin_ids.append(move.suggested_bin_id.id)
        
        return {
            'name': _('Warehouse Map - %s') % self.name,
            'type': 'ir.actions.client',
            'tag': 'warehouse_map_view',
            'context': {
                'default_warehouse_id': self.picking_type_id.warehouse_id.id,
                'highlight_bin_ids': list(set(bin_ids)),
                'picking_id': self.id,
            }
        }
    
    def action_suggest_putaway_bins(self):
        """FR-7: Suggest putaway bins for all moves"""
        self.ensure_one()
        
        for move in self.move_ids.filtered(lambda m: m.state not in ['done', 'cancel']):
            suggested_bin = move._get_suggested_putaway_bin()
            if suggested_bin:
                move.write({
                    'suggested_bin_id': suggested_bin.id,
                    'selected_bin_id': suggested_bin.id,
                    'location_dest_id': suggested_bin.location_id.id,
                })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Putaway Suggestion'),
                'message': _('Suggested bins have been assigned to moves.'),
                'type': 'success',
                'sticky': False,
            }
        }
