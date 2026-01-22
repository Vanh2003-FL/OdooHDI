# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MoveLineWarehouseMapWizard(models.TransientModel):
    """Wizard để gán vị trí sản phẩm/lot từ bảng nhập kho"""
    _name = 'move.line.warehouse.map.wizard'
    _description = 'Gán vị trí sản phẩm/Lot trên sơ đồ kho'

    move_line_id = fields.Many2one('stock.move.line', string='Move Line', required=True, readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Phiếu nhập kho', required=True, readonly=True)
    
    # Thông tin sản phẩm
    product_id = fields.Many2one('product.product', string='Sản phẩm', 
                                  related='move_line_id.product_id', readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial', 
                             related='move_line_id.lot_id', readonly=True)
    quantity = fields.Float(string='Số lượng', 
                           related='move_line_id.qty_done', readonly=True)
    location_dest_id = fields.Many2one('stock.location', string='Vị trí đích', 
                                        related='move_line_id.location_dest_id', readonly=True)
    
    # Chọn sơ đồ kho
    warehouse_map_id = fields.Many2one('warehouse.map', string='Sơ đồ kho', required=True,
                                        domain="[('location_id', 'parent_of', location_dest_id)]")
    
    # Vị trí trên sơ đồ
    posx = fields.Integer(string='Vị trí X (Cột)', required=True)
    posy = fields.Integer(string='Vị trí Y (Hàng)', required=True)
    posz = fields.Integer(string='Vị trí Z (Tầng)', default=0)
    
    # Chế độ xem
    view_mode = fields.Selection([
        ('form', 'Nhập tọa độ trực tiếp'),
        ('map', 'Chọn từ sơ đồ kho'),
    ], string='Cách chọn vị trí', default='form')
    
    @api.onchange('warehouse_map_id')
    def _onchange_warehouse_map(self):
        """Reset position when changing warehouse map"""
        self.posx = 0
        self.posy = 0
        self.posz = 0
    
    def action_open_warehouse_map(self):
        """Mở sơ đồ kho để chọn vị trí"""
        self.ensure_one()
        
        if not self.warehouse_map_id:
            raise UserError(_('Vui lòng chọn sơ đồ kho trước!'))
        
        # Mở warehouse map view
        return {
            'type': 'ir.actions.client',
            'tag': 'warehouse_map_view',
            'name': f'Gán vị trí - {self.warehouse_map_id.name}',
            'context': {
                'active_id': self.warehouse_map_id.id,
                'move_line_warehouse_map_wizard_id': self.id,
                'default_posx': self.posx,
                'default_posy': self.posy,
                'default_posz': self.posz,
            }
        }
    
    def action_confirm_position(self):
        """Xác nhận và gán vị trí cho move line"""
        self.ensure_one()
        
        if not self.warehouse_map_id:
            raise UserError(_('Vui lòng chọn sơ đồ kho!'))
        
        # Kiểm tra hợp lệ
        if self.posx < 0 or self.posy < 0:
            raise UserError(_('Vị trí X, Y phải >= 0!'))
        
        if self.posx >= self.warehouse_map_id.columns:
            raise UserError(_('Vị trí X vượt quá số cột của sơ đồ!'))
        
        if self.posy >= self.warehouse_map_id.rows:
            raise UserError(_('Vị trí Y vượt quá số hàng của sơ đồ!'))
        
        # Kiểm tra vị trí đã bị chiếm không
        existing = self.env['stock.quant'].search([
            ('location_id', 'child_of', self.location_dest_id.id),
            ('posx', '=', self.posx),
            ('posy', '=', self.posy),
            ('posz', '=', self.posz),
            ('display_on_map', '=', True),
            ('quantity', '>', 0),
            ('product_id.tracking', '!=', 'none'),
        ], limit=1)
        
        if existing:
            raise UserError(_(
                f'Vị trí [{self.posx}, {self.posy}, {self.posz}] đã có lot khác: '
                f'{existing.display_name}'
            ))
        
        # Cập nhật move_line với thông tin vị trí
        self.move_line_id.write({
            'posx': self.posx,
            'posy': self.posy,
            'posz': self.posz,
        })
        
        return {'type': 'ir.actions.act_window_close'}

