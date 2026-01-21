# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HDIWarehouseLayout(models.Model):
    _name = 'hdi.warehouse.layout'
    _description = 'Warehouse Layout / Grid Map'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ===== BASIC INFO =====
    name = fields.Char(
        string='Layout Name',
        required=True,
        tracking=True,
    )

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        required=True,
        tracking=True,
    )

    description = fields.Text(
        string='Description',
        help="Layout description and notes"
    )

    # ===== GRID DIMENSIONS =====
    rows = fields.Integer(
        string='Rows',
        default=10,
        required=True,
        help="Number of rows in the grid (Y axis)"
    )

    columns = fields.Integer(
        string='Columns',
        default=10,
        required=True,
        help="Number of columns in the grid (X axis)"
    )

    levels = fields.Integer(
        string='Levels',
        default=3,
        required=True,
        help="Number of levels/heights (Z axis)"
    )

    # ===== GRID CELLS =====
    location_grid_ids = fields.One2many(
        'hdi.warehouse.layout.grid',
        'layout_id',
        string='Grid Cells',
        help="Grid cell locations"
    )

    # ===== CAPACITY & USAGE =====
    total_slots = fields.Integer(
        compute='_compute_slot_stats',
        string='Total Slots',
        store=True,
    )

    occupied_slots = fields.Integer(
        compute='_compute_slot_stats',
        string='Occupied Slots',
        store=True,
    )

    empty_slots = fields.Integer(
        compute='_compute_slot_stats',
        string='Empty Slots',
        store=True,
    )

    utilization_rate = fields.Float(
        compute='_compute_utilization_rate',
        string='Utilization Rate (%)',
        store=True,
    )
    # ===== STATUS =====
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True)

    is_active = fields.Boolean(
        compute='_compute_is_active',
        string='Active',
        store=True,
    )

    # ===== TIMESTAMPS =====
    created_date = fields.Datetime(
        string='Created Date',
        readonly=True,
    )

    @api.model_create_single
    def create(self, vals):
        record = super().create(vals)
        # Auto-create grid cells based on dimensions
        record._create_grid_cells()
        return record

    def _create_grid_cells(self):
        """Create grid cells for this layout"""
        self.ensure_one()
        cells = []
        
        for row in range(self.rows):
            for col in range(self.columns):
                for level in range(self.levels):
                    cells.append({
                        'layout_id': self.id,
                        'row': row,
                        'column': col,
                        'level': level,
                        'location_code': f"{self.warehouse_id.code}-{row}-{col}-{level}",
                    })
        
        if cells:
            self.env['hdi.warehouse.layout.grid'].create(cells)

    @api.depends('state')
    def _compute_is_active(self):
        """Compute is_active based on state"""
        for record in self:
            record.is_active = record.state == 'active'

    @api.depends('location_grid_ids', 'location_grid_ids.batch_id')
    def _compute_slot_stats(self):
        """Compute slot statistics"""
        for record in self:
            total = len(record.location_grid_ids)
            occupied = len(record.location_grid_ids.filtered('batch_id'))
            empty = total - occupied
            
            record.total_slots = total
            record.occupied_slots = occupied
            record.empty_slots = empty

    @api.depends('total_slots', 'occupied_slots')
    def _compute_utilization_rate(self):
        """Compute utilization rate percentage"""
        for record in self:
            if record.total_slots > 0:
                record.utilization_rate = (record.occupied_slots / record.total_slots) * 100
            else:
                record.utilization_rate = 0.0

    def action_activate(self):
        """Activate this layout"""
        self.write({'state': 'active'})

    def action_archive(self):
        """Archive this layout"""
        self.write({'state': 'archived'})

    def action_view_grid(self):
        """Open the warehouse grid view"""
        return {
            'type': 'ir.actions.client',
            'tag': 'warehouse_grid',
            'name': _('Warehouse Grid'),
        }


class HDIWarehouseLayoutGrid(models.Model):
    _name = 'hdi.warehouse.layout.grid'
    _description = 'Warehouse Layout Grid Cell'

    # ===== GRID POSITION =====
    layout_id = fields.Many2one(
        'hdi.warehouse.layout',
        string='Layout',
        required=True,
        ondelete='cascade',
    )

    row = fields.Integer(
        string='Row',
        required=True,
    )

    column = fields.Integer(
        string='Column',
        required=True,
    )

    level = fields.Integer(
        string='Level',
        required=True,
    )

    location_code = fields.Char(
        string='Location Code',
        required=True,
    )

    # ===== CONTENT =====
    batch_id = fields.Many2one(
        'hdi.batch',
        string='Batch/Lot',
        help="Batch currently in this location",
        inverse_name=False,
        ondelete='set null',
    )

    location_id = fields.Many2one(
        'stock.location',
        string='Stock Location',
        help="Linked stock location",
        ondelete='set null',
    )

    # ===== STATUS =====
    is_occupied = fields.Boolean(
        compute='_compute_is_occupied',
        string='Occupied',
        store=True,
    )

    # ===== METADATA =====
    notes = fields.Text(
        string='Notes',
    )

    @api.depends('batch_id')
    def _compute_is_occupied(self):
        """Check if cell is occupied"""
        for record in self:
            record.is_occupied = bool(record.batch_id)

    def _get_days_in_warehouse(self):
        """Get days in warehouse for batch"""
        if self.batch_id:
            return self.batch_id.days_in_warehouse or 0
        return 0

    @property
    def days_in_warehouse(self):
        """Property to access days in warehouse"""
        return self._get_days_in_warehouse()
    def action_view_warehouse_map(self):
        """Open warehouse map view"""
        return {
            'type': 'ir.actions.client',
            'tag': 'warehouse_map_dialog',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'hdi.warehouse.layout',
            }
        }