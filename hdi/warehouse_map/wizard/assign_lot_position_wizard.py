# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AssignLotPositionWizard(models.TransientModel):
    _name = 'assign.lot.position.wizard'
    _description = 'Wizard gán vị trí cho lot/pallet'
    _transient_max_hours = 1.0

    posx = fields.Integer(string='Vị trí X (Cột)')
    posy = fields.Integer(string='Vị trí Y (Hàng)')
    posz = fields.Integer(string='Vị trí Z (Tầng)', default=0)

    # Use Integer fields only to store IDs
    warehouse_map_id = fields.Integer(string='Sơ đồ kho ID')
    lot_id = fields.Integer(string='Lot ID')
    
    # Lot name for display (read-only)
    lot_name = fields.Char(string='Chọn Lot/LPN/Pallet', compute='_compute_lot_name')

    @property
    def warehouse_map(self):
        """Get actual warehouse.map record from ID"""
        return self.env['warehouse.map'].browse(self.warehouse_map_id) if self.warehouse_map_id else None

    @property
    def lot(self):
        """Get actual stock.lot record from ID"""
        return self.env['stock.lot'].browse(self.lot_id) if self.lot_id else None

    @api.depends('lot_id')
    def _compute_lot_name(self):
        for rec in self:
            if rec.lot_id:
                lot = rec.env['stock.lot'].browse(rec.lot_id)
                rec.lot_name = lot.name if lot.exists() else ''
            else:
                rec.lot_name = ''

    @api.model
    def create_from_map_click(self, warehouse_map_id, posx, posy, posz, lot_id=None):
        """Create wizard record when user clicks cell on map
        
        Args:
            warehouse_map_id: ID of warehouse.map
            posx, posy, posz: Cell coordinates
            lot_id: Optional lot ID (for lot assignment mode)
        
        Returns:
            Dictionary with wizard action pointing to created record
        """
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(f"=== create_from_map_click called ===")
        _logger.info(f"warehouse_map_id: {warehouse_map_id}")
        _logger.info(f"posx: {posx}, posy: {posy}, posz: {posz}")
        _logger.info(f"lot_id: {lot_id}")
        
        # Create wizard record with actual values
        wizard_vals = {
            'warehouse_map_id': warehouse_map_id,
            'posx': posx,
            'posy': posy,
            'posz': posz or 0,
        }
        
        if lot_id:
            wizard_vals['lot_id'] = lot_id
        
        wizard = self.create(wizard_vals)
        _logger.info(f"Wizard created with id: {wizard.id}")
        
        return {
            'name': _('Gán vị trí [%d, %d]') % (posx, posy),
            'type': 'ir.actions.act_window',
            'res_model': 'assign.lot.position.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'new',
        }

    def action_assign_position(self):
        """Gán vị trí cho batch"""
        self.ensure_one()
        
        # Validate required fields
        if not self.warehouse_map_id:
            raise UserError(_('Thiếu thông tin sơ đồ kho!'))
            
        if self.posx is False or self.posy is False:
            raise UserError(_('Thiếu thông tin vị trí!'))
        
        if not self.batch_id:
            raise UserError(_('Vui lòng chọn batch!'))
        
        batch = self.batch
if not lot.exists():
            raise UserError(_('Lot không tồn tại!'))

        warehouse_map = self.warehouse_map
        if not warehouse_map:
            raise UserError(_('Sơ đồ kho không tồn tại!'))

        # Kiểm tra vị trí bị block
        blocked = self.env['warehouse.map.blocked.cell'].search([
            ('warehouse_map_id', '=', self.warehouse_map_id),
            ('posx', '=', self.posx),
            ('posy', '=', self.posy),
            ('posz', '=', self.posz),
        ], limit=1)
        
        if blocked:
            raise UserError(_(
                'Vị trí [%d, %d, %d] đang bị chặn'
            ) % (self.posx, self.posy, self.posz))

        # Kiểm tra vị trí đã có lot khác chưa
        existing_lot = self.env['stock.lot'].search([
            ('id', '!=', lot.id),
            ('display_on_map', '=', True),
            ('posx', '=', self.posx),
            ('posy', '=', self.posy),
            ('posz', '=', self.posz),
        ], limit=1)

        if existing_lot:
            raise UserError(_(
                'Vị trí [%d, %d, %d] đã có lot: %s'
            ) % (self.posx, self.posy, self.posz, existing_lot.name))

        # Gán vị trí cho lot
        lot.write({
            'posx': self.posx,
            'posy': self.posy,
            'posz': self.posz,
            'display_on_map': True,
            'warehouse_map_id': self.warehouse_map_id,
        })
        
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(f"[AssignPosition] SUCCESS - Lot {lot.name} assigned to [{self.posx}, {self.posy}, {self.posz}]")
        _logger.info(f"[AssignPosition] Lot display_on_map: {lot.display_on_map}")
        _logger.info(f"[AssignPosition] Lot has {len(lot.quant_ids)} quants")
        for quant in lot.quant_ids:
            _logger.info(f"[AssignPosition] Quant {quant.id}: location={quant.location_id.complete_name if quant.location_id else 'N/A'}")

        return {'type': 'ir.actions.act_window_close'}
