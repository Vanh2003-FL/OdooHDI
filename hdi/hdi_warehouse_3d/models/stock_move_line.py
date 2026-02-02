# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # Track if bin has been assigned via 3D
    warehouse_bin_assigned = fields.Boolean(
        string='Bin Assigned via 3D',
        default=False,
        help='Indicates that destination bin was assigned using 3D warehouse view'
    )
    
    assigned_bin_id = fields.Many2one(
        'stock.location',
        string='Assigned Bin',
        domain=[('usage', '=', 'internal'), ('shelf_id', '!=', False)],
        help='Bin assigned via 3D putaway'
    )

    def action_assign_to_bin_3d(self, bin_id):
        """Assign this move line to a specific bin
        📌 This is called from 3D view
        📌 Does NOT validate the picking - just sets destination
        """
        self.ensure_one()
        
        bin_location = self.env['stock.location'].browse(bin_id)
        
        if not bin_location.exists() or bin_location.usage != 'internal':
            raise ValueError('Invalid bin location')
        
        if bin_location.is_blocked:
            raise ValueError(f'Bin is blocked: {bin_location.block_reason}')
        
        # Check bin capacity
        current_qty = sum(bin_location.quant_ids.mapped('quantity'))
        if current_qty + self.reserved_uom_qty > bin_location.max_capacity:
            raise ValueError('Bin capacity would be exceeded')
        
        # Update destination location
        self.write({
            'location_dest_id': bin_location.id,
            'warehouse_bin_assigned': True,
            'assigned_bin_id': bin_location.id,
        })
        
        return {
            'success': True,
            'message': f'Assigned {self.product_id.display_name} to {bin_location.name}',
            'bin_id': bin_location.id,
            'bin_name': bin_location.name,
        }

    def action_clear_bin_assignment(self):
        """Clear bin assignment - revert to default putaway location"""
        self.ensure_one()
        
        # Get default destination from picking type
        default_dest = self.picking_id.location_dest_id
        
        self.write({
            'location_dest_id': default_dest.id,
            'warehouse_bin_assigned': False,
            'assigned_bin_id': False,
        })
