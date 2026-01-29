# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockWarehouseExtended(models.Model):
    """Extend stock.warehouse with 3D layout and visualization options"""
    _inherit = 'stock.warehouse'

    layout_id = fields.Many2one(
        'warehouse.layout',
        string='Bố trí 3D',
        ondelete='set null',
        help='Bố trí 3D mặc định cho kho này'
    )
    
    enable_3d_view = fields.Boolean(string='Bật xem 3D', default=True)
    enable_2d_view = fields.Boolean(string='Bật bản đồ 2D', default=True)
    
    default_view = fields.Selection(
        [('3d', 'Xem 3D'), ('2d', 'Bản đồ 2D')],
        string='Xem mặc định',
        default='3d'
    )
    
    max_bins_to_render = fields.Integer(
        string='Số ngăn tối đa hiển thị',
        default=5000,
        help='Giới hạn hiệu suất cho trình xem 3D'
    )
    
    def get_layout_info(self):
        """Return warehouse layout structure"""
        if self.layout_id:
            return self.layout_id.get_layout_info()
        return None
    
    def create_default_layout(self):
        """Auto-create default layout if missing"""
        if not self.layout_id:
            layout = self.env['warehouse.layout'].create({
                'name': f'{self.name} - Default Layout',
                'warehouse_id': self.id,
                'layout_type': '3d'
            })
            self.layout_id = layout
            return layout
        return self.layout_id
