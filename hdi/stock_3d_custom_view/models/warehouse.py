"""This module inherits stock.warehouse model."""
# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models


class StockWarehouse(models.Model):
    """Class for adding fields to stock.warehouse"""
    _inherit = 'stock.warehouse'

    layout_width = fields.Float(
        string="Layout Width (px)",
        default=1200.0,
        help="Width of the warehouse layout canvas in pixels"
    )
    layout_height = fields.Float(
        string="Layout Height (px)",
        default=800.0,
        help="Height of the warehouse layout canvas in pixels"
    )
    is_2d_configured = fields.Boolean(
        string="2D Layout Configured",
        default=False,
        help="Indicates if warehouse layout has been configured in 2D"
    )

    def action_open_warehouse_layout_editor(self):
        """
        This method opens the warehouse layout editor (2D/3D view).
        ------------------------------------------------
        @param self: object pointer.
        @return: client action with warehouse id and company id to display.
        """
        return {
            'type': 'ir.actions.client',
            'tag': 'open_warehouse_layout_editor',
            'warehouse_id': self.id,
            'company_id': self.company_id.id,
            'warehouse_name': self.name,
            'context': {
                'warehouse_id': self.id,
                'company_id': self.company_id.id,
            }
        }
