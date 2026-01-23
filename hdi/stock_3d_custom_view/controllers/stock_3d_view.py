"""This module handles the requests made by js files and returns the corresponding data."""
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
import math
from odoo import http
from odoo.http import request


class Stock3DView(http.Controller):
    """Class for handling the requests and responses - Integrated with warehouse_map"""

    @http.route('/3Dstock/warehouse', type='json', auth='public')
    def get_warehouse_data(self, company_id):
        """
        This method is used to handle the request for warehouse data.
        ------------------------------------------------
        @param self: object pointer.
        @param company_id: current company id.
        @return: a list of warehouses created under the active company.
        """
        warehouse = request.env['stock.warehouse'].sudo().search([
            ('company_id', '=', company_id)
        ])
        warehouse_list = []
        for rec in warehouse:
            warehouse_list.append((rec.id, rec.name))
        return warehouse_list

    @http.route('/3Dstock/locations', type='json', auth='public')
    def get_locations_3d(self, company_id, wh_id):
        """
        NEW: Get 3D shelf/location data for warehouse layout
        Returns all locations with 3D dimensions and positions
        ------------------------------------------------
        @param company_id: current company id.
        @param wh_id: the selected warehouse id.
        @return: list of locations with 3D properties
        """
        warehouse = request.env['stock.warehouse'].sudo().browse(int(wh_id))
        
        # Get all internal locations that have 3D properties
        locations = request.env['stock.location'].sudo().search([
            ('warehouse_id', '=', int(wh_id)),
            ('usage', '=', 'internal'),
            ('active', '=', True),
        ])
        
        locations_data = []
        for loc in locations:
            # Skip parent/root locations
            if loc.id in (
                warehouse.lot_stock_id.id, 
                warehouse.wh_input_stock_loc_id.id,
                warehouse.wh_qc_stock_loc_id.id,
                warehouse.wh_pack_stock_loc_id.id, 
                warehouse.wh_output_stock_loc_id.id):
                continue
            
            # Only include locations with 3D config
            if loc.loc_length > 0 or loc.loc_width > 0 or loc.loc_height > 0:
                locations_data.append({
                    'id': loc.id,
                    'name': loc.name,
                    'loc_3d_code': loc.loc_3d_code or loc.name,
                    'loc_pos_x': float(loc.loc_pos_x or 0),
                    'loc_pos_y': float(loc.loc_pos_y or 0),
                    'loc_pos_z': float(loc.loc_pos_z or 0),
                    'loc_length': float(loc.loc_length or 100),
                    'loc_width': float(loc.loc_width or 80),
                    'loc_height': float(loc.loc_height or 200),
                    'loc_max_capacity': float(loc.loc_max_capacity or 0),
                })
        
        return locations_data

    @http.route('/3Dstock/data/products', type='json', auth='public')
    def get_product_positions_3d(self, company_id, wh_id):
        """
        NEW: Get product/lot 3D positions from warehouse_map integration
        Returns actual quants with their posx, posy, posz positions
        ------------------------------------------------
        @param company_id: current company id.
        @param wh_id: the selected warehouse id.
        @return: list of products with 3D positions from warehouse_map
        """
        warehouse = request.env['stock.warehouse'].sudo().browse(int(wh_id))
        
        # Get all quants with positions in this warehouse
        quants = request.env['stock.quant'].sudo().search([
            ('location_id', 'child_of', warehouse.lot_stock_id.id),
            ('quantity', '>', 0),
            ('display_on_map', '=', True),
            ('product_id.tracking', 'in', ['lot', 'serial']),
        ])
        
        products_data = []
        for quant in quants:
            # Use warehouse_map positions (posx, posy, posz)
            # Convert to 3D coordinates (scale up for visibility)
            scale = 30  # Pixel to 3D unit scale
            products_data.append({
                'id': quant.id,
                'product_name': quant.product_id.display_name,
                'lot_name': quant.lot_id.name if quant.lot_id else 'N/A',
                'quantity': quant.quantity,
                'pos_x': quant.posx * scale,
                'pos_y': quant.posz * scale * 2,  # Z in warehouse_map becomes Y in 3D (height)
                'pos_z': quant.posy * scale,
                'location_name': quant.location_id.complete_name,
                # Color based on quantity/status
                'color': self._get_quant_color(quant),
            })
        
        return products_data
    
    def _get_quant_color(self, quant):
        """Determine color for product box in 3D based on status"""
        # Can customize based on product category, low stock, etc.
        if quant.quantity > 100:
            return 0x00802b  # Green - High stock
        elif quant.quantity > 50:
            return 0xe6b800  # Yellow - Medium stock
        elif quant.quantity > 0:
            return 0xcc0000  # Red - Low stock
        return 0x8c8c8c  # Gray - Empty

    @http.route('/3Dstock/data', type='json', auth='public')
    def get_stock_data(self, company_id, wh_id):
        """
        LEGACY: Get location box data for 3D warehouse structure
        This shows the location boxes (shelves/racks) as background
        ------------------------------------------------
        @param company_id: current company id.
        @param wh_id: the selected warehouse id.
        @return: list of locations with their 3D dimensions and positions
        """
        warehouse = request.env['stock.warehouse'].sudo().search(
            [('id', '=', int(wh_id)), ('company_id', '=', int(company_id))])
        locations = request.env['stock.location'].sudo().search(
            [('company_id', '=', int(company_id)),
             ('active', '=', True),
             ('usage', '=', 'internal'),
             ('loc_3d_code', '!=', False)])  # Only locations with 3D config
        
        location_dict = {}
        for loc in locations:
            if loc.warehouse_id.id == warehouse.id:
                # Skip special locations
                if loc.id not in (
                        warehouse.lot_stock_id.id, 
                        warehouse.wh_input_stock_loc_id.id,
                        warehouse.wh_qc_stock_loc_id.id,
                        warehouse.wh_pack_stock_loc_id.id, 
                        warehouse.wh_output_stock_loc_id.id):
                    
                    # Use renamed fields (loc_length, loc_width, etc.)
                    length = int(loc.loc_length * 3.779 * 2) if loc.loc_length else 50
                    width = int(loc.loc_width * 3.779 * 2) if loc.loc_width else 50
                    height = int(loc.loc_height * 3.779 * 2) if loc.loc_height else 50
                    
                    location_dict.update({
                        loc.loc_3d_code: [
                            loc.loc_pos_x or 0, 
                            loc.loc_pos_y or 0, 
                            loc.loc_pos_z or 0,
                            length, width, height
                        ]
                    })

        return location_dict

    @http.route('/3Dstock/save-shelf', type='json', auth='user')
    def save_shelf(self, company_id, wh_id, shelf_code, loc_length, loc_width, loc_height, loc_pos_x, loc_pos_y, loc_pos_z):
        """
        Create a new shelf/location with 3D properties
        ------------------------------------------------
        @param company_id: the current company id.
        @param wh_id: the warehouse id.
        @param shelf_code: the shelf code/name.
        @param loc_length: shelf length (X).
        @param loc_width: shelf width (Z).
        @param loc_height: shelf height (Y).
        @param loc_pos_x: shelf position X.
        @param loc_pos_y: shelf position Y.
        @param loc_pos_z: shelf position Z.
        @return: success message or error.
        """
        try:
            # Get warehouse object
            warehouse = request.env['stock.warehouse'].sudo().browse(int(wh_id))
            if not warehouse:
                return {
                    'success': False,
                    'message': 'Warehouse not found'
                }
            
            # Get stock location
            stock_location = warehouse.lot_stock_id
            
            # Create new location (shelf)
            location = request.env['stock.location'].sudo().create({
                'name': shelf_code,
                'loc_3d_code': shelf_code,
                'parent_location_id': stock_location.id,
                'usage': 'internal',
                'active': True,
                'company_id': int(company_id),
                'warehouse_id': int(wh_id),
                # 3D properties
                'loc_length': float(loc_length),
                'loc_width': float(loc_width),
                'loc_height': float(loc_height),
                'loc_pos_x': float(loc_pos_x),
                'loc_pos_y': float(loc_pos_y),
                'loc_pos_z': float(loc_pos_z),
            })
            
            return {
                'success': True,
                'message': f'Shelf "{shelf_code}" created successfully',
                'shelf_id': location.id,
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error creating shelf: {str(e)}'
            }

    @http.route('/3Dstock/save-position', type='json', auth='user')
    def save_product_position(self, company_id, wh_id, product_id, pos_x, pos_y, pos_z):
        """
        Save product position to stock.quant (warehouse_map integration)
        Saves position for all quants of this product in the warehouse
        ------------------------------------------------
        @param company_id: the current company id.
        @param wh_id: the warehouse id.
        @param product_id: the product id to assign position to.
        @param pos_x: X coordinate.
        @param pos_y: Y coordinate.
        @param pos_z: Z coordinate.
        @return: success message or error.
        """
        try:
            # Get warehouse object
            warehouse = request.env['stock.warehouse'].sudo().browse(int(wh_id))
            if not warehouse:
                return {
                    'success': False,
                    'message': 'Warehouse not found'
                }
            
            # Get product object
            product = request.env['product.product'].sudo().browse(int(product_id))
            if not product:
                return {
                    'success': False,
                    'message': 'Product not found'
                }
            
            # Find all stock.quant records for this product in this warehouse
            # that have quantities > 0 and are in internal locations
            quants = request.env['stock.quant'].sudo().search([
                ('product_id', '=', int(product_id)),
                ('warehouse_id', '=', int(wh_id)),
                ('quantity', '>', 0),
                ('location_id.usage', '=', 'internal'),
            ])
            
            if not quants:
                return {
                    'success': False,
                    'message': f'No stock found for product {product.name} in warehouse {warehouse.name}'
                }
            
            # Update all matching quants with the new position
            # Using warehouse_map's posx, posy, posz fields
            for quant in quants:
                quant.sudo().write({
                    'posx': float(pos_x),
                    'posy': float(pos_y),
                    'posz': float(pos_z),
                })
            
            return {
                'success': True,
                'message': f'Position assigned to {len(quants)} quant(s) for {product.name}',
                'updated_count': len(quants),
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error saving position: {str(e)}'
            }

    @http.route('/3Dstock/data/quantity', type='json', auth='public')
    def get_stock_count_data(self, loc_code):
        """
        Get stock quantity for a location (for color coding location boxes)
        ------------------------------------------------
        @param loc_code: the selected location code.
        @return: current quantity vs capacity data
        """
        quantity = request.env['stock.quant'].sudo().search(
            [('location_id.loc_3d_code', '=', loc_code)]).mapped('quantity')
        
        location = request.env['stock.location'].sudo().search(
            [('loc_3d_code', '=', loc_code)], limit=1)
        
        capacity = location.loc_max_capacity if location else 0
        count = math.fsum(quantity)
        quant_data = (0, 0)
        
        if capacity:
            if capacity > 0:
                load = int((count * 100) / capacity)
                quant_data = (capacity, load)
            else:
                if count > 0:
                    quant_data = (0, -1)
        return quant_data

    @http.route('/3Dstock/data/product', type='json', auth='public')
    def get_stock_product_data(self, loc_code):
        """
        Get detailed product data for a location
        ------------------------------------------------
        @param loc_code: the selected location code.
        @return: dictionary with products, capacity, available space
        """
        products = request.env['stock.quant'].sudo().search(
            [('location_id.loc_3d_code', '=', loc_code)])
        
        quantity_obj = request.env['stock.quant'].sudo().search(
            [('location_id.loc_3d_code', '=', loc_code)]).mapped('quantity')
        
        location = request.env['stock.location'].sudo().search(
            [('loc_3d_code', '=', loc_code)], limit=1)
        
        capacity = location.loc_max_capacity if location else 0
        product_list = []
        
        if products:
            for rec in products:
                lot_info = f" [{rec.lot_id.name}]" if rec.lot_id else ""
                product_list.append((
                    rec.product_id.display_name + lot_info, 
                    rec.quantity
                ))
        
        load = math.fsum(quantity_obj)
        space = capacity - load if capacity > 0 else 0
        
        data = {
            'capacity': capacity,
            'space': space,
            'product_list': product_list
        }
        return data

    @http.route('/3Dstock/data/standalone', type='json', auth='public')
    def get_standalone_stock_data(self, company_id, loc_id):
        """
        Get location data for individual location 3D view
        ------------------------------------------------
        @param company_id: the current company id.
        @param loc_id: the selected location id.
        @return: dictionary of location dimensions and positions
        """
        location = request.env['stock.location'].sudo().browse(int(loc_id))
        warehouse = location.warehouse_id
        
        locations = request.env['stock.location'].sudo().search(
            [('company_id.id', '=', int(company_id)),
             ('active', '=', True),
             ('usage', '=', 'internal'),
             ('warehouse_id', '=', warehouse.id)])
        
        location_dict = {}
        for loc in locations:
            if loc.loc_3d_code:
                length = int(loc.loc_length * 3.779 * 2) if loc.loc_length else 50
                width = int(loc.loc_width * 3.779 * 2) if loc.loc_width else 50
                height = int(loc.loc_height * 3.779 * 2) if loc.loc_height else 50
                
                location_dict.update({
                    loc.loc_3d_code: [
                        loc.loc_pos_x or 0, 
                        loc.loc_pos_y or 0, 
                        loc.loc_pos_z or 0,
                        length, width, height, loc.id
                    ]
                })
        
        return location_dict
