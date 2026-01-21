# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PickingMapAssignmentLine(models.TransientModel):
    """Line for location assignment"""
    _name = 'picking.map.assignment.line'
    _description = 'Picking Map Assignment Line'
    
    wizard_id = fields.Many2one('picking.map.assignment.wizard', required=True, ondelete='cascade')
    move_id = fields.Many2one('stock.move', string='Move', required=True)
    
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_qty = fields.Float(string='Quantity')
    
    suggested_location_id = fields.Many2one('stock.location', string='Suggested Location')
    selected_location_id = fields.Many2one('stock.location', string='Selected Location', required=True)
    
    # Map coordinates
    suggested_map_x = fields.Integer(related='suggested_location_id.coordinate_x', readonly=True)
    suggested_map_y = fields.Integer(related='suggested_location_id.coordinate_y', readonly=True)
    
    selected_map_x = fields.Integer(related='selected_location_id.coordinate_x', readonly=True)
    selected_map_y = fields.Integer(related='selected_location_id.coordinate_y', readonly=True)
    
    # Display info
    location_info = fields.Char(compute='_compute_location_info')
    
    @api.depends('selected_location_id', 'selected_map_x', 'selected_map_y')
    def _compute_location_info(self):
        """Generate location display info"""
        for line in self:
            if line.selected_location_id:
                info = line.selected_location_id.complete_name
                if line.selected_map_x or line.selected_map_y:
                    info += f" [{line.selected_map_x},{line.selected_map_y}]"
                line.location_info = info
            else:
                line.location_info = ''
