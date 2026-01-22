# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    def action_assign_warehouse_map_position(self):
        """Mở wizard gán vị trí cho phiếu nhập kho"""
        self.ensure_one()
        # Lấy move_line đầu tiên nếu có tracking
        move_line = self.move_line_ids.filtered(
            lambda x: x.product_id.tracking in ('lot', 'serial')
        )
        if move_line:
            move_line = move_line[0]
            return {
                'name': 'Gán vị trí sản phẩm/Lot',
                'type': 'ir.actions.act_window',
                'res_model': 'move.line.warehouse.map.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_move_line_id': move_line.id,
                    'default_picking_id': self.id,
                }
            }
        else:
            raise UserError('Không có sản phẩm nào có Lot/Serial trong phiếu nhập này')
    
    def button_validate(self):
        """Override validate để bắt buộc gán vị trí trước khi xác nhận phiếu kho"""
        self.ensure_one()
        
        # Chỉ check vị trí cho phiếu nhập kho (incoming)
        if self.picking_type_code == 'incoming':
            # Kiểm tra move_line có tracking (lot/serial) chưa gán vị trí
            move_lines_need_position = self.move_line_ids.filtered(
                lambda x: x.product_id.tracking in ('lot', 'serial') 
                and (not x.posx or not x.posy)
            )
            
            # Nếu có move_line chưa gán vị trí thì mở wizard
            if move_lines_need_position:
                return {
                    'name': 'Gán vị trí sản phẩm/Lot',
                    'type': 'ir.actions.act_window',
                    'res_model': 'move.line.warehouse.map.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_move_line_id': move_lines_need_position[0].id,
                        'default_picking_id': self.id,
                    }
                }
        
        # Nếu tất cả đã gán vị trí hoặc không cần tracking, proceed với validate
        result = super().button_validate()
        
        # Cập nhật vị trí quant từ move_line
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

