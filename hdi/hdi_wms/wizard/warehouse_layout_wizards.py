# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HdiBatchPlacementWizard(models.TransientModel):
    """Wizard to place batch in grid location"""
    _name = 'hdi.batch.placement.wizard'
    _description = 'Batch Placement Wizard'

    # ===== LOCATION INFO =====
    grid_location_id = fields.Many2one(
        'hdi.warehouse.location.grid',
        string='Grid Location',
        required=True,
    )

    layout_id = fields.Many2one(
        'hdi.warehouse.layout',
        related='grid_location_id.layout_id',
        readonly=True,
    )

    position_code = fields.Char(
        string='Position Code',
        related='grid_location_id.position_code',
        readonly=True,
    )

    location_id = fields.Many2one(
        'stock.location',
        string='Stock Location',
    )

    # ===== BATCH SELECTION =====
    batch_id = fields.Many2one(
        'hdi.batch',
        string='Batch / LPN',
        required=True,
        domain="[('state', '=', 'draft'), ('picking_id.picking_type_code', '=', 'incoming')]",
        help="Select batch to place in this location"
    )

    batch_type = fields.Selection(
        related='batch_id.batch_type',
        readonly=True,
    )

    batch_product = fields.Char(
        related='batch_id.product_id.name',
        readonly=True,
    )

    batch_quantity = fields.Float(
        related='batch_id.total_quantity',
        readonly=True,
    )

    batch_weight = fields.Float(
        related='batch_id.weight',
        readonly=True,
    )

    # ===== LOCATION CAPACITY CHECK =====
    capacity_ok = fields.Boolean(
        string='Capacity OK',
        compute='_compute_capacity_check',
    )

    capacity_message = fields.Char(
        string='Capacity Message',
        compute='_compute_capacity_check',
    )

    # ===== NOTES =====
    notes = fields.Text(
        string='Notes',
        help="Additional notes about this placement"
    )

    @api.depends('grid_location_id', 'batch_id')
    def _compute_capacity_check(self):
        for wizard in self:
            if not wizard.grid_location_id or not wizard.batch_id:
                wizard.capacity_ok = False
                wizard.capacity_message = ''
                continue

            grid = wizard.grid_location_id
            batch = wizard.batch_id

            # Check capacity
            if grid.capacity_type == 'weight' and grid.max_weight > 0:
                if batch.weight > grid.max_weight:
                    wizard.capacity_ok = False
                    wizard.capacity_message = _('Batch weight exceeds limit')
                    continue

            if grid.capacity_type == 'volume' and grid.max_volume > 0:
                if batch.volume > grid.max_volume:
                    wizard.capacity_ok = False
                    wizard.capacity_message = _('Batch volume exceeds limit')
                    continue

            if grid.capacity_type == 'count' and grid.max_items > 0:
                if int(batch.total_quantity) > grid.max_items:
                    wizard.capacity_ok = False
                    wizard.capacity_message = _('Batch item count exceeds limit')
                    continue

            wizard.capacity_ok = True
            wizard.capacity_message = _('Capacity sufficient')

    def action_place_batch(self):
        self.ensure_one()

        if not self.capacity_ok:
            raise UserError(self.capacity_message)

        # Update grid location with batch
        self.grid_location_id.write({
            'batch_id': self.batch_id.id,
            'location_id': self.location_id.id,
            'notes': self.notes,
        })

        # Update batch state
        self.batch_id.state = 'in_receiving'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Batch Placed'),
                'message': _('Batch %s placed at %s') % (
                    self.batch_id.name,
                    self.grid_location_id.position_code
                ),
                'type': 'success',
                'sticky': False,
            }
        }


class HdiBatchRelocationWizard(models.TransientModel):
    """Wizard to move batch to another location"""
    _name = 'hdi.batch.relocation.wizard'
    _description = 'Batch Relocation Wizard'

    # ===== SOURCE LOCATION =====
    from_grid_location_id = fields.Many2one(
        'hdi.warehouse.location.grid',
        string='From Location',
        readonly=True,
    )

    batch_id = fields.Many2one(
        'hdi.batch',
        string='Batch',
        readonly=True,
    )

    # ===== DESTINATION =====
    layout_id = fields.Many2one(
        'hdi.warehouse.layout',
        string='Layout',
        required=True,
    )

    to_grid_location_id = fields.Many2one(
        'hdi.warehouse.location.grid',
        string='To Location',
        required=True,
        domain="[('layout_id', '=', layout_id), ('batch_id', '=', False)]",
    )

    # ===== REASON =====
    relocation_reason = fields.Selection([
        ('capacity', 'Capacity optimization'),
        ('consolidation', 'Consolidation'),
        ('zone_change', 'Zone change'),
        ('damage', 'Damage relocation'),
        ('picking_optimization', 'Picking optimization'),
        ('other', 'Other'),
    ], string='Reason', required=True)

    notes = fields.Text(string='Notes')

    def action_relocate_batch(self):
        self.ensure_one()

        # Move batch to new location
        self.from_grid_location_id.write({
            'batch_id': False,
            'last_batch_id': self.batch_id.id,
            'last_change_date': fields.Datetime.now(),
        })

        self.to_grid_location_id.write({
            'batch_id': self.batch_id.id,
            'notes': self.notes,
        })

        # Log in batch chatter
        message = _(
            'Batch relocated from %s to %s (Reason: %s)'
        ) % (
            self.from_grid_location_id.position_code,
            self.to_grid_location_id.position_code,
            self.relocation_reason
        )
        self.batch_id.message_post(body=message)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Batch Relocated'),
                'message': _('Batch moved from %s to %s') % (
                    self.from_grid_location_id.position_code,
                    self.to_grid_location_id.position_code
                ),
                'type': 'success',
                'sticky': False,
            }
        }


class HdiBatchWarehouseTransferWizard(models.TransientModel):
    """Wizard to transfer batch to another warehouse"""
    _name = 'hdi.batch.warehouse.transfer.wizard'
    _description = 'Batch Warehouse Transfer Wizard'

    batch_id = fields.Many2one(
        'hdi.batch',
        string='Batch',
        readonly=True,
    )

    from_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='From Warehouse',
        readonly=True,
    )

    to_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='To Warehouse',
        required=True,
        domain="[('id', '!=', from_warehouse_id)]",
    )

    transfer_reason = fields.Selection([
        ('stock_balance', 'Stock balancing'),
        ('fulfillment', 'Fulfillment'),
        ('return', 'Return to supplier'),
        ('consolidation', 'Consolidation'),
        ('other', 'Other'),
    ], string='Reason', required=True)

    notes = fields.Text(string='Notes')

    def action_transfer_batch(self):
        self.ensure_one()

        # Get destination location (Goods In location of target warehouse)
        dest_location = self.to_warehouse_id.in_type_id.default_location_dest_id or \
                       self.to_warehouse_id.lot_stock_id

        # Create internal transfer
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_internal').id,
            'location_id': self.batch_id.location_id.id,
            'location_dest_id': dest_location.id,
            'note': self.notes,
        })

        # Add moves from batch
        for move in self.batch_id.move_ids:
            self.env['stock.move'].create({
                'picking_id': picking.id,
                'product_id': move.product_id.id,
                'quantity_done': move.product_qty,
                'location_id': move.location_id.id,
                'location_dest_id': dest_location.id,
                'name': move.name,
            })

        # Update batch
        self.batch_id.message_post(
            body=_('Transferred to warehouse: %s') % self.to_warehouse_id.name
        )

        return {
            'name': _('Internal Transfer'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'view_mode': 'form',
        }
