from odoo import models, fields, api
from odoo.exceptions import ValidationError


class WarehouseArea(models.Model):
    _name = 'warehouse.area'
    _description = 'Warehouse Non-Storage Area'
    _rec_name = 'name'

    view_id = fields.Many2one(
        'warehouse.view',
        string='Warehouse View',
        required=True,
        ondelete='cascade',
        help='Sơ đồ kho mà khu vực này thuộc về'
    )
    name = fields.Char(
        string='Area Name',
        required=True,
        help='Tên khu vực (ví dụ: Cửa ra vào, Khu bảo quản, Khu pack hàng)'
    )
    description = fields.Text(
        string='Description',
        help='Mô tả chi tiết về khu vực'
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
        help='Chiều rộng khu vực (tính bằng mét)'
    )
    height = fields.Float(
        string='Height (meters)',
        required=True,
        default=1.0,
        help='Chiều cao khu vực (tính bằng mét)'
    )
    
    # Visual properties
    color = fields.Char(
        string='Color',
        default='#FF6B6B',
        help='Màu hiển thị của khu vực (hex color)'
    )
    area_type = fields.Selection([
        ('entrance', 'Entrance - Cửa ra vào'),
        ('exit', 'Exit - Cửa thoát'),
        ('packing', 'Packing Area - Khu pack hàng'),
        ('receiving', 'Receiving Area - Khu tiếp nhận'),
        ('office', 'Office Area - Khu văn phòng'),
        ('maintenance', 'Maintenance Area - Khu bảo trì'),
        ('restricted', 'Restricted Area - Khu cấm'),
        ('other', 'Other - Khác'),
    ], string='Area Type', required=True, default='other',
       help='Loại khu vực'
    )
    
    is_dangerous = fields.Boolean(
        string='Is Dangerous Area',
        default=False,
        help='Đánh dấu nếu đây là khu vực nguy hiểm'
    )
    
    active = fields.Boolean(
        default=True,
        help='Kích hoạt/vô hiệu hóa khu vực'
    )
    
    @api.constrains('width', 'height')
    def _check_dimensions(self):
        for record in self:
            if record.width <= 0 or record.height <= 0:
                raise ValidationError('Chiều rộng và chiều cao phải lớn hơn 0')
    
    @api.constrains('x_pos', 'y_pos')
    def _check_positions(self):
        for record in self:
            if record.view_id:
                if (record.x_pos + record.width > record.view_id.width or
                    record.y_pos + record.height > record.view_id.height or
                    record.x_pos < 0 or record.y_pos < 0):
                    raise ValidationError('Khu vực vượt quá ranh giới của sơ đồ')
