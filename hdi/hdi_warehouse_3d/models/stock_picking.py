# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_open_3d_putaway(self):
        """Open 3D view to assign bins for incoming products
        📌 3D không thay thế validate picking
        📌 Chỉ can thiệp vào bước 'đặt hàng ở đâu'
        """
        self.ensure_one()
        
        # Only for incoming/internal transfers
        if self.picking_type_code not in ['incoming', 'internal']:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': '3D Putaway is only for incoming/internal transfers',
                    'type': 'warning',
                }
            }
        
        # Pass picking context to 3D view
        return {
            'type': 'ir.actions.client',
            'tag': 'warehouse_3d_putaway_wizard',
            'context': {
                'default_picking_id': self.id,
                'move_line_ids': self.move_line_ids.ids,
            }
        }

    def _get_move_lines_for_putaway(self):
        """Get move lines that need bin assignment"""
        return self.move_line_ids.filtered(
            lambda ml: ml.location_dest_id.usage == 'internal' 
            and not ml.warehouse_bin_assigned
        )
