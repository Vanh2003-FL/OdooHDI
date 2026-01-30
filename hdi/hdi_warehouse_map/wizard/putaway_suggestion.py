# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PutawaySuggestion(models.TransientModel):
    _name = 'putaway.suggestion'
    _description = 'Putaway Bin Suggestion'
    
    picking_id = fields.Many2one('stock.picking', string='Picking', required=True)
    line_ids = fields.One2many('putaway.suggestion.line', 'wizard_id', string='Suggestions')
    
    @api.model
    def default_get(self, fields_list):
        """Generate suggestions for all moves"""
        res = super().default_get(fields_list)
        
        picking_id = self.env.context.get('active_id')
        if picking_id:
            picking = self.env['stock.picking'].browse(picking_id)
            res['picking_id'] = picking_id
            
            lines = []
            for move in picking.move_ids.filtered(lambda m: m.state not in ['done', 'cancel']):
                suggested_bin = move._get_suggested_putaway_bin()
                lines.append((0, 0, {
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'quantity': move.product_uom_qty,
                    'suggested_bin_id': suggested_bin.id if suggested_bin else False,
                    'selected_bin_id': suggested_bin.id if suggested_bin else False,
                }))
            res['line_ids'] = lines
        
        return res
    
    def action_apply_suggestions(self):
        """Apply suggested bins to moves"""
        self.ensure_one()
        
        for line in self.line_ids:
            if line.selected_bin_id:
                line.move_id.write({
                    'suggested_bin_id': line.suggested_bin_id.id,
                    'selected_bin_id': line.selected_bin_id.id,
                    'location_dest_id': line.selected_bin_id.location_id.id,
                })
        
        return {'type': 'ir.actions.act_window_close'}


class PutawaySuggestionLine(models.TransientModel):
    _name = 'putaway.suggestion.line'
    _description = 'Putaway Suggestion Line'
    
    wizard_id = fields.Many2one('putaway.suggestion', string='Wizard', required=True, ondelete='cascade')
    move_id = fields.Many2one('stock.move', string='Move', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity')
    
    suggested_bin_id = fields.Many2one('warehouse.bin', string='Suggested Bin')
    selected_bin_id = fields.Many2one('warehouse.bin', string='Selected Bin')
    
    # Display information
    bin_state = fields.Selection(related='selected_bin_id.state', string='Bin State')
    bin_current_product = fields.Many2one(related='selected_bin_id.current_product_id', string='Current Product')
