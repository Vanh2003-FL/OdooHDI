# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    # Link to Bin
    bin_id = fields.Many2one('warehouse.bin', related='location_id.bin_id', 
                             string='Warehouse Bin', store=True, index=True)
    zone_id = fields.Many2one('warehouse.zone', related='bin_id.zone_id', 
                              string='Zone', store=True, index=True)
    
    # Bin status
    bin_state = fields.Selection(related='bin_id.state', string='Bin Status')
    bin_blocked = fields.Boolean(related='bin_id.is_blocked', string='Bin Blocked')
    
    def action_view_bin_details(self):
        """View bin details"""
        self.ensure_one()
        if not self.bin_id:
            return
        
        return {
            'name': _('Bin Details'),
            'type': 'ir.actions.act_window',
            'res_model': 'warehouse.bin',
            'res_id': self.bin_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
