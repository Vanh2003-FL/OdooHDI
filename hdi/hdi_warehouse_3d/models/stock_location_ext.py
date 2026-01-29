# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockLocationExtended(models.Model):
    """Extend stock.location with 3D position and warehouse.bin reference"""
    _inherit = 'stock.location'

    # Link to warehouse.bin for 3D visualization
    bin_id = fields.Many2one('warehouse.bin', string='Ngăn kho', ondelete='set null')
    
    # 3D Coordinates (replaces integer-based posx/posy/posz from core)
    loc_x = fields.Float(string='Vị trí X (mét)', default=0)
    loc_y = fields.Float(string='Vị trí Y (mét)', default=0)
    loc_z = fields.Float(string='Vị trí Z (mét)', default=0)
    
    # Dimensions
    loc_width = fields.Float(string='Chiều rộng (mét)', default=1)
    loc_length = fields.Float(string='Chiều dài (mét)', default=1)
    loc_height = fields.Float(string='Chiều cao (mét)', default=1)
    
    # Visual properties
    loc_color = fields.Char(string='Màu (Hex)', default='#4A90E2')
    loc_icon = fields.Char(string='Biểu tượng', default='📦')
    
    # Capacity
    max_weight = fields.Float(string='Trọng lượng tối đa (kg)', default=1000)
    max_volume = fields.Float(string='Thể tích tối đa (L)', default=1000)
    
    def get_3d_info(self):
        """Return 3D position and dimensions for visualization"""
        return {
            'location_id': self.id,
            'location_name': self.name,
            'position': [self.loc_x, self.loc_y, self.loc_z],
            'dimensions': [self.loc_width, self.loc_length, self.loc_height],
            'color': self.loc_color,
            'icon': self.loc_icon,
            'max_weight': self.max_weight,
            'max_volume': self.max_volume,
        }
    
    def get_bin_info(self):
        """Return linked bin's stock information"""
        if self.bin_id:
            return self.bin_id.get_stock_info()
        return None
