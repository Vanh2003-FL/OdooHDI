# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AssignLotPositionWizard(models.TransientModel):
    _name = 'assign.lot.position.wizard'
    _description = 'Wizard gán vị trí cho lot'

    posx = fields.Integer(string='Vị trí X (Cột)', required=True)
    posy = fields.Integer(string='Vị trí Y (Hàng)', required=True)
    posz = fields.Integer(string='Vị trí Z (Tầng)', default=0)

    warehouse_map_id = fields.Many2one('warehouse.map', string='Sơ đồ kho', required=True)

    # Mode: Batch hay Quant
    mode = fields.Selection([
        ('batch', 'Gán theo Batch/LPN'),
        ('quant', 'Gán theo Lot/Quant'),
    ], string='Chế độ gán', default='batch', required=True)

    # BATCH MODE - chỉ dùng batch_id, không dùng display fields
    batch_id = fields.Many2one('hdi.batch', string='Chọn Batch/LPN')

    # QUANT MODE
    quant_id = fields.Many2one('stock.quant', string='Chọn Lot/Quant')
    create_new = fields.Boolean(string='Tạo quant mới')
    new_product_id = fields.Many2one('product.product', string='Sản phẩm mới')
    new_lot_id = fields.Many2one('stock.lot', string='Lot/Serial mới',
                                 domain="[('product_id', '=', new_product_id)]")
    new_quantity = fields.Float(string='Số lượng mới', default=1.0)

    @api.model
    def create_from_map_click(self, warehouse_map_id, posx, posy, posz, batch_id=None):
        """Create wizard record when user clicks cell on map
        
        Args:
            warehouse_map_id: ID of warehouse.map
            posx, posy, posz: Cell coordinates
            batch_id: Optional batch ID (for batch assignment mode)
        
        Returns:
            Dictionary with wizard action
        """
        mode = 'batch' if batch_id else 'quant'
        
        wizard = self.create({
            'warehouse_map_id': warehouse_map_id,
            'posx': posx,
            'posy': posy,
            'posz': posz,
            'mode': mode,
            'batch_id': batch_id,
        })
        
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
        """Gán vị trí cho batch hoặc quant"""
        self.ensure_one()
        location = self.warehouse_map_id.location_id
        if not location:
            raise UserError(_('Sơ đồ kho không có location!'))

        # Kiểm tra vị trí bị block
        blocked = self.env['warehouse.map.blocked.cell'].search([
            ('warehouse_map_id', '=', self.warehouse_map_id.id),
            ('posx', '=', self.posx),
            ('posy', '=', self.posy),
            ('posz', '=', self.posz),
        ], limit=1)
        
        if blocked:
            raise UserError(_(
                'Vị trí [%d, %d, %d] đang bị chặn'
            ) % (self.posx, self.posy, self.posz))

        # ========== BATCH MODE ==========
        if self.mode == 'batch':
            if not self.batch_id:
                raise UserError(_('Vui lòng chọn batch!'))

            # Validate batch state
            if self.batch_id.state != 'stored':
                raise UserError(_('Batch phải ở trạng thái Stored!'))

            # Kiểm tra vị trí đã có lot khác chưa
            existing = self.env['stock.quant'].search([
                ('location_id', 'child_of', location.id),
                ('posx', '=', self.posx),
                ('posy', '=', self.posy),
                ('posz', '=', self.posz),
                ('display_on_map', '=', True),
                ('quantity', '>', 0),
                ('batch_id', '!=', self.batch_id.id),
            ], limit=1)

            if existing:
                raise UserError(_('Vị trí đã có lot khác!'))

            # Gán vị trí cho batch
            self.batch_id.write({
                'posx': self.posx,
                'posy': self.posy,
                'posz': self.posz,
                'display_on_map': True,
            })

            # Gán vị trí cho tất cả quants của batch
            self.batch_id.quant_ids.write({
                'posx': self.posx,
                'posy': self.posy,
                'posz': self.posz,
                'display_on_map': True,
            })

            return {'type': 'ir.actions.act_window_close'}

        # ========== QUANT MODE ==========
        # Create new quant
        if self.mode == 'quant' and self.create_new:
            if not self.new_product_id:
                raise UserError(_('Vui lòng chọn sản phẩm!'))

            quant_vals = {
                'product_id': self.new_product_id.id,
                'location_id': location.id,
                'quantity': self.new_quantity,
                'posx': self.posx,
                'posy': self.posy,
                'posz': self.posz,
                'display_on_map': True,
            }
            if self.new_lot_id:
                quant_vals['lot_id'] = self.new_lot_id.id

            self.env['stock.quant'].create(quant_vals)
            return {'type': 'ir.actions.act_window_close'}
        
        # Assign existing quant
        if self.mode == 'quant' and not self.create_new:
            if not self.quant_id:
                raise UserError(_('Vui lòng chọn quant!'))

            if self.quant_id.quantity <= 0:
                raise UserError(_('Quant không có số lượng!'))

            existing = self.env['stock.quant'].search([
                ('location_id', 'child_of', location.id),
                ('posx', '=', self.posx),
                ('posy', '=', self.posy),
                ('posz', '=', self.posz),
                ('display_on_map', '=', True),
                ('quantity', '>', 0),
                ('id', '!=', self.quant_id.id),
            ], limit=1)

            if existing:
                raise UserError(_('Vị trí đã có lot khác!'))

            self.quant_id.write({
                'posx': self.posx,
                'posy': self.posy,
                'posz': self.posz,
                'display_on_map': True,
            })

            return {'type': 'ir.actions.act_window_close'}
        
        raise UserError(_('Vui lòng chọn batch hoặc quant!'))
