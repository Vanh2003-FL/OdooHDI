# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HdiWarehouseLocationGrid(models.Model):
    """Grid Location in Warehouse Layout - Individual Slot/Cell"""
    _name = 'hdi.warehouse.location.grid'
    _description = 'Warehouse Grid Location'
    _order = 'layout_id, level, row, column'

    # ===== GRID POSITION =====
    layout_id = fields.Many2one(
        'hdi.warehouse.layout',
        string='Sơ đồ',
        required=True,
        ondelete='cascade',
        tracking=True,
    )

    position_code = fields.Char(
        string='Mã vị trí',
        required=True,
        unique='layout_id',
        tracking=True,
        help="Unique position code (L1-R2-C3)"
    )

    row = fields.Integer(
        string='Hàng',
        required=True,
        help="Row number (Y-axis)"
    )

    column = fields.Integer(
        string='Cột',
        required=True,
        help="Column number (X-axis)"
    )

    level = fields.Integer(
        string='Tầng',
        required=True,
        default=1,
        help="Level/height (Z-axis) - for 3D visualization"
    )

    # ===== INVENTORY DATA =====
    batch_id = fields.Many2one(
        'hdi.batch',
        string='Lô hàng',
        ondelete='set null',
        tracking=True,
        help="Batch/LPN currently stored here"
    )

    location_id = fields.Many2one(
        'stock.location',
        string='Vị trí kho',
        ondelete='set null',
        help="Link to core stock.location"
    )

    quant_ids = fields.One2many(
        'stock.quant',
        'grid_location_id',
        string='Quants',
        help="Inventory quants in this location"
    )

    # ===== SLOT PROPERTIES =====
    capacity_type = fields.Selection([
        ('weight', 'Giới hạn trọng lượng'),
        ('volume', 'Giới hạn thể tích'),
        ('count', 'Giới hạn số lượng'),
        ('unlimited', 'Không giới hạn'),
    ], string='Loại giới hạn', default='unlimited')

    max_weight = fields.Float(
        string='Trọng lượng tối đa (kg)',
        digits=(16, 2),
        help="Maximum weight capacity"
    )

    max_volume = fields.Float(
        string='Thể tích tối đa (m³)',
        digits=(16, 4),
        help="Maximum volume capacity"
    )

    max_items = fields.Integer(
        string='Số lượng tối đa',
        help="Maximum item count"
    )

    # ===== CURRENT STATUS =====
    current_weight = fields.Float(
        string='Trọng lượng hiện tại (kg)',
        compute='_compute_current_capacity',
        digits=(16, 2),
    )

    current_volume = fields.Float(
        string='Thể tích hiện tại (m³)',
        compute='_compute_current_capacity',
        digits=(16, 4),
    )

    current_items = fields.Integer(
        string='Số lượng hiện tại',
        compute='_compute_current_capacity',
    )

    utilization_percent = fields.Float(
        string='% Sử dụng',
        compute='_compute_current_capacity',
        digits=(5, 2),
    )

    is_available = fields.Boolean(
        string='Có sẵn',
        compute='_compute_availability',
        help="Is slot available for new batches"
    )

    status = fields.Selection([
        ('empty', 'Trống'),
        ('partial', 'Một phần'),
        ('full', 'Đầy'),
        ('reserved', 'Dành riêng'),
        ('blocked', 'Bị chặn'),
    ], string='Trạng thái', compute='_compute_status', store=True)

    # ===== ZONE & PREFERENCES =====
    zone_id = fields.Many2one(
        'hdi.warehouse.zone',
        string='Khu vực',
        compute='_compute_zone',
        store=True,
        help="Zone this location belongs to"
    )

    product_family = fields.Char(
        string='Họ sản phẩm',
        help="Reserved for specific product family (optional)"
    )

    is_reserved = fields.Boolean(
        string='Dành riêng',
        default=False,
        help="Is this slot reserved for specific product?"
    )

    reserved_product_ids = fields.Many2many(
        'product.product',
        string='Sản phẩm dành riêng',
        help="Products allowed in this reserved slot"
    )

    # ===== HISTORY & AUDIT =====
    last_batch_id = fields.Many2one(
        'hdi.batch',
        string='Lô trước đó',
        readonly=True,
        help="Previous batch stored here"
    )

    last_change_date = fields.Datetime(
        string='Thời gian thay đổi',
        readonly=True,
        help="When was this slot last updated"
    )

    notes = fields.Text(
        string='Ghi chú',
        help="Additional notes about this location"
    )

    @api.constrains('row', 'column', 'level', 'layout_id')
    def _check_position(self):
        """Validate position within layout dimensions"""
        for grid in self:
            if not (1 <= grid.row <= grid.layout_id.rows):
                raise ValidationError(
                    _('Row must be between 1 and %d') % grid.layout_id.rows
                )
            if not (1 <= grid.column <= grid.layout_id.columns):
                raise ValidationError(
                    _('Column must be between 1 and %d') % grid.layout_id.columns
                )
            if not (1 <= grid.level <= grid.layout_id.levels):
                raise ValidationError(
                    _('Level must be between 1 and %d') % grid.layout_id.levels
                )

    @api.depends('batch_id', 'max_weight', 'max_volume', 'max_items')
    def _compute_current_capacity(self):
        """Calculate current capacity usage"""
        for grid in self:
            if not grid.batch_id:
                grid.current_weight = 0
                grid.current_volume = 0
                grid.current_items = 0
                grid.utilization_percent = 0
                continue

            batch = grid.batch_id
            grid.current_weight = batch.weight or 0
            grid.current_volume = batch.volume or 0
            grid.current_items = int(batch.total_quantity or 0)

            # Calculate utilization percent based on capacity type
            if grid.capacity_type == 'weight' and grid.max_weight > 0:
                grid.utilization_percent = (grid.current_weight / grid.max_weight) * 100
            elif grid.capacity_type == 'volume' and grid.max_volume > 0:
                grid.utilization_percent = (grid.current_volume / grid.max_volume) * 100
            elif grid.capacity_type == 'count' and grid.max_items > 0:
                grid.utilization_percent = (grid.current_items / grid.max_items) * 100
            else:
                grid.utilization_percent = 0

    @api.depends('batch_id', 'is_reserved', 'utilization_percent')
    def _compute_availability(self):
        """Check if slot is available for new batches"""
        for grid in self:
            # Not available if occupied or reserved
            if grid.batch_id:
                grid.is_available = False
                continue

            if grid.is_reserved:
                grid.is_available = False
                continue

            # Check capacity
            if grid.capacity_type != 'unlimited':
                if grid.utilization_percent >= 100:
                    grid.is_available = False
                    continue

            grid.is_available = True

    @api.depends('batch_id', 'utilization_percent')
    def _compute_status(self):
        """Determine slot status"""
        for grid in self:
            if not grid.batch_id:
                grid.status = 'empty'
            elif grid.utilization_percent >= 100:
                grid.status = 'full'
            elif grid.is_reserved:
                grid.status = 'reserved'
            else:
                grid.status = 'partial'

    @api.depends('row', 'column', 'level', 'layout_id')
    def _compute_zone(self):
        """Assign zone based on position"""
        for grid in self:
            zone = self.env['hdi.warehouse.zone'].search([
                ('layout_id', '=', grid.layout_id.id),
                ('start_row', '<=', grid.row),
                ('end_row', '>=', grid.row),
                ('start_column', '<=', grid.column),
                ('end_column', '>=', grid.column),
            ], limit=1)
            grid.zone_id = zone.id if zone else False

    def action_place_batch(self):
        """Place a batch in this grid location"""
        self.ensure_one()
        if not self.is_available:
            raise UserError(_('This slot is not available'))

        return {
            'name': _('Place Batch - %s') % self.position_code,
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.batch.placement.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_grid_location_id': self.id,
                'default_location_id': self.location_id.id,
            }
        }

    def action_move_batch(self):
        """Move batch to another location"""
        self.ensure_one()
        if not self.batch_id:
            raise UserError(_('No batch in this location'))

        return {
            'name': _('Move Batch - %s') % self.batch_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.batch.relocation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_from_grid_location_id': self.id,
                'default_batch_id': self.batch_id.id,
            }
        }

    def action_pick_batch(self):
        """Create picking from this batch"""
        self.ensure_one()
        if not self.batch_id:
            raise UserError(_('No batch in this location'))

        batch = self.batch_id
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': batch.location_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })

        return {
            'name': batch.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'view_mode': 'form',
        }

    def action_view_batch_details(self):
        """View batch details"""
        self.ensure_one()
        if not self.batch_id:
            raise UserError(_('No batch in this location'))

        return {
            'name': self.batch_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.batch',
            'res_id': self.batch_id.id,
            'view_mode': 'form',
        }

    def action_view_location_details(self):
        """View location details"""
        self.ensure_one()
        return {
            'name': _('Location Details - %s') % self.position_code,
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.warehouse.location.grid',
            'res_id': self.id,
            'view_mode': 'form',
        }

    def action_transfer_warehouse(self):
        """Transfer batch to another warehouse"""
        self.ensure_one()
        if not self.batch_id:
            raise UserError(_('No batch in this location'))

        return {
            'name': _('Transfer Warehouse - %s') % self.batch_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.batch.warehouse.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_batch_id': self.batch_id.id,
                'default_from_warehouse_id': self.layout_id.warehouse_id.id,
            }
        }

    def write(self, vals):
        """Track history when batch changes"""
        for grid in self:
            if 'batch_id' in vals and vals['batch_id'] != grid.batch_id.id:
                # Save previous batch
                if grid.batch_id:
                    vals['last_batch_id'] = grid.batch_id.id
                vals['last_change_date'] = fields.Datetime.now()

        return super().write(vals)
