# -*- coding: utf-8 -*-
"""
🚀 Warehouse Put-Away Wizard
Assign received goods to specific bin locations using warehouse map

Workflow:
1. From stock.picking (receipt) → Open Put-Away Wizard
2. Select product line
3. Click on warehouse map to assign bin
4. Validate → update stock.move.line.location_dest_id
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WarehousePutAwayWizard(models.TransientModel):
    _name = 'warehouse.putaway.wizard'
    _description = 'Warehouse Put-Away Assignment Wizard'
    
    picking_id = fields.Many2one('stock.picking', string='Receipt', required=True, readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', compute='_compute_warehouse_id', store=True)
    line_ids = fields.One2many('warehouse.putaway.wizard.line', 'wizard_id', string='Products to Put Away')
    
    @api.depends('picking_id')
    def _compute_warehouse_id(self):
        """Get warehouse from picking destination location"""
        for wizard in self:
            wizard.warehouse_id = wizard.picking_id.location_dest_id.warehouse_id
    
    @api.model
    def default_get(self, fields_list):
        """Load move lines from picking context"""
        res = super().default_get(fields_list)
        
        if 'picking_id' not in res and self.env.context.get('active_id'):
            res['picking_id'] = self.env.context['active_id']
        
        picking = self.env['stock.picking'].browse(res.get('picking_id'))
        
        if not picking:
            raise UserError(_('No receipt found in context!'))
        
        # Create wizard lines from move lines that don't have specific bin yet
        lines = []
        for move in picking.move_ids:
            for move_line in move.move_line_ids:
                # Only show lines without specific bin assignment (still at stock location)
                if move_line.location_dest_id == picking.location_dest_id:
                    lines.append((0, 0, {
                        'move_line_id': move_line.id,
                        'product_id': move_line.product_id.id,
                        'quantity': move_line.quantity,
                        'lot_id': move_line.lot_id.id,
                        'current_dest_location_id': move_line.location_dest_id.id,
                    }))
        
        res['line_ids'] = lines
        return res
    
    def action_open_warehouse_map(self):
        """
        🗺️ Open warehouse map view for bin selection
        User clicks on bin → assigns selected product lines
        """
        self.ensure_one()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'warehouse_map_putaway_view',
            'name': _('Select Bin Location'),
            'context': {
                'wizard_id': self.id,
                'warehouse_id': self.warehouse_id.id,
                'picking_id': self.picking_id.id,
            },
            'target': 'new',
        }
    
    def action_validate_putaway(self):
        """
        ✅ Validate put-away assignments
        Updates stock.move.line.location_dest_id for all assigned lines
        """
        self.ensure_one()
        
        for line in self.line_ids:
            if not line.new_dest_location_id:
                raise UserError(
                    _('Product %s has no bin assigned! Please select a bin location.') 
                    % line.product_id.name
                )
            
            # Update move line destination
            line.move_line_id.write({
                'location_dest_id': line.new_dest_location_id.id
            })
        
        # Return to picking form
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class WarehousePutAwayWizardLine(models.TransientModel):
    _name = 'warehouse.putaway.wizard.line'
    _description = 'Put-Away Wizard Line (Product to Assign)'
    
    wizard_id = fields.Many2one('warehouse.putaway.wizard', required=True, ondelete='cascade')
    move_line_id = fields.Many2one('stock.move.line', string='Move Line', required=True, readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    quantity = fields.Float('Quantity', readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial', readonly=True)
    current_dest_location_id = fields.Many2one('stock.location', string='Current Destination', readonly=True)
    new_dest_location_id = fields.Many2one('stock.location', string='New Bin Location', domain=[('location_type', '=', 'bin')])
    
    @api.onchange('new_dest_location_id')
    def _onchange_new_dest_location(self):
        """Show bin capacity info when selected"""
        if self.new_dest_location_id:
            # Get current stock in selected bin
            quants = self.env['stock.quant'].search([
                ('location_id', '=', self.new_dest_location_id.id)
            ])
            total_qty = sum(quants.mapped('quantity'))
            
            if total_qty > 0:
                return {
                    'warning': {
                        'title': _('Bin Already Contains Stock'),
                        'message': _('Bin %s currently has %s items. Continue?') 
                            % (self.new_dest_location_id.name, total_qty)
                    }
                }
