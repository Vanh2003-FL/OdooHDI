# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    def action_assign_warehouse_map_position(self):
        """Mở wizard gán vị trí 3D cho phiếu nhập kho"""
        self.ensure_one()
        # Lấy move_line đầu tiên nếu có tracking
        move_line = self.move_line_ids.filtered(
            lambda x: x.product_id.tracking in ('lot', 'serial')
        )
        if move_line:
            move_line = move_line[0]
            # Tìm warehouse.map.3d của warehouse này (lấy từ picking_type)
            warehouse_id = self.picking_type_id.warehouse_id.id if self.picking_type_id.warehouse_id else None
            if not warehouse_id:
                raise UserError('Loại phiếu này không có kho gắn liền. Vui lòng cấu hình kho cho loại phiếu.')
            
            warehouse_map_3d = self.env['warehouse.map.3d'].search([
                ('warehouse_id', '=', warehouse_id),
                ('active', '=', True),
            ], limit=1)
            
            if not warehouse_map_3d:
                raise UserError('Không có sơ đồ kho 3D nào được kích hoạt cho kho này. Vui lòng tạo sơ đồ kho 3D trước.')
            
            return {
                'name': 'Gán vị trí 3D cho sản phẩm/Lot',
                'type': 'ir.actions.act_window',
                'res_model': 'move.line.warehouse.map.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_move_line_id': move_line.id,
                    'default_picking_id': self.id,
                    'default_warehouse_map_3d_id': warehouse_map_3d.id,
                }
            }
        else:
            raise UserError('Không có sản phẩm nào có Lot/Serial trong phiếu nhập này')
    
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

