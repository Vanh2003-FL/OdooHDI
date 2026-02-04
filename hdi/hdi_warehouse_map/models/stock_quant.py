# -*- coding: utf-8 -*-
"""
Extend stock.quant for warehouse map integration
⚠️ NO CREATE/WRITE - ONLY READ for visualization
"""

from odoo import models, api


class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    def get_location_layout_info(self):
        """
        📖 Get layout information for quant's location
        Used for visualization on warehouse map
        """
        self.ensure_one()
        layout = self.env['stock.location.layout'].search([
            ('location_id', '=', self.location_id.id)
        ], limit=1)
        
        if layout:
            return {
                'layout_id': layout.id,
                'x': layout.x,
                'y': layout.y,
                'z': layout.z_level,
                'color': layout.color,
            }
        return {}
    
    @api.model
    def get_heatmap_data(self, warehouse_id):
        """
        🌡️ Generate heatmap data for warehouse visualization
        Returns: {location_id: quantity_percentage}
        """
        warehouse = self.env['stock.warehouse'].browse(warehouse_id)
        lot_stock_location = warehouse.lot_stock_id
        
        # Get all quants in this warehouse
        quants = self.search([
            ('location_id', 'child_of', lot_stock_location.id),
            ('quantity', '>', 0)
        ])
        
        # Calculate max quantity for normalization
        location_quantities = {}
        for quant in quants:
            location_id = quant.location_id.id
            if location_id not in location_quantities:
                location_quantities[location_id] = 0
            location_quantities[location_id] += quant.quantity
        
        if not location_quantities:
            return {}
        
        max_qty = max(location_quantities.values())
        
        # Normalize to percentage
        heatmap = {
            loc_id: (qty / max_qty * 100) if max_qty > 0 else 0
            for loc_id, qty in location_quantities.items()
        }
        
        return heatmap
