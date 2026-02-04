from odoo import models, fields, api
from odoo.exceptions import ValidationError


class WarehouseView(models.Model):
    _name = 'warehouse.view'
    _description = 'Warehouse Diagram View'
    _rec_name = 'name'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        required=True,
        ondelete='cascade',
        help='Warehouse liên kết với sơ đồ'
    )
    name = fields.Char(
        string='View Name',
        required=True,
        help='Tên của sơ đồ kho'
    )
    description = fields.Text(
        string='Description',
        help='Mô tả chi tiết về sơ đồ kho'
    )
    width = fields.Float(
        string='Width (meters)',
        required=True,
        default=10.0,
        help='Chiều rộng sơ đồ kho (tính bằng mét)'
    )
    height = fields.Float(
        string='Height (meters)',
        required=True,
        default=10.0,
        help='Chiều cao sơ đồ kho (tính bằng mét)'
    )
    scale = fields.Float(
        string='Scale (pixels/meter)',
        required=True,
        default=50.0,
        help='Tỷ lệ hiển thị (pixel trên mét)'
    )
    
    # Relationships
    area_ids = fields.One2many(
        'warehouse.area',
        'view_id',
        string='Areas',
        help='Các khu vực không lưu trữ'
    )
    shelves_ids = fields.One2many(
        'warehouse.shelves',
        'view_id',
        string='Shelves',
        help='Các kệ lưu trữ'
    )
    
    active = fields.Boolean(
        default=True,
        help='Kích hoạt/vô hiệu hóa sơ đồ'
    )
    created_date = fields.Datetime(
        string='Created Date',
        default=lambda self: fields.Datetime.now(),
        readonly=True
    )
    
    @api.constrains('width', 'height', 'scale')
    def _check_dimensions(self):
        for record in self:
            if record.width <= 0 or record.height <= 0:
                raise ValidationError('Chiều rộng và chiều cao phải lớn hơn 0')
            if record.scale <= 0:
                raise ValidationError('Tỷ lệ phải lớn hơn 0')
