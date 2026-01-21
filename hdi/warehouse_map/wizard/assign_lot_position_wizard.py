# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AssignLotPositionWizard(models.TransientModel):
    _name = 'assign.lot.position.wizard'
    _description = 'Wizard gán vị trí cho batch'
    _transient_max_hours = 1.0

    posx = fields.Integer(string='Vị trí X (Cột)')
    posy = fields.Integer(string='Vị trí Y (Hàng)')
    posz = fields.Integer(string='Vị trí Z (Tầng)', default=0)

    # Use Integer fields only to store IDs - avoids All onchange/serialize issues
    warehouse_map_id = fields.Integer(string='Sơ đồ kho ID')
    batch_id = fields.Integer(string='Batch ID')
    
    # Batch name for display (read-only, no serialize)
    batch_name = fields.Char(string='Chọn Batch/LPN', compute='_compute_batch_name')

    @property
    def warehouse_map(self):
        """Get actual warehouse.map record from ID"""
        return self.env['warehouse.map'].browse(self.warehouse_map_id) if self.warehouse_map_id else None

    @property
    def batch(self):
        """Get actual hdi.batch record from ID"""
        return self.env['hdi.batch'].browse(self.batch_id) if self.batch_id else None

    @api.depends('batch_id')
    def _compute_batch_name(self):
        for rec in self:
            if rec.batch_id:
                batch = rec.env['hdi.batch'].browse(rec.batch_id)
                rec.batch_name = batch.name if batch.exists() else ''
            else:
                rec.batch_name = ''

    @api.model
    def create_from_map_click(self, warehouse_map_id, posx, posy, posz, batch_id=None):
        """Create wizard record when user clicks cell on map
        
        Args:
            warehouse_map_id: ID of warehouse.map
            posx, posy, posz: Cell coordinates
            batch_id: Optional batch ID (for batch assignment mode)
        
        Returns:
            Dictionary with wizard action pointing to created record
        """
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(f"=== create_from_map_click called ===")
        _logger.info(f"warehouse_map_id: {warehouse_map_id}")
        _logger.info(f"posx: {posx}, posy: {posy}, posz: {posz}")
        _logger.info(f"batch_id: {batch_id}")
        
        # Create wizard record with actual values
        # Use Integer fields only - no Many2one = no onchange issues
        wizard_vals = {
            'warehouse_map_id': warehouse_map_id,
            'posx': posx,
            'posy': posy,
            'posz': posz or 0,
        }
        
        if batch_id:
            wizard_vals['batch_id'] = batch_id
        
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
        if not batch.exists():
            raise UserError(_('Batch không tồn tại!'))
        
        if batch.state != 'stored':
            raise UserError(_('Batch phải ở trạng thái Stored!'))

        warehouse_map = self.warehouse_map
        location = warehouse_map.location_id if warehouse_map else None
        if not location:
            raise UserError(_('Sơ đồ kho không có location!'))

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
        existing = self.env['stock.quant'].search([
            ('location_id', 'child_of', location.id),
            ('posx', '=', self.posx),
            ('posy', '=', self.posy),
            ('posz', '=', self.posz),
            ('display_on_map', '=', True),
            ('quantity', '>', 0),
            ('batch_id', '!=', batch.id),
        ], limit=1)

        if existing:
            raise UserError(_('Vị trí đã có lot khác!'))

        # Gán vị trí cho batch
        batch.write({
            'posx': self.posx,
            'posy': self.posy,
            'posz': self.posz,
            'display_on_map': True,
        })

        # Gán vị trí cho tất cả quants của batch
        batch.quant_ids.write({
            'posx': self.posx,
            'posy': self.posy,
            'posz': self.posz,
            'display_on_map': True,
        })

        return {'type': 'ir.actions.act_window_close'}
