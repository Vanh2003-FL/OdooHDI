"""This module inherits stock.location model."""
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
#    Upgraded to Odoo 18 by Wokwy - Integrated with warehouse_map module
#
#############################################################################
from odoo import fields, models


class StockLocation(models.Model):
    """Class for adding fields to stock.location - 3D visualization properties"""
    _inherit = 'stock.location'

    # Renamed fields to avoid conflict with warehouse_map module
    # These are for LOCATION 3D box dimensions and positions
    loc_length = fields.Float(string="3D Length (M)",
                          help="Length of the location box in meters for 3D visualization")
    loc_width = fields.Float(string="3D Width (M)",
                         help="Width of the location box in meters for 3D visualization")
    loc_height = fields.Float(string="3D Height (M)",
                          help="Height of the location box in meters for 3D visualization")
    loc_pos_x = fields.Float(string="3D X Position (px)",
                         help="Position of the location box along X-axis in 3D scene")
    loc_pos_y = fields.Float(string="3D Y Position (px)",
                         help="Position of the location box along Y-axis in 3D scene")
    loc_pos_z = fields.Float(string="3D Z Position (px)",
                         help="Position of the location box along Z-axis in 3D scene")
    loc_3d_code = fields.Char(string="3D Location Code",
                              help="Unique code of the location for 3D visualization")
    loc_max_capacity = fields.Integer(string="3D Capacity (Units)",
                                  help="Maximum capacity of the location in terms of Units for 3D color coding")

    _sql_constraints = [
        ('loc_3d_code_unique', 'UNIQUE(loc_3d_code)',
         "The 3D location code must be unique per company !"),
    ]

    def action_view_location_3d_button(self):
        """
        This method is used to handle the view_location_3d_button button action.
        ------------------------------------------------
        @param self: object pointer.
        @return: client action with location id and company id to display.
        """
        return {
            'type': 'ir.actions.client',
            'tag': 'open_form_3d_view',
            'context': {
                'loc_id': self.id,
                'company_id': self.company_id.id,
            }
        }
    
    def action_view_warehouse_3d_map(self):
        """
        Open 3D warehouse map view from location form
        Shows all products/lots in child locations with their 3D positions
        """
        return {
            'type': 'ir.actions.client',
            'tag': 'open_warehouse_3d_view',
            'context': {
                'parent_location_id': self.id,
                'company_id': self.company_id.id,
            }
        }
