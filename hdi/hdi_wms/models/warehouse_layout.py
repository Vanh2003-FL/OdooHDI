# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import json


class WarehouseLayout(models.Model):
    _name = 'warehouse.layout'
    _description = 'Sơ Đồ Kho 3D'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ===== BASIC INFO =====
    name = fields.Char(
        string='Tên Sơ Đồ',
        required=True,
        tracking=True
    )

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Kho',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True
    )

    description = fields.Text(string='Mô Tả')

    # ===== WAREHOUSE DIMENSIONS =====
    max_x = fields.Integer(
        string='Chiều Dài (X)',
        required=True,
        default=20,
        help="Chiều dài kho (đơn vị mét)"
    )

    max_y = fields.Integer(
        string='Chiều Rộng (Y)',
        required=True,
        default=15,
        help="Chiều rộng kho (đơn vị mét)"
    )

    max_z = fields.Integer(
        string='Chiều Cao (Z)',
        required=True,
        default=5,
        help="Chiều cao kho (đơn vị mét)"
    )

    grid_unit = fields.Selection([
        ('meter', 'Mét'),
        ('feet', 'Feet'),
        ('cm', 'Centimet'),
    ], string='Đơn Vị', default='meter', required=True)

    # ===== STATUS =====
    is_active = fields.Boolean(
        string='Đang Sử Dụng',
        default=True,
        tracking=True
    )

    is_3d_enabled = fields.Boolean(
        string='Bật Hiển Thị 3D',
        default=True,
        help="Cho phép xem sơ đồ 3D interactif"
    )

    # ===== VISUALIZATION DATA =====
    layout_data_json = fields.Text(
        string='Dữ Liệu Layout (JSON)',
        default='{}',
        help="JSON chứa thông tin visualization (internal)"
    )

    location_ids = fields.One2many(
        'stock.location',
        'warehouse_layout_id',
        string='Vị Trí Trong Kho',
        help="Tất cả vị trí được gán cho sơ đồ này"
    )

    location_count = fields.Integer(
        compute='_compute_location_count',
        string='Số Vị Trí'
    )

    batch_count = fields.Integer(
        compute='_compute_batch_count',
        string='Số Lô Hàng'
    )

    # ===== STATISTICS =====
    total_capacity_volume = fields.Float(
        compute='_compute_capacity_stats',
        string='Tổng Dung Lượng (m³)'
    )

    total_used_volume = fields.Float(
        compute='_compute_capacity_stats',
        string='Dung Lượng Đã Dùng (m³)'
    )

    capacity_percentage = fields.Float(
        compute='_compute_capacity_stats',
        string='% Dung Lượng Sử Dụng'
    )

    @api.depends('location_ids')
    def _compute_location_count(self):
        for layout in self:
            layout.location_count = len(layout.location_ids)

    @api.depends('location_ids.batch_ids')
    def _compute_batch_count(self):
        for layout in self:
            batches = self.env['hdi.batch'].search([
                ('location_id', 'in', layout.location_ids.ids),
                ('state', '!=', 'cancel')
            ])
            layout.batch_count = len(batches)

    @api.depends('location_ids.max_volume', 'location_ids.current_volume')
    def _compute_capacity_stats(self):
        for layout in self:
            total_capacity = sum(layout.location_ids.mapped('max_volume'))
            total_used = sum(layout.location_ids.mapped('current_volume'))
            layout.total_capacity_volume = total_capacity
            layout.total_used_volume = total_used
            if total_capacity > 0:
                layout.capacity_percentage = (total_used / total_capacity) * 100
            else:
                layout.capacity_percentage = 0

    def action_open_3d_view(self):
        """Mở view 3D interactif"""
        self.ensure_one()
        
        # Open 3D viewer in new window
        return {
            'type': 'ir.actions.act_url',
            'url': f'/hdi_wms/warehouse_3d/{self.id}',
            'target': 'new',
        }

    def action_view_locations(self):
        """Xem tất cả vị trí trong sơ đồ"""
        self.ensure_one()
        return {
            'name': _('Vị Trí - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.location',
            'view_mode': 'kanban,list,form',
            'domain': [('warehouse_layout_id', '=', self.id)],
            'context': {'default_warehouse_layout_id': self.id},
        }

    def action_view_batches(self):
        """Xem tất cả batch trong sơ đồ"""
        self.ensure_one()
        return {
            'name': _('Lô Hàng - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.batch',
            'view_mode': 'list,form,kanban',
            'domain': [('location_id', 'in', self.location_ids.ids), ('state', '!=', 'cancel')],
        }

    def generate_3d_data(self):
        """
        Tạo dữ liệu JSON cho visualization 3D
        Format: {
            'warehouse': {'id', 'name', 'max_x', 'max_y', 'max_z'},
            'locations': [{'id', 'name', 'x', 'y', 'z', 'color', 'capacity', 'batch_count'}, ...],
            'batches': [{'id', 'name', 'location_id', 'x', 'y', 'z', 'color'}, ...]
        }
        """
        locations_data = []
        for loc in self.location_ids:
            locations_data.append({
                'id': loc.id,
                'name': loc.name,
                'complete_name': loc.complete_name,
                'x': loc.coordinate_x or 0,
                'y': loc.coordinate_y or 0,
                'z': loc.coordinate_z or 0,
                'color': loc.color_code_hex or '#4CAF50',
                'capacity_pct': loc.capacity_percentage or 0,
                'batch_count': loc.batch_count,
                'available_volume': loc.available_volume or 0,
                'is_putable': loc.is_putable,
            })

        batches_data = []
        for batch in self.env['hdi.batch'].search([
            ('location_id', 'in', self.location_ids.ids),
            ('state', '!=', 'cancel')
        ]):
            batches_data.append({
                'id': batch.id,
                'name': batch.name,
                'location_id': batch.location_id.id,
                'location_name': batch.location_id.complete_name,
                'x': batch.location_id.coordinate_x or 0,
                'y': batch.location_id.coordinate_y or 0,
                'z': batch.location_id.coordinate_z or 0,
                'color': '#FF9800',
                'state': batch.state,
            })

        data = {
            'warehouse': {
                'id': self.warehouse_id.id,
                'name': self.warehouse_id.name,
                'max_x': self.max_x,
                'max_y': self.max_y,
                'max_z': self.max_z,
                'unit': self.grid_unit,
            },
            'layout': {
                'id': self.id,
                'name': self.name,
            },
            'locations': locations_data,
            'batches': batches_data,
        }

        self.layout_data_json = json.dumps(data, indent=2, ensure_ascii=False)
        return data

    def refresh_layout_data(self):
        """Cập nhật dữ liệu layout"""
        self.generate_3d_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cập Nhật'),
                'message': _('Đã cập nhật dữ liệu sơ đồ'),
                'type': 'success',
            }
        }
