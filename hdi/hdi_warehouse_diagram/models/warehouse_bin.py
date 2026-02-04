from odoo import models, fields, api
from odoo.exceptions import ValidationError


class WarehouseBin(models.Model):
    _name = 'warehouse.bin'
    _description = 'Warehouse Bin/Location'
    _rec_name = 'name'

    shelves_id = fields.Many2one(
        'warehouse.shelves',
        string='Shelf',
        required=True,
        ondelete='cascade',
        help='Kệ chứa ô này'
    )
    view_id = fields.Many2one(
        'warehouse.view',
        string='Warehouse View',
        related='shelves_id.view_id',
        store=True,
        help='Sơ đồ kho chứa ô này'
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        related='shelves_id.warehouse_id',
        store=True,
        help='Warehouse chứa ô này'
    )
    
    name = fields.Char(
        string='Bin Name/Code',
        required=True,
        help='Mã hoặc tên ô (ví dụ: A1-L1-C1-R1)'
    )
    description = fields.Text(
        string='Description',
        help='Mô tả chi tiết về ô'
    )
    
    # Location information
    level = fields.Integer(
        string='Level/Tier',
        required=True,
        help='Tầng của ô trên kệ'
    )
    column = fields.Integer(
        string='Column',
        required=True,
        help='Cột của ô trên kệ'
    )
    row = fields.Integer(
        string='Row',
        required=True,
        help='Hàng của ô trên kệ'
    )
    
    # Position and dimensions
    x_pos = fields.Float(
        string='X Position',
        required=True,
        default=0.0,
        help='Vị trí X trên sơ đồ (tính bằng mét)'
    )
    y_pos = fields.Float(
        string='Y Position',
        required=True,
        default=0.0,
        help='Vị trí Y trên sơ đồ (tính bằng mét)'
    )
    width = fields.Float(
        string='Width (meters)',
        required=True,
        default=0.5,
        help='Chiều rộng ô (tính bằng mét)'
    )
    height = fields.Float(
        string='Height (meters)',
        required=True,
        default=0.5,
        help='Chiều cao ô (tính bằng mét)'
    )
    depth = fields.Float(
        string='Depth (meters)',
        required=True,
        default=0.5,
        help='Độ sâu ô (tính bằng mét)'
    )
    
    # Capacity
    capacity_units = fields.Integer(
        string='Unit Capacity',
        default=0,
        help='Sức chứa theo đơn vị sản phẩm'
    )
    capacity_weight = fields.Float(
        string='Weight Capacity (kg)',
        default=0.0,
        help='Sức chứa trọng lượng tối đa'
    )
    
    # Status
    status = fields.Selection([
        ('empty', 'Empty - Trống'),
        ('partial', 'Partial - Một phần'),
        ('full', 'Full - Đầy'),
        ('reserved', 'Reserved - Đã được đặt trước'),
        ('blocked', 'Blocked - Bị chặn'),
    ], string='Status', default='empty',
       help='Trạng thái của ô'
    )
    
    # Visual properties
    color = fields.Char(
        string='Color',
        default='#95E1D3',
        help='Màu hiển thị của ô (hex color)'
    )
    bin_type = fields.Selection([
        ('standard', 'Standard Bin - Ô tiêu chuẩn'),
        ('high_value', 'High Value Bin - Ô giá trị cao'),
        ('fragile', 'Fragile Bin - Ô hàng dễ vỡ'),
        ('hazmat', 'Hazmat Bin - Ô hóa chất'),
        ('climate_ctrl', 'Climate Controlled - Ô điều hòa'),
    ], string='Bin Type', default='standard',
       help='Loại ô'
    )
    
    # Product association
    location_id = fields.Many2one(
        'stock.location',
        string='Stock Location',
        help='Liên kết tới vị trí tồn kho trong Odoo'
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Products Assigned',
        help='Sản phẩm được gán cho ô này'
    )
    
    # Attributes
    is_reserved = fields.Boolean(
        string='Is Reserved',
        default=False,
        help='Ô này được đặt trước cho một sản phẩm cụ thể'
    )
    is_hazmat = fields.Boolean(
        string='Contains Hazmat',
        default=False,
        help='Ô chứa vật liệu nguy hiểm'
    )
    requires_cool_storage = fields.Boolean(
        string='Requires Cool Storage',
        default=False,
        help='Ô cần lưu trữ lạnh'
    )
    
    active = fields.Boolean(
        default=True,
        help='Kích hoạt/vô hiệu hóa ô'
    )
    
    @api.constrains('width', 'height', 'depth')
    def _check_dimensions(self):
        for record in self:
            if record.width <= 0 or record.height <= 0 or record.depth <= 0:
                raise ValidationError('Chiều rộng, chiều cao và độ sâu phải lớn hơn 0')
    
    @api.constrains('level', 'column', 'row')
    def _check_location(self):
        for record in self:
            if record.level <= 0 or record.column <= 0 or record.row <= 0:
                raise ValidationError('Level, Column và Row phải lớn hơn 0')
    
    @api.constrains('x_pos', 'y_pos')
    def _check_positions(self):
        for record in self:
            if record.shelves_id and record.view_id:
                if (record.x_pos + record.width > record.view_id.width or
                    record.y_pos + record.height > record.view_id.height or
                    record.x_pos < 0 or record.y_pos < 0):
                    raise ValidationError('Ô vượt quá ranh giới của sơ đồ')
