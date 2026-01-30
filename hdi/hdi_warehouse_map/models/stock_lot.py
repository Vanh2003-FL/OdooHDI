# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockLot(models.Model):
    _inherit = 'stock.lot'
    
    # FR-17: Lot bị block không được picking
    is_blocked = fields.Boolean(string='Blocked', default=False, tracking=True)
    block_reason = fields.Text(string='Block Reason')
    blocked_date = fields.Datetime(string='Blocked Date')
    blocked_by = fields.Many2one('res.users', string='Blocked By')
    
    # History
    history_ids = fields.One2many('lot.history', 'lot_id', string='Movement History')
    
    def action_block_lot(self):
        """Block lot"""
        self.ensure_one()
        return {
            'name': _('Block Lot'),
            'type': 'ir.actions.act_window',
            'res_model': 'bin.block.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lot_id': self.id,
                'default_action': 'block',
            }
        }
    
    def action_unblock_lot(self):
        """Unblock lot"""
        self.ensure_one()
        self.write({
            'is_blocked': False,
            'block_reason': False,
            'blocked_date': False,
            'blocked_by': False,
        })
        return True
    
    def action_view_history(self):
        """FR-19: Xem lịch sử di chuyển theo Lot/Sê-ri"""
        self.ensure_one()
        return {
            'name': _('Lot Movement History'),
            'type': 'ir.actions.act_window',
            'res_model': 'lot.history',
            'view_mode': 'tree,form',
            'domain': [('lot_id', '=', self.id)],
            'context': {'default_lot_id': self.id}
        }
    
    @api.constrains('is_blocked')
    def _check_blocked_lot_usage(self):
        """FR-17: Prevent usage of blocked lots"""
        for lot in self:
            if lot.is_blocked:
                # Check if lot is being used in any pending moves
                pending_moves = self.env['stock.move'].search([
                    ('lot_ids', 'in', lot.ids),
                    ('state', 'not in', ['done', 'cancel']),
                ])
                if pending_moves:
                    raise ValidationError(_(
                        'Cannot block lot %s!\n'
                        'It is being used in pending stock moves: %s'
                    ) % (lot.name, ', '.join(pending_moves.mapped('reference'))))
