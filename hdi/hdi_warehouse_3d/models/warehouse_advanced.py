# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class WarehouseCrossDock(models.Model):
    """
    Cross-Dock Operations
    
    Enables direct transfer from receiving to shipping without storage,
    reducing handling time and improving efficiency.
    """
    _name = 'warehouse.crossdock'
    _description = 'Cross-Dock Operation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_date desc, id desc'

    name = fields.Char(string='Mã giao hàng nhanh', required=True, copy=False, 
                       readonly=True, default=lambda self: _('Mới'))
    
    # Relationships
    warehouse_id = fields.Many2one('stock.warehouse', string='Kho', required=True,
                                   tracking=True, ondelete='restrict')
    layout_id = fields.Many2one('warehouse.layout', string='Bố trí',
                                related='warehouse_id.layout_id', store=True)
    
    # Source and destination
    source_picking_id = fields.Many2one('stock.picking', string='Chuyển hàng vào',
                                        domain="[('picking_type_code', '=', 'incoming')]",
                                        tracking=True, ondelete='cascade')
    dest_picking_id = fields.Many2one('stock.picking', string='Chuyển hàng ra',
                                      domain="[('picking_type_code', '=', 'outgoing')]",
                                      tracking=True, ondelete='cascade')
    
    # Cross-dock staging location
    staging_location_id = fields.Many2one('stock.location', string='Vị trí dàn xếp',
                                          domain="[('usage', '=', 'internal')]",
                                          required=True, tracking=True)
    staging_bin_id = fields.Many2one('warehouse.bin', string='Ngăn kho dàn xếp',
                                     domain="[('location_id', '=', staging_location_id)]")
    
    # Products and quantities
    product_id = fields.Many2one('product.product', string='Sản phẩm', required=True,
                                 tracking=True, ondelete='restrict')
    product_uom_id = fields.Many2one('uom.uom', string='Đơn vị',
                                     related='product_id.uom_id', store=True)
    planned_qty = fields.Float(string='Số lượng kế hoạch', default=1.0, required=True,
                               digits='Product Unit of Measure')
    received_qty = fields.Float(string='Số lượng đã nhận', readonly=True,
                                digits='Product Unit of Measure')
    shipped_qty = fields.Float(string='Số lượng đã giao', readonly=True,
                               digits='Product Unit of Measure')
    remaining_qty = fields.Float(string='Số lượng còn lại', compute='_compute_remaining_qty',
                                 store=True, digits='Product Unit of Measure')
    
    # Status and timing
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã xác nhận'),
        ('receiving', 'Đang nhận hàng'),
        ('staged', 'Đã dàn xếp'),
        ('shipping', 'Đang giao hàng'),
        ('done', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', required=True, tracking=True)
    
    scheduled_date = fields.Datetime(string='Ngày dự kiến', required=True,
                                     default=fields.Datetime.now, tracking=True)
    received_date = fields.Datetime(string='Ngày nhận', readonly=True)
    shipped_date = fields.Datetime(string='Ngày giao', readonly=True)
    
    # Time window for cross-dock
    max_staging_hours = fields.Integer(string='Số giờ dàn xếp tối đa', default=24,
                                       help='Số giờ tối đa sản phẩm có thể ở khu dàn xếp')
    staging_deadline = fields.Datetime(string='Hạn chốt dàn xếp', compute='_compute_staging_deadline',
                                       store=True)
    is_overdue = fields.Boolean(string='Quá hạn', compute='_compute_is_overdue')
    
    # Priority
    priority = fields.Selection([
        ('0', 'Thấp'),
        ('1', 'Bình thường'),
        ('2', 'Cao'),
        ('3', 'Khẩn cấp'),
    ], string='Độ ưu tiên', default='1', tracking=True)
    
    # Notes
    note = fields.Text(string='Ghi chú')
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('warehouse.crossdock') or _('New')
        return super().create(vals)
    
    @api.depends('planned_qty', 'received_qty', 'shipped_qty')
    def _compute_remaining_qty(self):
        for record in self:
            record.remaining_qty = record.received_qty - record.shipped_qty
    
    @api.depends('received_date', 'max_staging_hours')
    def _compute_staging_deadline(self):
        for record in self:
            if record.received_date:
                record.staging_deadline = record.received_date + timedelta(hours=record.max_staging_hours)
            else:
                record.staging_deadline = False
    
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_overdue = (
                record.staging_deadline and 
                record.staging_deadline < now and 
                record.state in ['staged', 'shipping']
            )
    
    def action_confirm(self):
        """Confirm cross-dock operation"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft cross-docks can be confirmed.'))
        
        # Validate staging location
        if not self.staging_location_id:
            raise UserError(_('Please select a staging location.'))
        
        self.write({'state': 'confirmed'})
        self.message_post(body=_('Cross-dock operation confirmed.'))
        return True
    
    def action_start_receiving(self):
        """Start receiving phase"""
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(_('Only confirmed cross-docks can start receiving.'))
        
        self.write({'state': 'receiving'})
        self.message_post(body=_('Started receiving goods.'))
        return True
    
    def action_receive(self, qty=None):
        """Mark goods as received"""
        self.ensure_one()
        
        if qty is None:
            qty = self.planned_qty
        
        if qty > self.planned_qty:
            raise UserError(_('Cannot receive more than planned quantity.'))
        
        self.write({
            'received_qty': qty,
            'received_date': fields.Datetime.now(),
            'state': 'staged',
        })
        
        self.message_post(body=_('Received %.2f %s. Goods staged at %s.') % (
            qty, self.product_uom_id.name, self.staging_location_id.name
        ))
        
        # Auto-trigger shipping if outbound is ready
        if self.dest_picking_id and self.dest_picking_id.state == 'assigned':
            self.action_start_shipping()
        
        return True
    
    def action_start_shipping(self):
        """Start shipping phase"""
        self.ensure_one()
        if self.state != 'staged':
            raise UserError(_('Only staged goods can start shipping.'))
        
        if self.received_qty <= 0:
            raise UserError(_('No goods available to ship.'))
        
        self.write({'state': 'shipping'})
        self.message_post(body=_('Started shipping goods.'))
        return True
    
    def action_ship(self, qty=None):
        """Mark goods as shipped"""
        self.ensure_one()
        
        if qty is None:
            qty = self.received_qty
        
        if qty > self.received_qty:
            raise UserError(_('Cannot ship more than received quantity.'))
        
        self.write({
            'shipped_qty': self.shipped_qty + qty,
            'shipped_date': fields.Datetime.now(),
            'state': 'done' if self.shipped_qty + qty >= self.received_qty else 'shipping',
        })
        
        self.message_post(body=_('Shipped %.2f %s.') % (qty, self.product_uom_id.name))
        
        return True
    
    def action_cancel(self):
        """Cancel cross-dock operation"""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_('Cannot cancel completed cross-dock.'))
        
        self.write({'state': 'cancelled'})
        self.message_post(body=_('Cross-dock operation cancelled.'))
        return True
    
    @api.model
    def _cron_check_overdue(self):
        """Check for overdue cross-docks and send alerts"""
        overdue_records = self.search([
            ('state', 'in', ['staged', 'shipping']),
            ('staging_deadline', '<', fields.Datetime.now()),
        ])
        
        for record in overdue_records:
            # Send notification
            record.activity_schedule(
                'mail.mail_activity_data_warning',
                user_id=record.warehouse_id.user_id.id or self.env.user.id,
                summary=_('Overdue Cross-Dock: %s') % record.name,
                note=_('Product %s has been in staging for more than %d hours. Please expedite shipping.') % (
                    record.product_id.name, record.max_staging_hours
                )
            )
        
        return True


class BinMovement(models.Model):
    """
    Bin Movement Tracking
    
    Track all movements of products between bins for analytics and traceability.
    """
    _name = 'warehouse.bin.movement'
    _description = 'Bin Movement History'
    _order = 'movement_date desc, id desc'
    _rec_name = 'product_id'

    # Product and quantity
    product_id = fields.Many2one('product.product', string='Product', required=True,
                                 ondelete='restrict', index=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure',
                                     related='product_id.uom_id', store=True)
    quantity = fields.Float(string='Quantity', required=True, digits='Product Unit of Measure')
    
    # Source and destination
    source_bin_id = fields.Many2one('warehouse.bin', string='Source Bin', 
                                    ondelete='restrict', index=True)
    dest_bin_id = fields.Many2one('warehouse.bin', string='Destination Bin', required=True,
                                  ondelete='restrict', index=True)
    
    source_location_id = fields.Many2one('stock.location', string='Source Location',
                                         related='source_bin_id.location_id', store=True)
    dest_location_id = fields.Many2one('stock.location', string='Dest Location',
                                       related='dest_bin_id.location_id', store=True)
    
    # Movement details
    movement_type = fields.Selection([
        ('putaway', 'Putaway'),
        ('pick', 'Pick'),
        ('transfer', 'Internal Transfer'),
        ('replenishment', 'Replenishment'),
        ('consolidation', 'Consolidation'),
        ('relocation', 'Relocation'),
    ], string='Movement Type', required=True, index=True)
    
    movement_date = fields.Datetime(string='Movement Date', required=True,
                                    default=fields.Datetime.now, index=True)
    
    # Related documents
    picking_id = fields.Many2one('stock.picking', string='Related Picking', ondelete='set null')
    move_line_id = fields.Many2one('stock.move.line', string='Related Move Line', ondelete='set null')
    
    # User and warehouse
    user_id = fields.Many2one('res.users', string='Moved By', default=lambda self: self.env.user,
                              required=True, ondelete='restrict')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',
                                   related='dest_bin_id.shelf_id.rack_id.aisle_id.zone_id.layout_id.warehouse_id',
                                   store=True, index=True)
    
    # Distance traveled (computed from bin positions)
    distance = fields.Float(string='Distance (m)', compute='_compute_distance', store=True,
                           help='Distance between source and destination bins')
    
    # Notes
    note = fields.Text(string='Notes')
    
    @api.depends('source_bin_id.pos_x', 'source_bin_id.pos_y', 'source_bin_id.shelf_id.pos_z',
                 'dest_bin_id.pos_x', 'dest_bin_id.pos_y', 'dest_bin_id.shelf_id.pos_z')
    def _compute_distance(self):
        """Calculate 3D distance between bins"""
        for record in self:
            if record.source_bin_id and record.dest_bin_id:
                dx = record.dest_bin_id.pos_x - record.source_bin_id.pos_x
                dy = record.dest_bin_id.pos_y - record.source_bin_id.pos_y
                # Use shelf's z position since bins don't have pos_z
                dz = (record.dest_bin_id.shelf_id.pos_z or 0) - (record.source_bin_id.shelf_id.pos_z or 0)
                record.distance = (dx**2 + dy**2 + dz**2) ** 0.5
            else:
                record.distance = 0.0
    
    @api.model
    def create_movement(self, product, qty, source_bin, dest_bin, movement_type, picking=None):
        """Helper method to create movement records"""
        return self.create({
            'product_id': product.id,
            'quantity': qty,
            'source_bin_id': source_bin.id if source_bin else False,
            'dest_bin_id': dest_bin.id,
            'movement_type': movement_type,
            'picking_id': picking.id if picking else False,
            'movement_date': fields.Datetime.now(),
        })
    
    @api.model
    def get_movement_analytics(self, warehouse_id, date_from=None, date_to=None):
        """Get movement analytics for a warehouse"""
        domain = [('warehouse_id', '=', warehouse_id)]
        
        if date_from:
            domain.append(('movement_date', '>=', date_from))
        if date_to:
            domain.append(('movement_date', '<=', date_to))
        
        movements = self.search(domain)
        
        return {
            'total_movements': len(movements),
            'total_distance': sum(movements.mapped('distance')),
            'avg_distance': sum(movements.mapped('distance')) / len(movements) if movements else 0,
            'by_type': {
                mt: len(movements.filtered(lambda m: m.movement_type == mt))
                for mt in dict(self._fields['movement_type'].selection).keys()
            },
            'busiest_bins': self._get_busiest_bins(movements, limit=10),
        }
    
    def _get_busiest_bins(self, movements, limit=10):
        """Get bins with most movements"""
        bin_counts = {}
        for move in movements:
            if move.source_bin_id:
                bin_counts[move.source_bin_id.id] = bin_counts.get(move.source_bin_id.id, 0) + 1
            if move.dest_bin_id:
                bin_counts[move.dest_bin_id.id] = bin_counts.get(move.dest_bin_id.id, 0) + 1
        
        sorted_bins = sorted(bin_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        return [
            {
                'bin_id': bin_id,
                'bin_name': self.env['warehouse.bin'].browse(bin_id).name,
                'movement_count': count,
            }
            for bin_id, count in sorted_bins
        ]


class PickToToteOperation(models.Model):
    """
    Pick-to-Tote Workflow
    
    Batch picking workflow where multiple orders are picked into totes,
    then sorted and packed at a packing station.
    """
    _name = 'warehouse.pick.tote'
    _description = 'Pick-to-Tote Operation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Tote Reference', required=True, copy=False,
                       readonly=True, default=lambda self: _('New'))
    
    # Tote identification
    tote_barcode = fields.Char(string='Tote Barcode', required=True, index=True,
                               help='Physical tote barcode for scanning')
    tote_color = fields.Char(string='Tote Color', help='Physical tote color for visual identification')
    
    # Assignment
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True,
                                   ondelete='restrict')
    picker_id = fields.Many2one('res.users', string='Assigned Picker', tracking=True,
                                domain="[('share', '=', False)]", ondelete='restrict')
    wave_id = fields.Many2one('warehouse.pick.wave', string='Pick Wave',
                              help='Group of totes picked together')
    
    # Orders in tote
    picking_ids = fields.Many2many('stock.picking', string='Pickings',
                                   domain="[('picking_type_code', '=', 'outgoing')]")
    picking_count = fields.Integer(string='Order Count', compute='_compute_picking_count')
    
    # Tote lines (products picked into tote)
    line_ids = fields.One2many('warehouse.pick.tote.line', 'tote_id', string='Tote Lines')
    line_count = fields.Integer(string='Line Count', compute='_compute_line_count')
    total_qty = fields.Float(string='Total Quantity', compute='_compute_total_qty',
                             digits='Product Unit of Measure')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('picking', 'Picking'),
        ('picked', 'Picked'),
        ('sorting', 'Sorting'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, index=True)
    
    # Timestamps
    assigned_date = fields.Datetime(string='Assigned Date')
    picking_start_date = fields.Datetime(string='Picking Started')
    picked_date = fields.Datetime(string='Picked Date')
    sorted_date = fields.Datetime(string='Sorted Date')
    
    # Metrics
    pick_duration = fields.Float(string='Pick Duration (min)', compute='_compute_durations', store=True)
    sort_duration = fields.Float(string='Sort Duration (min)', compute='_compute_durations', store=True)
    
    # Packing station
    packing_station_id = fields.Many2one('warehouse.packing.station', string='Packing Station',
                                         help='Station where tote is sorted and packed')
    
    note = fields.Text(string='Notes')
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('warehouse.pick.tote') or _('New')
        return super().create(vals)
    
    @api.depends('picking_ids')
    def _compute_picking_count(self):
        for record in self:
            record.picking_count = len(record.picking_ids)
    
    @api.depends('line_ids')
    def _compute_line_count(self):
        for record in self:
            record.line_count = len(record.line_ids)
    
    @api.depends('line_ids.picked_qty')
    def _compute_total_qty(self):
        for record in self:
            record.total_qty = sum(record.line_ids.mapped('picked_qty'))
    
    @api.depends('picking_start_date', 'picked_date', 'sorted_date')
    def _compute_durations(self):
        for record in self:
            if record.picking_start_date and record.picked_date:
                delta = record.picked_date - record.picking_start_date
                record.pick_duration = delta.total_seconds() / 60.0
            else:
                record.pick_duration = 0.0
            
            if record.picked_date and record.sorted_date:
                delta = record.sorted_date - record.picked_date
                record.sort_duration = delta.total_seconds() / 60.0
            else:
                record.sort_duration = 0.0
    
    def action_assign_picker(self, picker):
        """Assign tote to a picker"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft totes can be assigned.'))
        
        self.write({
            'picker_id': picker.id,
            'state': 'assigned',
            'assigned_date': fields.Datetime.now(),
        })
        
        self.message_post(body=_('Tote assigned to %s.') % picker.name)
        return True
    
    def action_start_picking(self):
        """Start picking process"""
        self.ensure_one()
        if self.state != 'assigned':
            raise UserError(_('Only assigned totes can start picking.'))
        
        self.write({
            'state': 'picking',
            'picking_start_date': fields.Datetime.now(),
        })
        
        self.message_post(body=_('Picking started.'))
        return True
    
    def action_confirm_picked(self):
        """Confirm all items picked"""
        self.ensure_one()
        if self.state != 'picking':
            raise UserError(_('Only picking totes can be confirmed.'))
        
        # Validate all lines picked
        unpicked = self.line_ids.filtered(lambda l: l.picked_qty < l.planned_qty)
        if unpicked:
            raise UserError(_('Some items are not fully picked: %s') % 
                          ', '.join(unpicked.mapped('product_id.name')))
        
        self.write({
            'state': 'picked',
            'picked_date': fields.Datetime.now(),
        })
        
        self.message_post(body=_('All items picked. Ready for sorting.'))
        return True
    
    def action_start_sorting(self):
        """Start sorting at packing station"""
        self.ensure_one()
        if self.state != 'picked':
            raise UserError(_('Only picked totes can start sorting.'))
        
        if not self.packing_station_id:
            raise UserError(_('Please assign a packing station first.'))
        
        self.write({'state': 'sorting'})
        self.message_post(body=_('Sorting started at %s.') % self.packing_station_id.name)
        return True
    
    def action_complete(self):
        """Complete sorting and packing"""
        self.ensure_one()
        if self.state != 'sorting':
            raise UserError(_('Only sorting totes can be completed.'))
        
        self.write({
            'state': 'done',
            'sorted_date': fields.Datetime.now(),
        })
        
        self.message_post(body=_('Tote sorted and completed.'))
        return True


class PickToToteLine(models.Model):
    """Tote Line Items"""
    _name = 'warehouse.pick.tote.line'
    _description = 'Pick-to-Tote Line'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    tote_id = fields.Many2one('warehouse.pick.tote', string='Tote', required=True,
                              ondelete='cascade', index=True)
    
    # Product
    product_id = fields.Many2one('product.product', string='Product', required=True,
                                 ondelete='restrict')
    product_uom_id = fields.Many2one('uom.uom', string='Unit', related='product_id.uom_id')
    
    # Quantities
    planned_qty = fields.Float(string='Planned Qty', required=True, digits='Product Unit of Measure')
    picked_qty = fields.Float(string='Picked Qty', digits='Product Unit of Measure')
    remaining_qty = fields.Float(string='Remaining', compute='_compute_remaining_qty',
                                 digits='Product Unit of Measure')
    
    # Source bin
    source_bin_id = fields.Many2one('warehouse.bin', string='Pick From Bin',
                                    domain="[('bin_status', 'in', ['partial', 'full'])]")
    
    # Order allocation (which order this item belongs to)
    picking_id = fields.Many2one('stock.picking', string='Order', required=True,
                                 ondelete='cascade')
    
    # Status
    is_picked = fields.Boolean(string='Picked', compute='_compute_is_picked', store=True)
    
    @api.depends('planned_qty', 'picked_qty')
    def _compute_remaining_qty(self):
        for line in self:
            line.remaining_qty = line.planned_qty - line.picked_qty
    
    @api.depends('picked_qty', 'planned_qty')
    def _compute_is_picked(self):
        for line in self:
            line.is_picked = line.picked_qty >= line.planned_qty


class PickWave(models.Model):
    """Pick Wave - Group of totes picked together"""
    _name = 'warehouse.pick.wave'
    _description = 'Pick Wave'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Wave Reference', required=True, copy=False,
                       default=lambda self: _('New'))
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    
    tote_ids = fields.One2many('warehouse.pick.tote', 'wave_id', string='Totes')
    tote_count = fields.Integer(string='Tote Count', compute='_compute_tote_count')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('released', 'Released'),
        ('done', 'Done'),
    ], string='Status', default='draft', tracking=True)
    
    scheduled_date = fields.Datetime(string='Scheduled Date', default=fields.Datetime.now)
    
    @api.depends('tote_ids')
    def _compute_tote_count(self):
        for wave in self:
            wave.tote_count = len(wave.tote_ids)


class PackingStation(models.Model):
    """Packing Station for sorting totes"""
    _name = 'warehouse.packing.station'
    _description = 'Packing Station'

    name = fields.Char(string='Station Name', required=True)
    code = fields.Char(string='Station Code', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    location_id = fields.Many2one('stock.location', string='Location', required=True)
    
    active = fields.Boolean(string='Active', default=True)
    user_ids = fields.Many2many('res.users', string='Authorized Users')
