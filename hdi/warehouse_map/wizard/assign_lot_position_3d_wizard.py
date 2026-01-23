# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class AssignLotPosition3DWizard(models.TransientModel):
    _name = 'assign.lot.position.3d.wizard'
    _description = 'Wizard để gán tọa độ 3D cho Lot/Serial'

    warehouse_map_3d_id = fields.Many2one('warehouse.map.3d', string='Sơ đồ 3D', required=True)
    quant_id = fields.Many2one('stock.quant', string='Quant')
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial')
    product_id = fields.Many2one('product.product', string='Sản phẩm', required=True)
    location_id = fields.Many2one('stock.location', string='Vị trí', required=True)
    
    # Tọa độ 3D
    posx = fields.Integer(string='Vị trí X (Cột)', required=True, default=0)
    posy = fields.Integer(string='Vị trí Y (Hàng)', required=True, default=0)
    posz = fields.Integer(string='Vị trí Z (Tầng)', required=True, default=0)
    
    display_on_map = fields.Boolean(string='Hiển thị trên sơ đồ', default=True)
    
    @api.onchange('warehouse_map_3d_id')
    def _onchange_warehouse_map_3d(self):
        """Giới hạn location theo warehouse của map"""
        if self.warehouse_map_3d_id:
            domain = [('location_id', 'child_of', self.warehouse_map_3d_id.location_id.id),
                     ('usage', '=', 'internal')]
            return {'domain': {'location_id': domain}}
    
    @api.onchange('posx', 'posy', 'posz')
    def _onchange_position(self):
        """Kiểm tra xem vị trí đã bị chiếm chưa"""
        if self.warehouse_map_3d_id and self.posx is not False and self.posy is not False and self.posz is not False:
            # Kiểm tra blocked cell
            blocked = self.env['warehouse.map.blocked.cell.3d'].search([
                ('warehouse_map_3d_id', '=', self.warehouse_map_3d_id.id),
                ('posx', '=', self.posx),
                ('posy', '=', self.posy),
                ('posz', '=', self.posz),
            ], limit=1)
            
            if blocked:
                return {
                    'warning': {
                        'title': 'Cảnh báo',
                        'message': f'Vị trí ({self.posx}, {self.posy}, {self.posz}) đang bị chặn!'
                    }
                }
            
            # Kiểm tra quant khác đã chiếm vị trí này chưa
            existing_quant = self.env['stock.quant'].search([
                ('location_id', 'child_of', self.warehouse_map_3d_id.location_id.id),
                ('posx', '=', self.posx),
                ('posy', '=', self.posy),
                ('posz', '=', self.posz),
                ('quantity', '>', 0),
                ('id', '!=', self.quant_id.id if self.quant_id else False),
            ], limit=1)
            
            if existing_quant:
                return {
                    'warning': {
                        'title': 'Cảnh báo',
                        'message': f'Vị trí ({self.posx}, {self.posy}, {self.posz}) đã có sản phẩm:\n'
                                 f'{existing_quant.product_id.name} - Lot: {existing_quant.lot_id.name if existing_quant.lot_id else "N/A"}'
                    }
                }
    
    def action_assign_position(self):
        """Gán tọa độ 3D cho quant/lot"""
        self.ensure_one()
        
        # Validate coordinates
        if self.posx < 0 or self.posy < 0 or self.posz < 0:
            raise UserError('Tọa độ không được âm!')
        
        if self.posx >= self.warehouse_map_3d_id.columns:
            raise UserError(f'Tọa độ X không được vượt quá {self.warehouse_map_3d_id.columns - 1}')
        
        if self.posy >= self.warehouse_map_3d_id.rows:
            raise UserError(f'Tọa độ Y không được vượt quá {self.warehouse_map_3d_id.rows - 1}')
        
        if self.posz >= self.warehouse_map_3d_id.levels:
            raise UserError(f'Tọa độ Z không được vượt quá {self.warehouse_map_3d_id.levels - 1}')
        
        # Kiểm tra blocked cell
        blocked = self.env['warehouse.map.blocked.cell.3d'].search([
            ('warehouse_map_3d_id', '=', self.warehouse_map_3d_id.id),
            ('posx', '=', self.posx),
            ('posy', '=', self.posy),
            ('posz', '=', self.posz),
        ], limit=1)
        
        if blocked:
            raise UserError(f'Không thể gán vị trí ({self.posx}, {self.posy}, {self.posz}) vì ô này đang bị chặn!')
        
        # Tìm hoặc tạo quant
        if self.quant_id:
            # Cập nhật quant hiện tại
            self.quant_id.write({
                'posx': self.posx,
                'posy': self.posy,
                'posz': self.posz,
                'display_on_map': self.display_on_map,
            })
        else:
            # Tìm quant theo product, location và lot
            domain = [
                ('product_id', '=', self.product_id.id),
                ('location_id', '=', self.location_id.id),
            ]
            if self.lot_id:
                domain.append(('lot_id', '=', self.lot_id.id))
            else:
                domain.append(('lot_id', '=', False))
            
            quants = self.env['stock.quant'].search(domain)
            
            if quants:
                # Cập nhật tất cả quant tìm được
                quants.write({
                    'posx': self.posx,
                    'posy': self.posy,
                    'posz': self.posz,
                    'display_on_map': self.display_on_map,
                })
            else:
                raise UserError('Không tìm thấy quant để cập nhật. Vui lòng kiểm tra lại thông tin.')
        
        return {'type': 'ir.actions.act_window_close'}
