from odoo import models, fields, api
from odoo.exceptions import ValidationError


class WarehouseShelves(models.Model):
    _name = 'warehouse.shelves'
    _description = 'Warehouse Shelves/Racks'
    _rec_name = 'name'

    view_id = fields.Many2one(
        'warehouse.view',
        string='Warehouse View',
        required=True,
        ondelete='cascade',
        help='Sơ đồ kho mà kệ này thuộc về'
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        related='view_id.warehouse_id',
        store=True,
        help='Warehouse chứa kệ này'
    )
    name = fields.Char(
        string='Shelf Name',
        required=True,
        help='Tên kệ (ví dụ: A1, A2, B1, ...)'
    )
    description = fields.Text(
        string='Description',
        help='Mô tả chi tiết về kệ'
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
        default=1.0,
        help='Chiều rộng kệ (tính bằng mét)'
    )
    height = fields.Float(
        string='Height (meters)',
        required=True,
        default=1.0,
        help='Chiều cao kệ (tính bằng mét)'
    )
    depth = fields.Float(
        string='Depth (meters)',
        required=True,
        default=0.5,
        help='Độ sâu kệ (tính bằng mét)'
    )
    
    # Shelf configuration
    rows = fields.Integer(
        string='Rows',
        required=True,
        default=4,
        help='Số hàng trên kệ'
    )
    columns = fields.Integer(
        string='Columns',
        required=True,
        default=3,
        help='Số cột trên kệ'
    )
    levels = fields.Integer(
        string='Levels/Tiers',
        required=True,
        default=4,
        help='Số tầng của kệ'
    )
    
    # Capacity
    capacity_weight = fields.Float(
        string='Weight Capacity (kg)',
        default=0.0,
        help='Sức chứa trọng lượng tối đa của kệ'
    )
    max_height = fields.Float(
        string='Max Height (cm)',
        default=0.0,
        help='Chiều cao tối đa của sản phẩm trên kệ'
    )
    
    # Visual properties
    color = fields.Char(
        string='Color',
        default='#4ECDC4',
        help='Màu hiển thị của kệ (hex color)'
    )
    shelf_type = fields.Selection([
        ('standard', 'Standard Shelves - Kệ tiêu chuẩn'),
        ('heavy_duty', 'Heavy Duty Shelves - Kệ nặng'),
        ('pallet_rack', 'Pallet Rack - Kệ pallet'),
        ('cantilever', 'Cantilever Shelves - Kệ nước ngoài'),
        ('mobile', 'Mobile Shelves - Kệ di động'),
    ], string='Shelf Type', required=True, default='standard',
       help='Loại kệ'
    )
    
    # Relationships
    bin_ids = fields.One2many(
        'warehouse.bin',
        'shelves_id',
        string='Bins',
        help='Các ô lưu trữ trên kệ này'
    )
    bin_count = fields.Integer(
        string='Total Bins',
        compute='_compute_bin_count',
        store=True,
        help='Tổng số ô trên kệ'
    )
    
    active = fields.Boolean(
        default=True,
        help='Kích hoạt/vô hiệu hóa kệ'
    )
    
    @api.depends('bin_ids')
    def _compute_bin_count(self):
        for record in self:
            record.bin_count = len(record.bin_ids)
    
    @api.constrains('width', 'height', 'depth', 'rows', 'columns', 'levels')
    def _check_dimensions(self):
        for record in self:
            if record.width <= 0 or record.height <= 0 or record.depth <= 0:
                raise ValidationError('Chiều rộng, chiều cao và độ sâu phải lớn hơn 0')
            if record.rows <= 0 or record.columns <= 0 or record.levels <= 0:
                raise ValidationError('Số hàng, cột và tầng phải lớn hơn 0')
    
    @api.constrains('x_pos', 'y_pos')
    def _check_positions(self):
        for record in self:
            if record.view_id:
                if (record.x_pos + record.width > record.view_id.width or
                    record.y_pos + record.height > record.view_id.height or
                    record.x_pos < 0 or record.y_pos < 0):
                    raise ValidationError('Kệ vượt quá ranh giới của sơ đồ')
    
    @api.model
    def create(self, vals):
        record = super().create(vals)
        # Tự động tạo bins dựa trên cấu hình
        record._create_default_bins()
        return record
    
    def _create_default_bins(self):
        """Tự động tạo bins dựa trên số hàng, cột và tầng"""
        self.ensure_one()
        bin_width = self.width / self.columns if self.columns > 0 else self.width
        bin_height = self.height / self.levels if self.levels > 0 else self.height
        bin_depth = self.depth / self.rows if self.rows > 0 else self.depth
        
        bins_to_create = []
        for level in range(self.levels):
            for col in range(self.columns):
                for row in range(self.rows):
                    bin_name = f"{self.name}-L{level+1}C{col+1}R{row+1}"
                    x_pos = self.x_pos + (col * bin_width)
                    y_pos = self.y_pos + (level * bin_height)
                    
                    bins_to_create.append({
                        'shelves_id': self.id,
                        'name': bin_name,
                        'level': level + 1,
                        'column': col + 1,
                        'row': row + 1,
                        'x_pos': x_pos,
                        'y_pos': y_pos,
                        'width': bin_width,
                        'height': bin_height,
                        'depth': bin_depth,
                    })
        
        if bins_to_create:
            self.env['warehouse.bin'].create(bins_to_create)
