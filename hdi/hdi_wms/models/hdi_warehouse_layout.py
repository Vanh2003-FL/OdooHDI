# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HdiWarehouseLayout(models.Model):
    """Warehouse Layout/Diagram with Grid Visualization"""
    _name = 'hdi.warehouse.layout'
    _description = 'Warehouse Layout with Grid System'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'warehouse_id, name'

    # ===== BASIC INFO =====
    name = fields.Char(
        string='Tên sơ đồ',
        required=True,
        tracking=True,
    )

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Kho',
        required=True,
        ondelete='cascade',
        tracking=True,
        help="Kho được áp dụng sơ đồ này"
    )

    active = fields.Boolean(
        string='Hoạt động',
        default=True,
        tracking=True,
    )

    description = fields.Text(
        string='Mô tả',
        help="Mô tả sơ đồ kho"
    )

    # ===== GRID CONFIGURATION =====
    rows = fields.Integer(
        string='Số hàng',
        required=True,
        default=5,
        help="Số hàng trong sơ đồ (Y axis)"
    )

    columns = fields.Integer(
        string='Số cột',
        required=True,
        default=10,
        help="Số cột trong sơ đồ (X axis)"
    )

    levels = fields.Integer(
        string='Số tầng',
        required=True,
        default=3,
        help="Số tầng chứa hàng (Z axis) - mô phỏng kệ 3D"
    )

    cell_width = fields.Float(
        string='Chiều rộng ô (px)',
        default=100,
        help="Chiều rộng của mỗi ô trong sơ đồ (pixels)"
    )

    cell_height = fields.Float(
        string='Chiều cao ô (px)',
        default=80,
        help="Chiều cao của mỗi ô trong sơ đồ (pixels)"
    )

    # ===== ZONES & SECTIONS =====
    zone_ids = fields.One2many(
        'hdi.warehouse.zone',
        'layout_id',
        string='Khu vực',
        help="Các khu vực trong sơ đồ (ví dụ: Zone A, B, C, ...)"
    )

    location_grid_ids = fields.One2many(
        'hdi.warehouse.location.grid',
        'layout_id',
        string='Vị trí Grid',
        help="Các vị trí trong lưới"
    )

    # ===== STATISTICS =====
    total_slots = fields.Integer(
        string='Tổng slot',
        compute='_compute_statistics',
        help="Tổng số slot trong sơ đồ"
    )

    occupied_slots = fields.Integer(
        string='Slot đang dùng',
        compute='_compute_statistics',
        help="Số slot đang có hàng"
    )

    empty_slots = fields.Integer(
        string='Slot trống',
        compute='_compute_statistics',
        help="Số slot còn trống"
    )

    utilization_rate = fields.Float(
        string='Tỷ lệ sử dụng (%)',
        compute='_compute_statistics',
        digits=(5, 2),
        help="Phần trăm slot đang được sử dụng"
    )

    # ===== TIMESTAMPS =====
    created_date = fields.Datetime(
        string='Ngày tạo',
        default=fields.Datetime.now,
        readonly=True,
    )

    updated_date = fields.Datetime(
        string='Ngày cập nhật',
        default=fields.Datetime.now,
        readonly=True,
    )

    @api.constrains('rows', 'columns', 'levels')
    def _check_grid_dimensions(self):
        """Validate grid dimensions"""
        for layout in self:
            if layout.rows < 1 or layout.columns < 1 or layout.levels < 1:
                raise ValidationError(
                    _('Số hàng, cột, tầng phải >= 1')
                )
            if (layout.rows * layout.columns * layout.levels) > 10000:
                raise ValidationError(
                    _('Tổng số ô không được vượt quá 10,000')
                )

    @api.depends('location_grid_ids', 'location_grid_ids.batch_id')
    def _compute_statistics(self):
        """Calculate warehouse utilization statistics"""
        for layout in self:
            total = layout.rows * layout.columns * layout.levels
            layout.total_slots = total
            occupied = len(layout.location_grid_ids.filtered(lambda g: g.batch_id))
            layout.occupied_slots = occupied
            layout.empty_slots = total - occupied
            layout.utilization_rate = (occupied / total * 100) if total > 0 else 0.0

    def action_generate_grid(self):
        """Auto-generate grid slots based on dimensions"""
        self.ensure_one()
        # Delete existing grid
        self.location_grid_ids.unlink()

        # Generate new grid
        grid_ids = []
        for level in range(1, self.levels + 1):
            for row in range(1, self.rows + 1):
                for col in range(1, self.columns + 1):
                    grid_ids.append({
                        'layout_id': self.id,
                        'row': row,
                        'column': col,
                        'level': level,
                        'position_code': f'L{level}-R{row}-C{col}',
                    })

        if grid_ids:
            self.env['hdi.warehouse.location.grid'].create(grid_ids)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Grid Generated'),
                'message': _('%d slots generated') % len(grid_ids),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_layout(self):
        """Open warehouse layout visualization"""
        self.ensure_one()
        return {
            'name': _('Sơ đồ Kho - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.warehouse.layout',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(self.env.ref('hdi_wms.view_warehouse_layout_form').id, 'form')],
            'target': 'fullscreen',
        }

    def action_view_grids(self):
        """View all grid slots"""
        self.ensure_one()
        return {
            'name': _('Grid Slots - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.warehouse.location.grid',
            'view_mode': 'list,form',
            'domain': [('layout_id', '=', self.id)],
            'context': {'default_layout_id': self.id},
        }

    @api.model
    def create(self, vals):
        result = super().create(vals)
        # Auto-generate grid when creating
        if vals.get('rows') and vals.get('columns') and vals.get('levels'):
            result.action_generate_grid()
        return result


class HdiWarehouseZone(models.Model):
    """Warehouse Zones (A, B, C sections)"""
    _name = 'hdi.warehouse.zone'
    _description = 'Warehouse Zone'
    _order = 'name'

    name = fields.Char(
        string='Tên khu vực',
        required=True,
        help="Zone A, Zone B, Zone C, ..."
    )

    layout_id = fields.Many2one(
        'hdi.warehouse.layout',
        string='Sơ đồ',
        required=True,
        ondelete='cascade',
    )

    zone_type = fields.Selection([
        ('general', 'Kho chung'),
        ('reserved', 'Kho dành riêng'),
        ('hazmat', 'Khu nguy hiểm'),
        ('cold', 'Kho lạnh'),
        ('quarantine', 'Khu cách ly'),
    ], string='Loại khu vực', default='general')

    description = fields.Text(string='Mô tả')

    color = fields.Char(
        string='Màu hiển thị',
        default='#3498db',
        help="Mã màu hex (ví dụ: #3498db)"
    )

    # Zone boundaries (for visualization)
    start_row = fields.Integer(string='Hàng bắt đầu')
    end_row = fields.Integer(string='Hàng kết thúc')
    start_column = fields.Integer(string='Cột bắt đầu')
    end_column = fields.Integer(string='Cột kết thúc')

    location_count = fields.Integer(
        string='Số vị trí',
        compute='_compute_location_count',
    )

    @api.depends('layout_id.location_grid_ids')
    def _compute_location_count(self):
        for zone in self:
            zone.location_count = len(zone.layout_id.location_grid_ids.filtered(
                lambda g: zone.start_row <= g.row <= zone.end_row and
                zone.start_column <= g.column <= zone.end_column
            ))
