# -*- coding: utf-8 -*-

from odoo import models, fields, api


class WarehouseMap(models.Model):
    _name = 'warehouse.map'
    _description = 'Warehouse Map Layout'
    _order = 'sequence, name'

    name = fields.Char(string='Tên sơ đồ', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Kho', required=True)
    location_id = fields.Many2one('stock.location', string='Vị trí kho chính', 
                                   domain="[('usage', '=', 'internal')]")
    rows = fields.Integer(string='Số hàng', default=10)
    columns = fields.Integer(string='Số cột', default=10)
    
    # Spacing configuration
    row_spacing_interval = fields.Integer(
        string='Khoảng cách sau mỗi X hàng',
        default=0,
        help='Thêm khoảng trống sau mỗi X hàng (0 = không có). VD: 5 = có khoảng trống sau hàng 5, 10, 15...'
    )
    column_spacing_interval = fields.Integer(
        string='Khoảng cách sau mỗi X cột',
        default=0,
        help='Thêm khoảng trống sau mỗi X cột (0 = không có). VD: 3 = có khoảng trống sau cột 3, 6, 9...'
    )
    
    sequence = fields.Integer(string='Thứ tự', default=10)
    active = fields.Boolean(string='Hoạt động', default=True)
    
    # Blocked cells count
    blocked_cell_count = fields.Integer(
        string='Số ô bị chặn',
        compute='_compute_blocked_cell_count'
    )
    
    @api.depends('row_spacing_interval')  # dummy depends
    def _compute_blocked_cell_count(self):
        for record in self:
            record.blocked_cell_count = self.env['warehouse.map.blocked.cell'].search_count([
                ('warehouse_map_id', '=', record.id)
            ])
    
    @api.model
    def get_map_data(self, map_id):
        """
        Lấy dữ liệu sơ đồ kho từ stock.lot có vị trí map.
        
        Thay thế batch bằng lot để dùng chung 1 model.
        stock.lot giờ có thể chứa nhiều sản phẩm qua quants.
        """
        import logging
        _logger = logging.getLogger(__name__)
        
        warehouse_map = self.browse(map_id)
        if not warehouse_map:
            return {}
        
        _logger.info(f"[GetMapData] Warehouse map: {warehouse_map.name}")
        
        # Tổ chức dữ liệu theo vị trí
        lot_data = {}
        
        # Lấy thông tin lots có display_on_map (stock.lot custom)
        # Lưu ý: posx/posy có thể = 0, phải check is not False
        lots = self.env['stock.lot'].search([
            ('display_on_map', '=', True),
            ('warehouse_map_id', '=', warehouse_map.id),
        ])
        
        # Filter in Python to handle posx/posy = 0 case
        lots = lots.filtered(lambda l: l.posx is not False and l.posy is not False)
        
        _logger.info(f"[GetMapData] Found {len(lots)} lots to display")
        
        for lot in lots:
            x = lot.posx or 0
            y = lot.posy or 0
            z = lot.posz or 0
            position_key = f"{x}_{y}_{z}"
            
            _logger.info(f"[GetMapData] Processing lot: {lot.name} at position [{x}, {y}, {z}]")
            
            # Lấy thông tin lot để hiển thị
            lot_map_data = lot.get_lot_data_for_map()
            lot_map_data['warehouse_map_id'] = warehouse_map.id
            
            lot_data[position_key] = lot_map_data
        
        # Lấy blocked cells
        blocked_cells = self.env['warehouse.map.blocked.cell'].get_blocked_cells_dict(warehouse_map.id)
        
        return {
            'id': warehouse_map.id,
            'name': warehouse_map.name,
            'rows': warehouse_map.rows,
            'columns': warehouse_map.columns,
            'row_spacing_interval': warehouse_map.row_spacing_interval,
            'column_spacing_interval': warehouse_map.column_spacing_interval,
            'warehouse_id': warehouse_map.warehouse_id.id,
            'warehouse_name': warehouse_map.warehouse_id.name,
            'lots': lot_data,
            'blocked_cells': blocked_cells,
        }
    
    def action_view_map(self):
        """Mở view hiển thị sơ đồ kho"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'warehouse_map_view',
            'name': f'Sơ đồ - {self.name}',
            'context': {
                'active_id': self.id,
            }
        }
    
    def action_open_block_cell_wizard(self, posx, posy, posz=0):
        """Mở wizard để chặn/bỏ chặn ô"""
        self.ensure_one()
        return {
            'name': 'Chặn/Bỏ chặn ô',
            'type': 'ir.actions.act_window',
            'res_model': 'block.cell.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_warehouse_map_id': self.id,
                'default_posx': posx,
                'default_posy': posy,
                'default_posz': posz,
            }
        }
