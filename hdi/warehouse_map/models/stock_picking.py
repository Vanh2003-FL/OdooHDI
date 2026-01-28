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
        
        # Cập nhật display_on_map cho outgoing (xuất kho) và internal (chuyển kho)
        if self.picking_type_code in ('outgoing', 'internal'):
            self._update_quants_display_on_map()
        
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
    
    def _update_quants_display_on_map(self):
        """Cập nhật display_on_map cho quants sau khi pick/transfer
        
        Logic:
        - Nếu quantity <= 0: Ẩn khỏi sơ đồ (display_on_map = False) và set qty = 0
        - Nếu quantity > 0: Vẫn hiển thị với số lượng còn lại
        """
        for picking in self:
            for move_line in picking.move_line_ids:
                # Xử lý cho location nguồn (nơi lấy hàng ra)
                quants_source = self.env['stock.quant'].search([
                    ('product_id', '=', move_line.product_id.id),
                    ('location_id', '=', move_line.location_id.id),
                    ('lot_id', '=', move_line.lot_id.id if move_line.lot_id else False),
                ])
                
                for quant in quants_source:
                    # Nếu quantity <= 0 → Ẩn khỏi sơ đồ và fix quantity
                    if quant.quantity <= 0:
                        quant.write({
                            'quantity': 0,
                            'display_on_map': False,
                            'posx': False,
                            'posy': False,
                            'posz': 0,
                        })
                    # Nếu quantity > 0 → Giữ nguyên trên sơ đồ
                    elif quant.quantity > 0 and quant.display_on_map:
                        # Không cần update gì, giữ nguyên position và display_on_map
                        pass
                
                # Xử lý cho location đích (internal transfer)
                if self.picking_type_code == 'internal':
                    quants_dest = self.env['stock.quant'].search([
                        ('product_id', '=', move_line.product_id.id),
                        ('location_id', '=', move_line.location_dest_id.id),
                        ('lot_id', '=', move_line.lot_id.id if move_line.lot_id else False),
                    ])
                    
                    # Set display_on_map = True cho quant ở vị trí đích (nếu có)
                    for quant in quants_dest:
                        if quant.quantity > 0 and not quant.display_on_map:
                            # Chỉ hiển thị nếu có gán vị trí (posx, posy)
                            if quant.posx and quant.posy:
                                quant.write({'display_on_map': True})

