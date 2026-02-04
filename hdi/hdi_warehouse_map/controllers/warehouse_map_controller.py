# -*- coding: utf-8 -*-
"""
🌐 Warehouse Map API Controllers
Provides JSON API for 2D/3D warehouse visualization
"""

from odoo import http
from odoo.http import request
import json


class WarehouseMapController(http.Controller):
    
    @http.route('/warehouse_map/layout/<int:warehouse_id>', type='json', auth='user')
    def get_warehouse_layout(self, warehouse_id):
        """
        📡 API: Get complete warehouse layout data for rendering
        Returns hierarchical JSON structure for 2D/3D viewers
        """
        layout_model = request.env['stock.location.layout']
        data = layout_model.get_warehouse_layout_data(warehouse_id)
        return data
    
    @http.route('/warehouse_map/scan_serial', type='json', auth='user')
    def scan_serial_highlight_bin(self, serial_number):
        """
        🔦 API: Scan serial number and return bin locations to highlight
        
        Workflow:
        1. Scan Serial → Find lot_id
        2. Read stock.quant
        3. Get location_id (bin)
        4. Return layout info for highlighting
        """
        layout_model = request.env['stock.location.layout']
        result = layout_model.highlight_bin_by_serial(serial_number)
        return result
    
    @http.route('/warehouse_map/bin_details/<int:location_id>', type='json', auth='user')
    def get_bin_details(self, location_id):
        """
        📦 API: Get details of a bin (when clicked on map)
        Returns: lots/serials in this bin
        
        Domain: stock.quant(location_id=bin, lot_id!=False)
        """
        quants = request.env['stock.quant'].search([
            ('location_id', '=', location_id),
            ('quantity', '>', 0)
        ])
        
        lots_data = []
        for quant in quants:
            lot_data = {
                'quant_id': quant.id,
                'product_id': quant.product_id.id,
                'product_name': quant.product_id.name,
                'product_code': quant.product_id.default_code or '',
                'quantity': quant.quantity,
                'reserved_quantity': quant.reserved_quantity,
                'available_quantity': quant.quantity - quant.reserved_quantity,
                'uom': quant.product_uom_id.name,
            }
            
            if quant.lot_id:
                lot_data.update({
                    'lot_id': quant.lot_id.id,
                    'lot_name': quant.lot_id.name,
                    'lot_ref': quant.lot_id.ref or '',
                })
            
            lots_data.append(lot_data)
        
        location = request.env['stock.location'].browse(location_id)
        
        return {
            'location_id': location_id,
            'location_name': location.name,
            'location_complete_name': location.complete_name,
            'quants': lots_data,
            'total_quantity': sum(quants.mapped('quantity')),
            'lot_count': len(quants.filtered('lot_id')),
        }
    
    @http.route('/warehouse_map/heatmap/<int:warehouse_id>', type='json', auth='user')
    def get_warehouse_heatmap(self, warehouse_id):
        """
        🌡️ API: Get heatmap data for warehouse visualization
        Returns quantity percentage for each location
        """
        quant_model = request.env['stock.quant']
        heatmap_data = quant_model.get_heatmap_data(warehouse_id)
        return heatmap_data
    
    @http.route('/warehouse_map/update_layout', type='json', auth='user', methods=['POST'])
    def update_layout(self, layout_id, x, y, width=None, height=None, rotation=None):
        """
        ✏️ API: Update layout position (for drag & drop editor)
        """
        layout = request.env['stock.location.layout'].browse(layout_id)
        if not layout.exists():
            return {'error': 'Layout not found'}
        
        vals = {'x': x, 'y': y}
        if width is not None:
            vals['width'] = width
        if height is not None:
            vals['height'] = height
        if rotation is not None:
            vals['rotation'] = rotation
        
        layout.write(vals)
        
        return {
            'success': True,
            'layout_json': json.loads(layout.layout_json)
        }
    
    @http.route('/warehouse_map/search_product', type='json', auth='user')
    def search_product_in_warehouse(self, warehouse_id, product_name):
        """
        🔍 API: Search product and highlight bins containing it
        """
        warehouse = request.env['stock.warehouse'].browse(warehouse_id)
        
        products = request.env['product.product'].search([
            '|',
            ('name', 'ilike', product_name),
            ('default_code', 'ilike', product_name)
        ])
        
        if not products:
            return {'error': 'Product not found'}
        
        quants = request.env['stock.quant'].search([
            ('product_id', 'in', products.ids),
            ('location_id', 'child_of', warehouse.lot_stock_id.id),
            ('quantity', '>', 0)
        ])
        
        # Find bin layouts
        location_ids = quants.mapped('location_id').ids
        bin_layouts = request.env['stock.location.layout'].search([
            ('location_id', 'in', location_ids),
            ('location_type', '=', 'bin')
        ])
        
        results = []
        for layout in bin_layouts:
            bin_quants = quants.filtered(lambda q: q.location_id == layout.location_id)
            results.append({
                'layout_id': layout.id,
                'location_id': layout.location_id.id,
                'location_name': layout.location_id.complete_name,
                'x': layout.x,
                'y': layout.y,
                'z': layout.z_level,
                'products': [{
                    'product_id': q.product_id.id,
                    'product_name': q.product_id.name,
                    'quantity': q.quantity,
                } for q in bin_quants]
            })
        
        return {'bins': results}
