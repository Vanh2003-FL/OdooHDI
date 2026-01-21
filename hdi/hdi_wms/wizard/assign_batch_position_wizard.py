# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AssignBatchPositionWizard(models.TransientModel):
    _name = 'assign.batch.position.wizard'
    _description = 'Wizard gán vị trí batch trên sơ đồ kho'

    batch_id = fields.Many2one('hdi.batch', string='Batch', required=True, readonly=True)
    warehouse_map_id = fields.Many2one('warehouse.map', string='Sơ đồ kho', required=True)
    
    posx = fields.Integer(string='Vị trí X (Cột)', required=True)
    posy = fields.Integer(string='Vị trí Y (Hàng)', required=True)
    posz = fields.Integer(string='Vị trí Z (Tầng)', default=0)
    
    display_on_map = fields.Boolean(string='Hiển thị trên sơ đồ', default=True)
    
    # Display info
    batch_name = fields.Char(related='batch_id.name', string='Batch Number', readonly=True)
    product_id = fields.Many2one(related='batch_id.product_id', string='Sản phẩm', readonly=True)
    total_quantity = fields.Float(related='batch_id.total_quantity', string='Số lượng', readonly=True)
    location_id = fields.Many2one(related='batch_id.location_id', string='Vị trí hiện tại', readonly=True)
    
    # Map info
    rows = fields.Integer(related='warehouse_map_id.rows', readonly=True)
    columns = fields.Integer(related='warehouse_map_id.columns', readonly=True)
    
    @api.onchange('warehouse_map_id')
    def _onchange_warehouse_map(self):
        """Reset position when changing warehouse map"""
        self.posx = False
        self.posy = False
        self.posz = 0
    
    @api.constrains('posx', 'posy', 'warehouse_map_id')
    def _check_position_bounds(self):
        """Validate position is within map boundaries"""
        for wizard in self:
            if wizard.posx and wizard.warehouse_map_id:
                if wizard.posx < 0 or wizard.posx > wizard.warehouse_map_id.columns:
                    raise UserError(_(
                        'Position X must be between 0 and %d (columns)'
                    ) % wizard.warehouse_map_id.columns)
            
            if wizard.posy and wizard.warehouse_map_id:
                if wizard.posy < 0 or wizard.posy > wizard.warehouse_map_id.rows:
                    raise UserError(_(
                        'Position Y must be between 0 and %d (rows)'
                    ) % wizard.warehouse_map_id.rows)
    
    def action_assign_position(self):
        """Assign position to batch and all its quants"""
        self.ensure_one()
        
        if not self.posx or not self.posy:
            raise UserError(_('Please provide X and Y coordinates.'))
        
        # Check if position is already occupied
        # Check blocked cells first
        blocked = self.env['warehouse.map.blocked.cell'].search([
            ('warehouse_map_id', '=', self.warehouse_map_id.id),
            ('posx', '=', self.posx),
            ('posy', '=', self.posy),
            ('posz', '=', self.posz),
        ], limit=1)
        
        if blocked:
            raise UserError(_(
                'Position [%d, %d, %d] is blocked: %s'
            ) % (self.posx, self.posy, self.posz, blocked.reason or 'No reason provided'))
        
        # Check if another batch/quant with tracked products occupies this position
        existing_quants = self.env['stock.quant'].search([
            ('location_id', 'child_of', self.warehouse_map_id.location_id.id),
            ('posx', '=', self.posx),
            ('posy', '=', self.posy),
            ('posz', '=', self.posz),
            ('display_on_map', '=', True),
            ('quantity', '>', 0),
            ('product_id.tracking', '!=', 'none'),
            ('batch_id', '!=', self.batch_id.id),
        ], limit=1)
        
        if existing_quants:
            raise UserError(_(
                'Position [%d, %d, %d] is already occupied by: %s (Lot: %s)'
            ) % (self.posx, self.posy, self.posz, 
                 existing_quants.product_id.display_name,
                 existing_quants.lot_id.name if existing_quants.lot_id else 'N/A'))
        
        # Assign position to batch
        self.batch_id.write({
            'posx': self.posx,
            'posy': self.posy,
            'posz': self.posz,
            'display_on_map': self.display_on_map,
        })
        
        # Update all quants in this batch (only tracked products)
        tracked_quants = self.batch_id.quant_ids.filtered(
            lambda q: q.product_id.tracking != 'none'
        )
        
        if tracked_quants:
            tracked_quants.write({
                'posx': self.posx,
                'posy': self.posy,
                'posz': self.posz,
                'display_on_map': self.display_on_map,
            })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Position [%d, %d, %d] assigned to batch %s. %d quants updated.') % (
                    self.posx, self.posy, self.posz, 
                    self.batch_id.name,
                    len(tracked_quants)
                ),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
    
    def action_view_map(self):
        """Open warehouse map to visualize available positions"""
        self.ensure_one()
        return self.warehouse_map_id.action_view_map()
