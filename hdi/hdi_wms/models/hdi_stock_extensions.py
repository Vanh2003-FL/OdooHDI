# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockLocation(models.Model):
    _inherit = 'stock.location'

    # ===== GRID LOCATION LINK =====
    grid_location_id = fields.Many2one(
        'hdi.warehouse.location.grid',
        string='Grid Location',
        help="Link to warehouse grid layout"
    )

    is_grid_enabled = fields.Boolean(
        string='Grid Enabled',
        compute='_compute_grid_enabled',
        help="Is this location part of a grid layout?"
    )

    grid_position_code = fields.Char(
        string='Grid Position',
        related='grid_location_id.position_code',
        readonly=True,
        store=False,
    )

    grid_row = fields.Integer(
        string='Row',
        related='grid_location_id.row',
        readonly=True,
        store=False,
    )

    grid_column = fields.Integer(
        string='Column',
        related='grid_location_id.column',
        readonly=True,
        store=False,
    )

    grid_level = fields.Integer(
        string='Level',
        related='grid_location_id.level',
        readonly=True,
        store=False,
    )

    @api.depends('grid_location_id')
    def _compute_grid_enabled(self):
        for location in self:
            location.is_grid_enabled = bool(location.grid_location_id)


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    # ===== WAREHOUSE LAYOUT =====
    layout_id = fields.Many2one(
        'hdi.warehouse.layout',
        string='Sơ đồ kho',
        ondelete='set null',
        help="Associated warehouse layout for grid visualization"
    )

    has_layout = fields.Boolean(
        string='Có sơ đồ',
        related='layout_id.active',
        readonly=True,
        store=False,
    )

    layout_rows = fields.Integer(
        string='Hàng sơ đồ',
        related='layout_id.rows',
        readonly=True,
        store=False,
    )

    layout_columns = fields.Integer(
        string='Cột sơ đồ',
        related='layout_id.columns',
        readonly=True,
        store=False,
    )

    layout_levels = fields.Integer(
        string='Tầng sơ đồ',
        related='layout_id.levels',
        readonly=True,
        store=False,
    )

    def action_open_layout(self):
        """Open warehouse layout visualization"""
        self.ensure_one()
        if not self.layout_id:
            raise UserError(_('No layout assigned to this warehouse'))

        return {
            'name': _('Warehouse Layout - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.warehouse.layout',
            'res_id': self.layout_id.id,
            'view_mode': 'form',
            'views': [(self.env.ref('hdi_wms.view_warehouse_layout_form').id, 'form')],
            'target': 'fullscreen',
        }

    def action_create_layout(self):
        """Create a new layout for this warehouse"""
        self.ensure_one()

        layout = self.env['hdi.warehouse.layout'].create({
            'warehouse_id': self.id,
            'name': _('Layout - %s') % self.name,
            'rows': 5,
            'columns': 10,
            'levels': 3,
        })

        return self.action_open_layout()
