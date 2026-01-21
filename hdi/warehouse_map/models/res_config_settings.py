# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Fix stock_sms fields cho Odoo 18 - thêm related_sudo=False
    stock_move_sms_validation = fields.Boolean(
        related='company_id.stock_move_sms_validation',
        string='SMS Validation with stock move',
        readonly=False,
        related_sudo=False
    )
    
    stock_sms_confirmation_template_id = fields.Many2one(
        related='company_id.stock_sms_confirmation_template_id',
        readonly=False,
        related_sudo=False
    )
