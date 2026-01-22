# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    def button_validate(self):
        """Override validate để cập nhật vị trí quant từ warehouse map"""
        # Gọi parent validate trước (này sẽ tạo quant)
        result = super().button_validate()
        
        # Cập nhật vị trí quant từ move_line có warehouse map position
        if self.picking_type_code == 'incoming':
            self._update_quants_positions_from_move_lines()
        
        return result
    
    def _update_quants_positions_from_move_lines(self):
        """Cập nhật vị trí quant từ move_line có warehouse map position"""
        for picking in self:
            for move_line in picking.move_line_ids:
                # Kiểm tra move_line có vị trí không
                if not move_line.posx or not move_line.posy:
                    continue
                
                # Kiểm tra sản phẩm có tracking không
                if move_line.product_id.tracking == 'none':
                    continue
                
                # Tìm quant đã tạo từ move (qua stock.move -> quants)
                # Quants được tạo với lot_id tương ứng
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', move_line.product_id.id),
                    ('lot_id', '=', move_line.lot_id.id or False),
                    ('location_id', '=', move_line.location_dest_id.id),
                ])
                
                if quants:
                    # Cập nhật vị trí cho quant
                    for quant in quants:
                        quant.write({
                            'posx': move_line.posx,
                            'posy': move_line.posy,
                            'posz': move_line.posz or 0,
                            'display_on_map': True,
                        })

