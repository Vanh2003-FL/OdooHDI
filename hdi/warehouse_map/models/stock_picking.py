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
    
    def action_assign_serials_to_lot(self):
        """Mở wizard gom serial vào lot"""
        self.ensure_one()
        
        # Lấy move_line có tracking
        move_lines = self.move_line_ids.filtered(
            lambda x: x.product_id.tracking in ('lot', 'serial')
        )
        
        if not move_lines:
            raise UserError(_('Không có sản phẩm nào có Lot/Serial trong phiếu nhập này'))
        
        return {
            'name': 'Gom Serial vào Lot',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot.serial.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_move_line_ids': [(6, 0, move_lines.ids)],
                'default_product_id': move_lines[0].product_id.id if move_lines else False,
            }
        }
    
    def button_validate(self):
        """Override validate - chỉ cho phép gán vị trí AFTER xác nhận"""
        # Proceed với validate bình thường
        result = super().button_validate()
        
        # Cập nhật vị trí quant từ move_line (nếu đã gán)
        if self.picking_type_code == 'incoming':
            self._update_quants_positions_from_move_lines()
        
        return result
    
    def _update_quants_positions_from_move_lines(self):
        """Cập nhật vị trí quant từ move_line có warehouse map position"""
        for picking in self:
            for move_line in picking.move_line_ids:
                # Chỉ cập nhật nếu user thực sự gán vị trí (position_assigned = True)
                if not move_line.position_assigned:
                    continue
                
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

