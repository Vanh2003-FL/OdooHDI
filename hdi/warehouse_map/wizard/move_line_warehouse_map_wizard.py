# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MoveLineWarehouseMapWizard(models.TransientModel):
    """Wizard để gán vị trí 3D sản phẩm/lot từ bảng nhập kho"""
    _name = 'move.line.warehouse.map.wizard'
    _description = 'Gán vị trí 3D sản phẩm/Lot trên sơ đồ kho'

    move_line_id = fields.Many2one('stock.move.line', string='Move Line', required=True, readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Phiếu nhập kho', required=True, readonly=True)
    
    # Thông tin sản phẩm
    product_id = fields.Many2one('product.product', string='Sản phẩm', 
                                  readonly=True)
    lot_name = fields.Char(string='Lot/Serial', readonly=True)  # Hiển thị lot name từ move_line
    lot_id = fields.Many2one('stock.lot', string='Chọn Lot nếu cần')  # Cho phép chọn nếu move_line chưa có
    quantity = fields.Float(string='Số lượng', readonly=True)
    location_dest_id = fields.Many2one('stock.location', string='Vị trí đích', 
                                        readonly=True)
    
    # Sơ đồ kho 3D (không còn 2D)
    warehouse_map_3d_id = fields.Many2one('warehouse.map.3d', string='Sơ đồ kho 3D', required=True)
    
    @api.model
    def default_get(self, fields_list):
        """Load dữ liệu từ move_line_id"""
        result = super().default_get(fields_list)
        
        if self._context.get('default_move_line_id'):
            move_line = self.env['stock.move.line'].browse(self._context.get('default_move_line_id'))
            
            if 'product_id' in fields_list:
                result['product_id'] = move_line.product_id.id
            
            # Lấy lot name từ move_line (dù chưa save vào DB)
            if 'lot_name' in fields_list:
                if move_line.lot_id:
                    result['lot_name'] = move_line.lot_id.name
                else:
                    result['lot_name'] = ''
            
            # Load lot_id để cho phép chọn
            if 'lot_id' in fields_list:
                if move_line.lot_id:
                    result['lot_id'] = move_line.lot_id.id
                else:
                    result['lot_id'] = False
            
            if 'quantity' in fields_list:
                result['quantity'] = move_line.quantity
            
            if 'location_dest_id' in fields_list:
                result['location_dest_id'] = move_line.location_dest_id.id
        
        return result
    
    # Chọn sơ đồ kho 3D (không còn 2D)
    warehouse_map_3d_id = fields.Many2one('warehouse.map.3d', string='Sơ đồ kho 3D', required=True)
    
    # Vị trí 3D trên sơ đồ
    posx = fields.Integer(string='Vị trí X (Cột)', required=True, default=0)
    posy = fields.Integer(string='Vị trí Y (Hàng)', required=True, default=0)
    posz = fields.Integer(string='Vị trí Z (Tầng)', required=True, default=0)
    
    @api.onchange('warehouse_map_3d_id')
    def _onchange_warehouse_map(self):
        """Reset position when changing warehouse map"""
        self.posx = 0
        self.posy = 0
        self.posz = 0
    
    def action_open_warehouse_map(self):
        """Mở sơ đồ kho 3D để chọn vị trí"""
        self.ensure_one()
        
        if not self.warehouse_map_3d_id:
            raise UserError(_('Vui lòng chọn sơ đồ kho 3D trước!'))
        
        # Mở warehouse map 3D view
        return {
            'type': 'ir.actions.client',
            'tag': 'warehouse_map_3d_view',
            'name': f'Gán vị trí 3D - {self.warehouse_map_3d_id.name}',
            'context': {
                'active_id': self.warehouse_map_3d_id.id,
                'move_line_warehouse_map_wizard_id': self.id,
                'default_posx': self.posx,
                'default_posy': self.posy,
                'default_posz': self.posz,
            }
        }
    
    def action_confirm_position(self):
        """Xác nhận và gán vị trí 3D cho move line + cập nhật quant"""
        self.ensure_one()
        
        # Không bắt buộc lot_name vì lot có thể chưa được save từ move_line
        # Chỉ check warehouse_map_3d
        if not self.warehouse_map_3d_id:
            raise UserError(_('Vui lòng chọn sơ đồ kho 3D!'))
        
        # Kiểm tra hợp lệ 3D
        if self.posx < 0 or self.posy < 0 or self.posz < 0:
            raise UserError(_('Vị trí X, Y, Z phải >= 0!'))
        
        # Cấm gán vị trí [0, 0, 0] vì đó là vị trí mặc định (chưa gán)
        if self.posx == 0 and self.posy == 0 and self.posz == 0:
            raise UserError(_('Vị trí [0, 0, 0] là vị trí mặc định! Vui lòng chọn vị trí khác'))
        
        if self.posx >= self.warehouse_map_3d_id.columns:
            raise UserError(_('Vị trí X vượt quá số cột của sơ đồ!'))
        
        if self.posy >= self.warehouse_map_3d_id.rows:
            raise UserError(_('Vị trí Y vượt quá số hàng của sơ đồ!'))
        
        if self.posz >= self.warehouse_map_3d_id.levels:
            raise UserError(_('Vị trí Z vượt quá số tầng của sơ đồ!'))
        
        # Kiểm tra vị trí đã bị chặn không
        blocked = self.env['warehouse.map.blocked.cell.3d'].search([
            ('warehouse_map_3d_id', '=', self.warehouse_map_3d_id.id),
            ('posx', '=', self.posx),
            ('posy', '=', self.posy),
            ('posz', '=', self.posz),
        ], limit=1)
        
        if blocked:
            raise UserError(_(
                f'Vị trí [{self.posx}, {self.posy}, {self.posz}] đang bị chặn!'
            ))
        
        # Kiểm tra vị trí đã bị chiếm không
        existing = self.env['stock.quant'].search([
            ('location_id', 'child_of', self.location_dest_id.id),
            ('posx', '=', self.posx),
            ('posy', '=', self.posy),
            ('posz', '=', self.posz),
            ('display_on_map', '=', True),
            ('quantity', '>', 0),
            ('product_id.tracking', '!=', 'none'),
            # Bỏ qua lot hiện tại để cho phép update
            ('id', '!=', self.move_line_id.id),
        ], limit=1)
        
        if existing:
            raise UserError(_(
                f'Vị trí [{self.posx}, {self.posy}, {self.posz}] đã có lot khác: '
                f'{existing.display_name}'
            ))
        
        # Cập nhật move_line với thông tin vị trí
        update_vals = {
            'posx': self.posx,
            'posy': self.posy,
            'posz': self.posz,
            'position_assigned': True,  # Đánh dấu đã gán vị trí
        }
        
        # Nếu user chọn lot từ dropdown, cập nhật
        if self.lot_id and not self.move_line_id.lot_id:
            update_vals['lot_id'] = self.lot_id.id
        
        self.move_line_id.write(update_vals)
        
        # Cập nhật vị trí quant (sản phẩm đã được tạo từ button_validate)
        quants = self.env['stock.quant'].search([
            ('product_id', '=', self.move_line_id.product_id.id),
            ('lot_id', '=', self.move_line_id.lot_id.id or False),
            ('location_id', '=', self.move_line_id.location_dest_id.id),
        ])
        
        if quants:
            quants.write({
                'posx': self.posx,
                'posy': self.posy,
                'posz': self.posz,
                'display_on_map': True,
            })
        
        return {'type': 'ir.actions.act_window_close'}
    
    @api.model
    def update_position_from_3d_view(self, wizard_id, posx, posy, posz):
        """Cập nhật vị trí từ 3D view và xác nhận"""
        wizard = self.browse(wizard_id)
        wizard.write({
            'posx': posx,
            'posy': posy,
            'posz': posz,
        })
        # Gọi action_confirm_position để xác nhận
        return wizard.action_confirm_position()

