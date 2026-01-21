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
        """Lấy dữ liệu sơ đồ kho với thông tin batches - chỉ hiển thị batch"""
        import logging
        _logger = logging.getLogger(__name__)
        
        warehouse_map = self.browse(map_id)
        if not warehouse_map:
            return {}
        
        # Lấy tất cả locations con
        domain = [('location_id', 'child_of', warehouse_map.location_id.id),
                  ('usage', '=', 'internal')]
        locations = self.env['stock.location'].search(domain)
        
        _logger.info(f"[GetMapData] Warehouse map: {warehouse_map.name}, Location: {warehouse_map.location_id.name}")
        _logger.info(f"[GetMapData] Found {len(locations)} child locations")
        
        # Tổ chức dữ liệu theo vị trí
        lot_data = {}
        
        # Lấy thông tin batches có display_on_map
        # KHÔNG lọc theo location vì batch có thể chưa có quants
        # Lưu ý: posx/posy có thể = 0, phải check is not False
        batches = self.env['hdi.batch'].search([
            ('display_on_map', '=', True),
        ])
        
        # Filter in Python to handle posx/posy = 0 case
        batches = batches.filtered(lambda b: b.posx is not False and b.posy is not False)
        
        _logger.info(f"[GetMapData] Found {len(batches)} batches to display")
        
        for batch in batches:
            x = batch.posx or 0
            y = batch.posy or 0
            z = batch.posz or 0
            position_key = f"{x}_{y}_{z}"
            
            _logger.info(f"[GetMapData] Processing batch: {batch.name} at position [{x}, {y}, {z}]")
            
            # CHỈ DÙNG THÔNG TIN TỪ BATCH - KHÔNG DÙNG QUANTS
            product = batch.product_id
            
            # Dùng total_quantity của batch (từ compute) hoặc planned_quantity
            total_qty = batch.total_quantity or batch.planned_quantity or 0
            reserved_qty = batch.reserved_quantity or 0
            available_qty = batch.available_quantity or 0
            
            lot_data[position_key] = {
                'id': batch.id,
                'batch_id': batch.id,
                'batch_name': batch.name,
                'product_id': product.id if product else False,
                'product_name': product.display_name if product else 'No Product',
                'product_code': product.default_code if product else '',
                'lot_id': False,
                'lot_name': batch.name,
                'quantity': total_qty,
                'uom': product.uom_id.name if product else 'Unit',
                'reserved_quantity': reserved_qty,
                'available_quantity': available_qty,
                'location_id': batch.location_id.id,
                'location_name': batch.location_id.name,
                'location_complete_name': batch.location_id.complete_name,
                'in_date': batch.create_date.strftime('%d-%m-%Y') if batch.create_date else False,
                'days_in_stock': 0,
                'x': x,
                'y': y,
                'z': z,
                'position_key': position_key,
            }
        
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
