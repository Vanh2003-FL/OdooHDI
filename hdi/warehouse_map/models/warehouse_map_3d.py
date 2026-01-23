# -*- coding: utf-8 -*-

from odoo import models, fields, api


class WarehouseMap3D(models.Model):
    _name = 'warehouse.map.3d'
    _description = 'Warehouse Map 3D Layout'
    _order = 'sequence, name'

    name = fields.Char(string='Tên sơ đồ 3D', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Kho', required=True)
    location_id = fields.Many2one('stock.location', string='Vị trí kho chính', 
                                   domain="[('usage', '=', 'internal')]")
    
    # Kích thước 3D
    rows = fields.Integer(string='Số hàng (Y)', default=10, help='Chiều dài kho')
    columns = fields.Integer(string='Số cột (X)', default=10, help='Chiều rộng kho')
    levels = fields.Integer(string='Số tầng (Z)', default=5, help='Chiều cao kho / Số tầng kệ')
    
    # Spacing configuration cho mỗi chiều
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
    level_spacing_interval = fields.Integer(
        string='Khoảng cách sau mỗi X tầng',
        default=0,
        help='Thêm khoảng trống sau mỗi X tầng (0 = không có). VD: 2 = có khoảng trống sau tầng 2, 4, 6...'
    )
    
    # Kích thước hiển thị
    cell_width = fields.Float(string='Độ rộng ô (m)', default=1.2, help='Độ rộng mỗi ô trong mét')
    cell_depth = fields.Float(string='Độ sâu ô (m)', default=1.0, help='Độ sâu mỗi ô trong mét')
    cell_height = fields.Float(string='Độ cao ô (m)', default=2.5, help='Độ cao mỗi tầng trong mét')
    
    sequence = fields.Integer(string='Thứ tự', default=10)
    active = fields.Boolean(string='Hoạt động', default=True)
    
    # Cài đặt hiển thị
    show_grid = fields.Boolean(string='Hiển thị lưới', default=True)
    show_axes = fields.Boolean(string='Hiển thị trục tọa độ', default=True)
    show_labels = fields.Boolean(string='Hiển thị nhãn', default=True)
    
    # Blocked cells count
    blocked_cell_count = fields.Integer(
        string='Số ô bị chặn',
        compute='_compute_blocked_cell_count'
    )
    
    @api.depends('row_spacing_interval')  # dummy depends
    def _compute_blocked_cell_count(self):
        for record in self:
            record.blocked_cell_count = self.env['warehouse.map.blocked.cell.3d'].search_count([
                ('warehouse_map_3d_id', '=', record.id)
            ])
    
    @api.model
    def get_map_3d_data(self, map_id):
        """Lấy dữ liệu sơ đồ kho 3D với thông tin lot - mỗi lot là 1 vị trí trong không gian 3D"""
        warehouse_map = self.browse(map_id)
        if not warehouse_map:
            return {}
        
        # Lấy tất cả locations con
        domain = [('location_id', 'child_of', warehouse_map.location_id.id),
                  ('usage', '=', 'internal')]
        locations = self.env['stock.location'].search(domain)
        
        # Lấy thông tin quants (lot/serial) - mỗi quant là 1 vị trí trên sơ đồ 3D
        # CHỈ hiển thị sản phẩm có theo dõi lô/serial (tracking != 'none')
        quants = self.env['stock.quant'].search([
            ('location_id', 'in', locations.ids),
            ('quantity', '>', 0),
            ('display_on_map', '=', True),
            ('product_id.tracking', '!=', 'none'),  # Chỉ sản phẩm có tracking
        ])
        
        # Tổ chức dữ liệu theo vị trí x, y, z của quant
        lot_data = {}
        for quant in quants:
            # Lấy vị trí x, y, z từ quant
            x = quant.posx
            y = quant.posy
            z = quant.posz or 0
            
            # Bỏ qua quant nếu chưa có vị trí hợp lệ (phải là số >= 0, không phải None/False)
            if x is None or x is False or y is None or y is False:
                continue
            
            # Tạo key unique cho mỗi vị trí 3D
            position_key = f"{int(x)}_{int(y)}_{int(z)}"
            
            lot_info = {
                'id': quant.id,
                'quant_id': quant.id,
                'product_id': quant.product_id.id,
                'product_name': quant.product_id.display_name,
                'product_code': quant.product_id.default_code or '',
                'lot_id': quant.lot_id.id if quant.lot_id else False,
                'lot_name': quant.lot_id.name if quant.lot_id else 'No Lot',
                'vendor_name': quant.lot_id.name if quant.lot_id else '',
                'quantity': quant.quantity,
                'uom': quant.product_uom_id.name,
                'reserved_quantity': quant.reserved_quantity,
                'available_quantity': quant.quantity - quant.reserved_quantity,
                'location_id': quant.location_id.id,
                'location_name': quant.location_id.name,
                'location_complete_name': quant.location_id.complete_name,
                'in_date': quant.in_date.strftime('%d-%m-%Y') if quant.in_date else False,
                'days_in_stock': quant.days_in_stock,
                'x': x,
                'y': y,
                'z': z,
                'position_key': position_key,
            }
            
            lot_data[position_key] = lot_info
        
        # Lấy blocked cells 3D
        blocked_cells = self.env['warehouse.map.blocked.cell.3d'].get_blocked_cells_dict(warehouse_map.id)
        
        return {
            'id': warehouse_map.id,
            'name': warehouse_map.name,
            'rows': warehouse_map.rows,
            'columns': warehouse_map.columns,
            'levels': warehouse_map.levels,
            'row_spacing_interval': warehouse_map.row_spacing_interval,
            'column_spacing_interval': warehouse_map.column_spacing_interval,
            'level_spacing_interval': warehouse_map.level_spacing_interval,
            'cell_width': warehouse_map.cell_width,
            'cell_depth': warehouse_map.cell_depth,
            'cell_height': warehouse_map.cell_height,
            'show_grid': warehouse_map.show_grid,
            'show_axes': warehouse_map.show_axes,
            'show_labels': warehouse_map.show_labels,
            'warehouse_id': warehouse_map.warehouse_id.id,
            'warehouse_name': warehouse_map.warehouse_id.name,
            'lots': lot_data,
            'blocked_cells': blocked_cells,
        }
    
    def action_view_map_3d(self):
        """Mở view hiển thị sơ đồ kho 3D"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'warehouse_map_3d_view',
            'name': f'Sơ đồ 3D - {self.name}',
            'context': {
                'active_id': self.id,
            }
        }
    
    def action_open_block_cell_3d_wizard(self, posx, posy, posz=0):
        """Mở wizard để chặn/bỏ chặn ô 3D"""
        self.ensure_one()
        return {
            'name': 'Chặn/Bỏ chặn ô 3D',
            'type': 'ir.actions.act_window',
            'res_model': 'block.cell.3d.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_warehouse_map_3d_id': self.id,
                'default_posx': posx,
                'default_posy': posy,
                'default_posz': posz,
            }
        }


class WarehouseMapBlockedCell3D(models.Model):
    _name = 'warehouse.map.blocked.cell.3d'
    _description = 'Blocked Cell in 3D Warehouse Map'
    _rec_name = 'display_name'

    warehouse_map_3d_id = fields.Many2one('warehouse.map.3d', string='Sơ đồ 3D', required=True, ondelete='cascade')
    posx = fields.Integer(string='Vị trí X', required=True)
    posy = fields.Integer(string='Vị trí Y', required=True)
    posz = fields.Integer(string='Vị trí Z (Tầng)', required=True, default=0)
    reason = fields.Text(string='Lý do chặn')
    display_name = fields.Char(string='Tên', compute='_compute_display_name', store=True)
    
    _sql_constraints = [
        ('unique_position_3d', 'unique(warehouse_map_3d_id, posx, posy, posz)', 
         'Vị trí này đã bị chặn trong sơ đồ 3D!')
    ]
    
    @api.depends('warehouse_map_3d_id', 'posx', 'posy', 'posz')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.warehouse_map_3d_id.name} - ({record.posx}, {record.posy}, {record.posz})"
    
    @api.model
    def get_blocked_cells_dict(self, map_3d_id):
        """Trả về dictionary các ô bị chặn với key là 'x_y_z'"""
        blocked_cells = self.search([('warehouse_map_3d_id', '=', map_3d_id)])
        result = {}
        for cell in blocked_cells:
            key = f"{cell.posx}_{cell.posy}_{cell.posz}"
            result[key] = {
                'id': cell.id,
                'posx': cell.posx,
                'posy': cell.posy,
                'posz': cell.posz,
                'reason': cell.reason or '',
            }
        return result
