# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WarehouseMapAssignLotWizard(models.TransientModel):
    """Wizard để gán lot/quant vào vị trí lưới"""
    _name = 'warehouse.map.assign.lot.wizard'
    _description = 'Gán Lot/Quant vào Vị trí Lưới'

    layout_id = fields.Many2one(
        'hdi.warehouse.layout',
        string='Sơ đồ Kho',
        required=True,
    )

    position_x = fields.Integer(
        string='Vị trí X (Cột)',
        readonly=True,
    )

    position_y = fields.Integer(
        string='Vị trí Y (Hàng)',
        readonly=True,
    )

    position_z = fields.Integer(
        string='Vị trí Z (Tầng)',
        readonly=True,
    )

    option = fields.Selection([
        ('existing', 'Chọn Lot hiện có'),
        ('new', 'Tạo Quant mới'),
    ], string='Lựa chọn', required=True, default='existing')

    # ===== OPTION 1: EXISTING QUANT =====
    quant_id = fields.Many2one(
        'stock.quant',
        string='Lot/Quant',
        domain="[('quantity', '>', 0), ('warehouse_id', '=', warehouse_id), ('display_on_map', '=', False)]"
    )

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        related='layout_id.warehouse_id',
        readonly=True,
    )

    # ===== OPTION 2: NEW QUANT =====
    product_id = fields.Many2one(
        'product.product',
        string='Sản phẩm',
    )

    lot_id = fields.Many2one(
        'stock.production.lot',
        string='Lot/Serial',
    )

    quantity = fields.Float(
        string='Số lượng',
        default=1.0,
    )

    @api.onchange('option')
    def _onchange_option(self):
        """Clear fields when switching options"""
        if self.option == 'existing':
            self.product_id = False
            self.lot_id = False
            self.quantity = 1.0
        else:
            self.quant_id = False

    def action_assign(self):
        """Gán lot vào vị trí lưới"""
        self.ensure_one()

        if self.option == 'existing':
            if not self.quant_id:
                raise UserError(_('Vui lòng chọn một quant!'))
            
            quant = self.quant_id
            quant.write({
                'pos_x': self.position_x,
                'pos_y': self.position_y,
                'pos_z': self.position_z,
                'display_on_map': True,
            })
            
            message = _('Đã gán quant "%s" vào vị trí (%d, %d, %d)') % (
                quant.product_id.name,
                self.position_x,
                self.position_y,
                self.position_z
            )

        else:  # new quant
            if not self.product_id:
                raise UserError(_('Vui lòng chọn sản phẩm!'))
            
            if self.quantity <= 0:
                raise UserError(_('Số lượng phải lớn hơn 0!'))

            # Create new quant
            quant = self.env['stock.quant'].create({
                'product_id': self.product_id.id,
                'location_id': self.layout_id.warehouse_id.lot_stock_id.id,
                'quantity': self.quantity,
                'lot_id': self.lot_id.id if self.lot_id else False,
                'pos_x': self.position_x,
                'pos_y': self.position_y,
                'pos_z': self.position_z,
                'display_on_map': True,
            })

            message = _('Đã tạo quant mới cho "%s" tại vị trí (%d, %d, %d)') % (
                self.product_id.name,
                self.position_x,
                self.position_y,
                self.position_z
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Thành công'),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }
