# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import json


class WarehouseLayout(models.Model):
    """Main warehouse layout structure with 3D/2D configuration"""
    _name = 'warehouse.layout'
    _description = 'Warehouse Layout Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Tên bố trí', required=True, index=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Kho', required=True, ondelete='cascade')
    layout_type = fields.Selection(
        [('2d', 'Bản đồ 2D'), ('3d', 'Xem 3D')],
        string='Loại bố trí',
        default='3d'
    )
    
    # 3D Dimensions
    length = fields.Float(string='Chiều dài (mét)', default=100)
    width = fields.Float(string='Chiều rộng (mét)', default=50)
    height = fields.Float(string='Chiều cao (mét)', default=10)
    
    # 3D Camera Configuration
    camera_x = fields.Float(string='Vị trí Camera X', default=150)
    camera_y = fields.Float(string='Vị trí Camera Y', default=100)
    camera_z = fields.Float(string='Vị trí Camera Z', default=80)
    camera_target_x = fields.Float(string='Mục tiêu X', default=50)
    camera_target_y = fields.Float(string='Mục tiêu Y', default=25)
    camera_target_z = fields.Float(string='Mục tiêu Z', default=5)
    
    # 3D Model File
    model_file = fields.Char(string='Đường dẫn tệp mô hình 3D')
    background_color = fields.Char(string='Màu nền', default='#f0f0f0')
    
    zone_ids = fields.One2many('warehouse.zone', 'layout_id', string='Khu vực')
    aisle_ids = fields.One2many('warehouse.aisle', 'layout_id', string='Lối đi')
    
    created_date = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now)
    updated_date = fields.Datetime(string='Ngày cập nhật')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['updated_date'] = fields.Datetime.now()
        return super().create(vals_list)
    
    def write(self, vals):
        vals['updated_date'] = fields.Datetime.now()
        return super().write(vals)
    
    def get_layout_info(self):
        """Return complete layout structure for 3D viewer"""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.layout_type,
            'dimensions': {
                'length': self.length,
                'width': self.width,
                'height': self.height
            },
            'camera': {
                'position': [self.camera_x, self.camera_y, self.camera_z],
                'target': [self.camera_target_x, self.camera_target_y, self.camera_target_z]
            },
            'zones': [zone.get_zone_info() for zone in self.zone_ids],
            'aisles': [aisle.get_aisle_info() for aisle in self.aisle_ids]
        }


class WarehouseZone(models.Model):
    """Zone types: storage, picking, packing, receiving, shipping, cross-dock"""
    _name = 'warehouse.zone'
    _description = 'Warehouse Zone'
    _order = 'sequence, name'

    name = fields.Char(string='Tên khu vực', required=True)
    layout_id = fields.Many2one('warehouse.layout', string='Bố trí', ondelete='cascade')
    
    zone_type = fields.Selection(
        [('storage', 'Kho lưu trữ'), 
         ('picking', 'Khu lấy hàng'), 
         ('packing', 'Khu đóng gói'),
         ('receiving', 'Khu tiếp nhận'), 
         ('shipping', 'Khu giao hàng'),
         ('crossdock', 'Giao hàng nhanh')],
        string='Loại khu vực',
        required=True
    )
    
    location_ids = fields.Many2many('stock.location', string='Vị trí trong khu vực')
    
    # 3D Position
    pos_x = fields.Float(string='Vị trí X (mét)', default=0)
    pos_y = fields.Float(string='Vị trí Y (mét)', default=0)
    pos_z = fields.Float(string='Vị trí Z (mét)', default=0)
    
    # 3D Dimensions
    length = fields.Float(string='Chiều dài (mét)', default=10)
    width = fields.Float(string='Chiều rộng (mét)', default=10)
    height = fields.Float(string='Chiều cao (mét)', default=3)
    
    zone_color = fields.Char(string='Màu khu vực (Hex)', default='#FF6B6B')
    sequence = fields.Integer(string='Thứ tự', default=10)
    
    aisle_ids = fields.One2many('warehouse.aisle', 'zone_id', string='Aisles in Zone')
    
    def get_zone_info(self):
        """Return zone info for 3D viewer"""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.zone_type,
            'position': [self.pos_x, self.pos_y, self.pos_z],
            'dimensions': [self.length, self.width, self.height],
            'color': self.zone_color,
            'location_count': len(self.location_ids),
            'aisle_count': len(self.aisle_ids)
        }


class WarehouseAisle(models.Model):
    """Aisle/Corridor structure within zone"""
    _name = 'warehouse.aisle'
    _description = 'Warehouse Aisle'
    _order = 'sequence, name'

    name = fields.Char(string='Tên lối đi', required=True)
    layout_id = fields.Many2one('warehouse.layout', string='Bố trí', ondelete='cascade')
    zone_id = fields.Many2one('warehouse.zone', string='Khu vực', ondelete='cascade')
    
    direction = fields.Selection(
        [('ns', 'Bắc-Nam'), ('ew', 'Đông-Tây')],
        string='Hướng',
        default='ns'
    )
    
    # 3D Position
    pos_x = fields.Float(string='Vị trí X (mét)', default=0)
    pos_y = fields.Float(string='Vị trí Y (mét)', default=0)
    pos_z = fields.Float(string='Vị trí Z (mét)', default=0)
    
    # Dimensions
    length = fields.Float(string='Chiều dài (mét)', default=20)
    width = fields.Float(string='Chiều rộng (mét)', default=2)
    height = fields.Float(string='Chiều cao (mét)', default=3)
    
    rack_ids = fields.One2many('warehouse.rack', 'aisle_id', string='Giá kệ trong lối đi')
    sequence = fields.Integer(string='Thứ tự', default=10)
    
    def get_aisle_info(self):
        """Return aisle info for 3D viewer"""
        return {
            'id': self.id,
            'name': self.name,
            'direction': self.direction,
            'position': [self.pos_x, self.pos_y, self.pos_z],
            'dimensions': [self.length, self.width, self.height],
            'rack_count': len(self.rack_ids)
        }


class WarehouseRack(models.Model):
    """Rack structure containing shelves"""
    _name = 'warehouse.rack'
    _description = 'Warehouse Rack'
    _order = 'sequence, name'

    name = fields.Char(string='Tên giá kệ', required=True)
    aisle_id = fields.Many2one('warehouse.aisle', string='Lối đi', ondelete='cascade')
    
    # 3D Position
    pos_x = fields.Float(string='Vị trí X (mét)', default=0)
    pos_y = fields.Float(string='Vị trí Y (mét)', default=0)
    pos_z = fields.Float(string='Vị trí Z (mét)', default=0)
    
    # Dimensions
    width = fields.Float(string='Chiều rộng (mét)', default=1)
    depth = fields.Float(string='Chiều sâu (mét)', default=0.5)
    height = fields.Float(string='Chiều cao (mét)', default=2)
    
    shelf_count = fields.Integer(string='Số tầng', default=4, required=True)
    bin_per_shelf = fields.Integer(string='Số ngăn mỗi tầng', default=4, required=True)
    max_weight_per_shelf = fields.Float(string='Tải trọng tối đa mỗi tầng (kg)', default=500)
    
    shelf_ids = fields.One2many('warehouse.shelf', 'rack_id', string='Các tầng')
    sequence = fields.Integer(string='Thứ tự', default=10)
    
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-create shelves when rack is created"""
        racks = super().create(vals_list)
        for rack in racks:
            rack._create_shelves()
        return racks
    
    def _create_shelves(self):
        """Create shelves for this rack"""
        shelf_height = self.height / self.shelf_count if self.shelf_count > 0 else 0
        for level in range(1, self.shelf_count + 1):
            self.env['warehouse.shelf'].create({
                'rack_id': self.id,
                'shelf_level': level,
                'pos_z': self.pos_z + (level - 1) * shelf_height,
                'max_weight': self.max_weight_per_shelf
            })


class WarehouseShelf(models.Model):
    """Individual shelf level within rack"""
    _name = 'warehouse.shelf'
    _description = 'Warehouse Shelf'
    _order = 'shelf_level'

    rack_id = fields.Many2one('warehouse.rack', string='Giá kệ', ondelete='cascade', required=True)
    shelf_level = fields.Integer(string='Tầng', required=True)
    
    # 3D Position
    pos_z = fields.Float(string='Độ cao Z', default=0)
    
    max_weight = fields.Float(string='Tải trọng tối đa (kg)', default=500)
    
    bin_ids = fields.One2many('warehouse.bin', 'shelf_id', string='Các ngăn trên tầng')
    
    occupied_weight = fields.Float(
        string='Trọng lượng hiện tại (kg)',
        compute='_compute_occupied_weight',
        store=False
    )
    
    utilization_percentage = fields.Float(
        string='Tỷ lệ sử dụng %',
        compute='_compute_utilization',
        store=False
    )
    
    @api.depends('bin_ids', 'bin_ids.total_weight')
    def _compute_occupied_weight(self):
        """Calculate total weight of all bins on this shelf"""
        for shelf in self:
            shelf.occupied_weight = sum(bin.total_weight for bin in shelf.bin_ids)
    
    @api.depends('occupied_weight', 'max_weight')
    def _compute_utilization(self):
        """Calculate utilization percentage"""
        for shelf in self:
            shelf.utilization_percentage = (
                (shelf.occupied_weight / shelf.max_weight * 100) 
                if shelf.max_weight > 0 else 0
            )


class WarehouseBin(models.Model):
    """Individual bin/cell - CRITICAL BRIDGE to stock.location"""
    _name = 'warehouse.bin'
    _description = 'Warehouse Bin'
    _order = 'sequence, name'
    
    # Add SQL constraints and indices for performance
    _sql_constraints = [
        ('unique_location', 'UNIQUE(location_id)', 'Each stock location can only link to one bin!'),
        ('unique_bin_name', 'UNIQUE(name, shelf_id)', 'Bin name must be unique per shelf!')
    ]

    name = fields.Char(string='Mã ngăn', required=True, index=True)
    shelf_id = fields.Many2one('warehouse.shelf', string='Tầng', ondelete='cascade')
    
    # *** CRITICAL LINK: One-to-One relationship with stock.location ***
    location_id = fields.Many2one(
        'stock.location',
        string='Vị trí kho',
        unique=True,
        index=True,
        ondelete='cascade',
        required=True,
        help='Liên kết duy nhất với stock.location cho luồng lấy hàng cốt lõi'
    )
    
    # 3D Position (relative to shelf)
    pos_x = fields.Float(string='Vị trí X (tương đối)', default=0)
    pos_y = fields.Float(string='Vị trí Y (tương đối)', default=0)
    sequence = fields.Integer(string='Thứ tự', default=10)
    
    # Bin Dimensions
    bin_width = fields.Float(string='Chiều rộng (mét)', default=0.5)
    bin_depth = fields.Float(string='Chiều sâu (mét)', default=0.5)
    bin_height = fields.Float(string='Chiều cao (mét)', default=0.3)
    
    max_weight = fields.Float(string='Trọng lượng tối đa (kg)', default=100)
    max_volume = fields.Float(string='Thể tích tối đa (L)', default=50)
    
    # Bin Status (computed from stock.quant)
    bin_status = fields.Selection(
        [('empty', 'Trống'), ('partial', 'Một phần'), ('full', 'Đầy')],
        string='Trạng thái',
        compute='_compute_bin_status',
        store=True
    )
    
    is_pick_bin = fields.Boolean(string='Là ngăn lấy hàng', default=True)
    pick_priority = fields.Selection(
        [('low', 'Thấp'), ('medium', 'Trung bình'), ('high', 'Cao')],
        string='Ưu tiên lấy hàng',
        compute='_compute_pick_priority',
        store=True
    )
    
    # Stock Quantities (computed from core)
    total_quantity = fields.Float(
        string='Tổng số lượng',
        compute='_compute_total_quantity',
        store=False,
        help='Tổng số lượng tất cả quant trong vị trí này'
    )
    
    total_weight = fields.Float(
        string='Tổng trọng lượng (kg)',
        compute='_compute_total_weight',
        store=False,
        help='Tổng (số lượng × trọng lượng sản phẩm)'
    )
    
    pick_frequency = fields.Integer(
        string='Số lần lấy (30 ngày)',
        compute='_compute_pick_frequency',
        store=False,
        help='Số lần lấy hàng trong 30 ngày qua'
    )
    
    last_picked_date = fields.Datetime(
        string='Ngày lấy cuối',
        compute='_compute_last_picked_date',
        store=False
    )
    
    quant_ids = fields.One2many(
        'stock.quant',
        related='location_id.quant_ids',
        string='Quant trong ngăn',
        readonly=True
    )
    
    @api.depends('location_id', 'location_id.quant_ids.quantity')
    def _compute_total_quantity(self):
        """Calculate total quantity by summing stock.quant"""
        for bin in self:
            if bin.location_id:
                quants = self.env['stock.quant'].search([
                    ('location_id', '=', bin.location_id.id)
                ])
                bin.total_quantity = sum(q.quantity for q in quants)
            else:
                bin.total_quantity = 0
    
    @api.depends('total_quantity', 'location_id', 'location_id.quant_ids')
    def _compute_total_weight(self):
        """Calculate total weight: sum(quant.quantity × product.weight)"""
        for bin in self:
            if bin.location_id:
                quants = self.env['stock.quant'].search([
                    ('location_id', '=', bin.location_id.id)
                ])
                bin.total_weight = sum(
                    q.quantity * (q.product_id.weight or 0)
                    for q in quants
                )
            else:
                bin.total_weight = 0
    
    @api.depends('total_quantity', 'max_weight', 'total_weight')
    def _compute_bin_status(self):
        """Status based on weight utilization: empty/partial/full"""
        for bin in self:
            if bin.total_quantity == 0:
                bin.bin_status = 'empty'
            elif bin.total_weight >= bin.max_weight * 0.9:  # >90% = full
                bin.bin_status = 'full'
            else:
                bin.bin_status = 'partial'
    
    @api.depends('pick_frequency')
    def _compute_pick_priority(self):
        """Priority based on pick frequency"""
        for bin in self:
            if bin.pick_frequency > 10:
                bin.pick_priority = 'high'
            elif bin.pick_frequency > 3:
                bin.pick_priority = 'medium'
            else:
                bin.pick_priority = 'low'
    
    @api.depends('location_id')
    def _compute_pick_frequency(self):
        """Count picks in last 30 days from stock.move"""
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=30)
        
        for bin in self:
            if bin.location_id:
                # Use count instead of len for better performance
                bin.pick_frequency = self.env['stock.move'].search_count([
                    ('location_dest_id', '=', bin.location_id.id),
                    ('state', '=', 'done'),
                    ('date_expected', '>=', cutoff_date)
                ])
            else:
                bin.pick_frequency = 0
    
    @api.depends('location_id')
    def _compute_last_picked_date(self):
        """Get the most recent pick date"""
        for bin in self:
            if bin.location_id:
                last_move = self.env['stock.move'].search(
                    [
                        ('location_dest_id', '=', bin.location_id.id),
                        ('state', '=', 'done')
                    ],
                    order='date_expected desc',
                    limit=1
                )
                bin.last_picked_date = last_move.date_expected if last_move else None
            else:
                bin.last_picked_date = None
    
    def get_stock_info(self):
        """Return current stock info for this bin"""
        return {
            'bin_id': self.id,
            'bin_name': self.name,
            'location_id': self.location_id.id,
            'total_quantity': self.total_quantity,
            'total_weight': self.total_weight,
            'status': self.bin_status,
            'pick_frequency_30d': self.pick_frequency,
            'last_picked': self.last_picked_date,
            'quants': [
                {
                    'product_id': q.product_id.id,
                    'product_name': q.product_id.name,
                    'quantity': q.quantity,
                    'lot_id': q.lot_id.name if q.lot_id else None
                }
                for q in self.quant_ids
            ]
        }
    
    def get_picking_moves(self):
        """Get all picking moves to/from this bin (for route planning)"""
        if not self.location_id:
            return []
        
        moves = self.env['stock.move'].search([
            '|',
            ('location_id', '=', self.location_id.id),
            ('location_dest_id', '=', self.location_id.id),
            ('state', 'in', ['assigned', 'partially_available'])
        ])
        
        return [
            {
                'move_id': m.id,
                'picking_id': m.picking_id.id,
                'product': m.product_id.name,
                'qty': m.product_qty,
                'from_location': m.location_id.name,
                'to_location': m.location_dest_id.name
            }
            for m in moves
        ]
