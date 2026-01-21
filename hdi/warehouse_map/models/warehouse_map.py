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
        warehouse_map = self.browse(map_id)
        if not warehouse_map:
            return {}
        
        # Lấy tất cả locations con
        domain = [('location_id', 'child_of', warehouse_map.location_id.id),
                  ('usage', '=', 'internal')]
        locations = self.env['stock.location'].search(domain)
        
        # Tổ chức dữ liệu theo vị trí
        lot_data = {}
        
        # Lấy thông tin batches có display_on_map
        # Batch cần có ít nhất 1 quant trong locations của warehouse_map
        batches = self.env['hdi.batch'].search([
            ('display_on_map', '=', True),
            ('posx', '!=', False),
            ('posy', '!=', False),
        ])
        
        # Filter batches that have quants in warehouse_map locations
        valid_batches = batches.filtered(
            lambda b: any(q.location_id.id in locations.ids for q in b.quant_ids)
        )
        
        for batch in valid_batches:
            x = batch.posx or 0
            y = batch.posy or 0
            z = batch.posz or 0
            position_key = f"{x}_{y}_{z}"
            
            # Get total quantity and product info from batch's quants
            total_qty = sum(batch.quant_ids.mapped('quantity'))
            reserved_qty = sum(batch.quant_ids.mapped('reserved_quantity'))
            
            # Get product info from first quant (batches should have same product)
            first_quant = batch.quant_ids[0] if batch.quant_ids else None
            
            lot_data[position_key] = {
                'id': batch.id,
                'batch_id': batch.id,
                'batch_name': batch.name,
                'product_id': first_quant.product_id.id if first_quant else False,
                'product_name': first_quant.product_id.display_name if first_quant else 'No Product',
                'product_code': first_quant.product_id.default_code if first_quant else '',
                'lot_id': False,  # Batch không có lot_id cụ thể
                'lot_name': batch.name,  # Hiển thị tên batch
                'quantity': total_qty,
                'uom': first_quant.product_uom_id.name if first_quant else 'Unit',
                'reserved_quantity': reserved_qty,
                'available_quantity': total_qty - reserved_qty,
                'location_id': first_quant.location_id.id if first_quant else False,
                'location_name': first_quant.location_id.name if first_quant else '',
                'location_complete_name': first_quant.location_id.complete_name if first_quant else '',
                'in_date': batch.create_date.strftime('%d-%m-%Y') if batch.create_date else False,
                'days_in_stock': 0,  # TODO: Calculate from batch
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
