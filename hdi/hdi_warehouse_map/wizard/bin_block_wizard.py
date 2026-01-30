# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BinBlockWizard(models.TransientModel):
    _name = 'bin.block.wizard'
    _description = 'Block/Unblock Bin or Lot Wizard'
    
    action = fields.Selection([
        ('block', 'Block'),
        ('unblock', 'Unblock'),
    ], string='Action', required=True, default='block')
    
    bin_id = fields.Many2one('warehouse.bin', string='Bin')
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial')
    
    reason = fields.Text(string='Reason', required=True)
    
    def action_confirm(self):
        """Confirm block/unblock action"""
        self.ensure_one()
        
        if self.action == 'block':
            if self.bin_id:
                self.bin_id.write({
                    'is_blocked': True,
                    'block_reason': self.reason,
                    'blocked_date': fields.Datetime.now(),
                    'blocked_by': self.env.user.id,
                })
                message = _('Bin %s has been blocked.') % self.bin_id.complete_name
            elif self.lot_id:
                self.lot_id.write({
                    'is_blocked': True,
                    'block_reason': self.reason,
                    'blocked_date': fields.Datetime.now(),
                    'blocked_by': self.env.user.id,
                })
                message = _('Lot %s has been blocked.') % self.lot_id.name
            else:
                raise UserError(_('Please select a Bin or Lot to block.'))
        else:  # unblock
            if self.bin_id:
                self.bin_id.action_unblock_bin()
                message = _('Bin %s has been unblocked.') % self.bin_id.complete_name
            elif self.lot_id:
                self.lot_id.action_unblock_lot()
                message = _('Lot %s has been unblocked.') % self.lot_id.name
            else:
                raise UserError(_('Please select a Bin or Lot to unblock.'))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }
