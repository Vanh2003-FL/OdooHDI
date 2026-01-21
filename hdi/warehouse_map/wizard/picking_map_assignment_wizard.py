# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PickingMapAssignmentWizard(models.TransientModel):
    """Wizard để assign locations từ warehouse map cho picking"""
    _name = 'picking.map.assignment.wizard'
    _description = 'Assign Locations from Warehouse Map'
    
    picking_id = fields.Many2one('stock.picking', string='Picking', required=True)
    warehouse_map_id = fields.Many2one('warehouse.map', string='Warehouse Map', required=True)
    
    picking_type = fields.Selection(related='picking_id.picking_type_code', readonly=True)
    
    # For incoming pickings (putaway)
    suggested_putaway_ids = fields.Many2many(
        'hdi.putaway.suggestion',
        string='Putaway Suggestions',
        compute='_compute_suggested_putaway'
    )
    
    # Assignment lines
    assignment_line_ids = fields.One2many(
        'picking.map.assignment.line',
        'wizard_id',
        string='Location Assignments'
    )
    
    @api.depends('picking_id', 'picking_id.move_ids_without_package')
    def _compute_suggested_putaway(self):
        """Get putaway suggestions for products"""
        for wizard in self:
            if wizard.picking_type == 'incoming':
                products = wizard.picking_id.move_ids_without_package.mapped('product_id')
                
                suggestions = self.env['hdi.putaway.suggestion'].search([
                    ('product_id', 'in', products.ids),
                    ('state', '=', 'suggested')
                ], order='priority desc')
                
                wizard.suggested_putaway_ids = suggestions
            else:
                wizard.suggested_putaway_ids = False
    
    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        """Generate assignment lines from picking moves"""
        if self.picking_id:
            lines = []
            
            for move in self.picking_id.move_ids_without_package:
                # Get suggested location
                suggested_location = False
                
                if self.picking_type == 'incoming':
                    # Find best putaway location
                    putaway = self.env['hdi.putaway.suggestion'].search([
                        ('product_id', '=', move.product_id.id),
                        ('state', '=', 'suggested')
                    ], order='priority desc, score desc', limit=1)
                    
                    if putaway:
                        suggested_location = putaway.location_id
                    else:
                        # Fallback to any available location
                        suggested_location = self.env['stock.location'].search([
                            ('location_id', 'child_of', self.picking_id.location_dest_id.id),
                            ('usage', '=', 'internal'),
                            ('is_putable', '=', True),
                        ], order='location_priority asc', limit=1)
                
                lines.append((0, 0, {
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'product_qty': move.product_uom_qty,
                    'suggested_location_id': suggested_location.id if suggested_location else False,
                    'selected_location_id': suggested_location.id if suggested_location else False,
                }))
            
            self.assignment_line_ids = lines
    
    def action_apply_assignments(self):
        """Apply location assignments to picking"""
        self.ensure_one()
        
        if not self.assignment_line_ids:
            raise UserError(_('No assignments to apply!'))
        
        # Update move destination locations
        for line in self.assignment_line_ids:
            if line.selected_location_id:
                line.move_id.write({
                    'location_dest_id': line.selected_location_id.id
                })
                
                # Also update existing move lines if any
                line.move_id.move_line_ids.write({
                    'location_dest_id': line.selected_location_id.id
                })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Location assignments applied successfully!'),
                'type': 'success',
            }
        }
    
    def action_open_map(self):
        """Open warehouse map to select locations visually"""
        self.ensure_one()
        
        return self.warehouse_map_id.action_view_map()


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
