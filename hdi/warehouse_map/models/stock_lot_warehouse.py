# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockLotWarehouse(models.Model):
    """
    Kế thừa stock.lot để thêm chức năng warehouse mapping.
    Cho phép một lot chứa nhiều sản phẩm thông qua quants.
    """
    _inherit = 'stock.lot'

    # ===== WAREHOUSE MAP POSITION =====
    posx = fields.Integer(
        string='Vị trí X (Cột)',
        help='Vị trí cột trong sơ đồ kho'
    )
    posy = fields.Integer(
        string='Vị trí Y (Hàng)',
        help='Vị trí hàng trong sơ đồ kho'
    )
    posz = fields.Integer(
        string='Vị trí Z (Tầng)',
        default=0,
        help='Tầng/kệ trong sơ đồ kho'
    )
    display_on_map = fields.Boolean(
        string='Hiển thị trên sơ đồ',
        default=False,
        help='Lot này có hiển thị trên sơ đồ kho không'
    )
    has_map_position = fields.Boolean(
        compute='_compute_has_map_position',
        string='Đã có vị trí',
        store=True,
        help='Lot đã được gán vị trí trên sơ đồ'
    )

    # ===== BATCH TYPE (OPTIONAL) =====
    batch_type = fields.Selection([
        ('pallet', 'Pallet'),
        ('lpn', 'LPN'),
        ('container', 'Container'),
        ('loose', 'Loose Items'),
    ], string='Loại lô', default='pallet', help="Loại container chứa lot này")

    # ===== QUANTITY INFO =====
    total_quantity = fields.Float(
        string='Tổng số lượng',
        compute='_compute_total_quantity',
        store=True,
        help='Tổng quantity từ tất cả quants của lot này'
    )
    available_quantity = fields.Float(
        string='Số lượng khả dụng',
        compute='_compute_available_quantity',
        store=True,
    )
    reserved_quantity = fields.Float(
        string='Số lượng đặt',
        compute='_compute_reserved_quantity',
        store=True,
    )

    # ===== PHYSICAL ATTRIBUTES =====
    weight = fields.Float(string='Trọng lượng (kg)', digits='Stock Weight')
    volume = fields.Float(string='Thể tích (m³)', digits=(16, 4))
    height = fields.Float(string='Chiều cao (cm)', digits=(16, 2))
    width = fields.Float(string='Chiều rộng (cm)', digits=(16, 2))
    length = fields.Float(string='Chiều dài (cm)', digits=(16, 2))

    # ===== RELATIONSHIPS =====
    location_id = fields.Many2one(
        'stock.location',
        string='Vị trí hiện tại',
        help='Vị trí kho chứa lot này'
    )
    warehouse_map_id = fields.Many2one(
        'warehouse.map',
        string='Sơ đồ kho',
        help='Sơ đồ kho chứa lot này'
    )

    # ===== IMPORT INFO =====
    import_invoice_number = fields.Char(
        string='Số hóa đơn nhập khẩu',
        help='Số hóa đơn nhập khẩu / Import invoice reference'
    )
    import_packing_list = fields.Char(
        string='Phiếu đóng gói',
        help='Phiếu đóng gói / Packing list reference'
    )
    import_bill_of_lading = fields.Char(
        string='Vận đơn',
        help='Vận đơn / Bill of Lading reference'
    )

    # ===== COMPUTED FIELDS =====
    quant_count = fields.Integer(
        compute='_compute_quant_count',
        string='Số quants'
    )
    product_count = fields.Integer(
        compute='_compute_product_count',
        string='Số loại sản phẩm'
    )

    @api.depends('posx', 'posy', 'posz')
    def _compute_has_map_position(self):
        """Kiểm tra lot đã có vị trí hay chưa"""
        for record in self:
            record.has_map_position = (
                record.posx is not False and
                record.posy is not False and
                record.posz is not False
            )

    @api.depends('quant_ids', 'quant_ids.quantity')
    def _compute_total_quantity(self):
        """Tính tổng quantity từ tất cả quants"""
        for record in self:
            record.total_quantity = sum(
                quant.quantity for quant in record.quant_ids
            )

    @api.depends('quant_ids', 'quant_ids.available_quantity')
    def _compute_available_quantity(self):
        """Tính available quantity"""
        for record in self:
            record.available_quantity = sum(
                quant.available_quantity for quant in record.quant_ids
            )

    @api.depends('quant_ids', 'quant_ids.reserved_quantity')
    def _compute_reserved_quantity(self):
        """Tính reserved quantity"""
        for record in self:
            record.reserved_quantity = sum(
                quant.reserved_quantity for quant in record.quant_ids
            )

    @api.depends('quant_ids')
    def _compute_quant_count(self):
        """Đếm số quants"""
        for record in self:
            record.quant_count = len(record.quant_ids)

    @api.depends('quant_ids', 'quant_ids.product_id')
    def _compute_product_count(self):
        """Đếm số loại sản phẩm"""
        for record in self:
            record.product_count = len(set(
                quant.product_id.id for quant in record.quant_ids
            ))

    def action_view_map(self):
        """Mở view hiển thị sơ đồ kho"""
        self.ensure_one()
        if not self.warehouse_map_id:
            return {'type': 'ir.actions.act_window', 'name': 'No Map', 'res_model': 'ir.ui.view'}
        
        return {
            'type': 'ir.actions.client',
            'tag': 'warehouse_map_view',
            'name': f'Sơ đồ - {self.warehouse_map_id.name}',
            'context': {
                'active_id': self.warehouse_map_id.id,
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
                'default_warehouse_map_id': self.warehouse_map_id.id if self.warehouse_map_id else False,
                'default_posx': posx or self.posx,
                'default_posy': posy or self.posy,
                'default_posz': posz or self.posz,
            }
        }

    def get_lot_data_for_map(self):
        """
        Lấy dữ liệu lot để hiển thị trên sơ đồ kho.
        Dùng thay thế cho batch data.
        """
        self.ensure_one()
        
        # Nếu lot có nhiều sản phẩm, lấy thông tin tổng hợp
        products = self.quant_ids.mapped('product_id')
        
        # Nếu chỉ có 1 sản phẩm, lấy thông tin của nó
        if len(products) == 1:
            product = products[0]
            product_name = product.display_name
            product_code = product.default_code
        else:
            # Nhiều sản phẩm
            product_names = ', '.join([p.display_name for p in products])
            product_name = f"{len(products)} sản phẩm: {product_names}"
            product_code = ''

        return {
            'id': self.id,
            'lot_id': self.id,
            'lot_name': self.name,
            'batch_name': self.name,  # Để tương thích
            'product_id': self.product_id.id if self.product_id else False,
            'product_name': product_name,
            'product_code': product_code,
            'quantity': self.total_quantity,
            'uom': self.product_id.uom_id.name if self.product_id else 'Unit',
            'reserved_quantity': self.reserved_quantity,
            'available_quantity': self.available_quantity,
            'location_id': self.location_id.id,
            'location_name': self.location_id.name if self.location_id else '',
            'location_complete_name': self.location_id.complete_name if self.location_id else '',
            'in_date': self.create_date.strftime('%d-%m-%Y') if self.create_date else False,
            'x': self.posx or 0,
            'y': self.posy or 0,
            'z': self.posz or 0,
            'position_key': f"{self.posx}_{self.posy}_{self.posz}",
            'batch_type': self.batch_type,
            'product_count': self.product_count,
        }
