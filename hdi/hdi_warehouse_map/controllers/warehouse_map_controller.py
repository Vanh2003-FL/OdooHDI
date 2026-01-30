# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json


class WarehouseMapController(http.Controller):
    
    @http.route('/warehouse_map/get_data', type='json', auth='user')
    def get_warehouse_data(self, warehouse_id=None, **kwargs):
        """Get warehouse structure data for visualization"""
        
        domain = []
        if warehouse_id:
            domain = [('warehouse_id', '=', warehouse_id)]
        
        Bin = request.env['warehouse.bin']
        bins = Bin.search(domain)
        
        # Prepare data structure
        warehouse_data = {
            'zones': [],
            'bins': [],
        }
        
        # Get zones with structure
        zones = bins.mapped('zone_id')
        for zone in zones:
            zone_data = {
                'id': zone.id,
                'code': zone.code,
                'name': zone.name,
                'color': zone.color,
                'position_x': zone.position_x,
                'position_y': zone.position_y,
                'width': zone.width,
                'height': zone.height,
                'aisles': [],
            }
            
            for aisle in zone.aisle_ids:
                aisle_data = {
                    'id': aisle.id,
                    'code': aisle.code,
                    'name': aisle.name,
                    'position_x': aisle.position_x,
                    'position_y': aisle.position_y,
                    'racks': [],
                }
                
                for rack in aisle.rack_ids:
                    rack_data = {
                        'id': rack.id,
                        'code': rack.code,
                        'name': rack.name,
                        'position_x': rack.position_x,
                        'position_y': rack.position_y,
                        'position_z': rack.position_z,
                        'width': rack.width,
                        'depth': rack.depth,
                        'height': rack.height,
                        'levels': [],
                    }
                    
                    for level in rack.level_ids:
                        level_data = {
                            'id': level.id,
                            'code': level.code,
                            'name': level.name,
                            'level_number': level.level_number,
                            'height_from_ground': level.height_from_ground,
                            'bins': [],
                        }
                        
                        for bin in level.bin_ids:
                            bin_data = {
                                'id': bin.id,
                                'code': bin.code,
                                'name': bin.complete_name,
                                'coordinate_x': bin.coordinate_x,
                                'coordinate_y': bin.coordinate_y,
                                'coordinate_z': bin.coordinate_z,
                                'width': bin.width,
                                'depth': bin.depth,
                                'height': bin.height,
                                'state': bin.state,
                                'color': bin.display_color,
                                'is_blocked': bin.is_blocked,
                                'current_sku': bin.current_sku or '',
                                'current_lot': bin.current_lot_id.name if bin.current_lot_id else '',
                                'quantity': bin.total_quantity,
                                'utilization': bin.capacity_utilization,
                            }
                            level_data['bins'].append(bin_data)
                            warehouse_data['bins'].append(bin_data)
                        
                        rack_data['levels'].append(level_data)
                    
                    aisle_data['racks'].append(rack_data)
                
                zone_data['aisles'].append(aisle_data)
            
            warehouse_data['zones'].append(zone_data)
        
        return warehouse_data
    
    @http.route('/warehouse_map/get_bin_details', type='json', auth='user')
    def get_bin_details(self, bin_id, **kwargs):
        """Get detailed information about a specific bin"""
        
        Bin = request.env['warehouse.bin']
        bin = Bin.browse(bin_id)
        
        if not bin.exists():
            return {'error': 'Bin not found'}
        
        quants_data = []
        for quant in bin.quant_ids.filtered(lambda q: q.quantity > 0):
            quants_data.append({
                'product_id': quant.product_id.id,
                'product_name': quant.product_id.display_name,
                'sku': quant.product_id.default_code or '',
                'lot_name': quant.lot_id.name if quant.lot_id else '',
                'quantity': quant.quantity,
                'reserved_quantity': quant.reserved_quantity,
                'available_quantity': quant.available_quantity,
                'uom': quant.product_uom_id.name,
            })
        
        return {
            'id': bin.id,
            'complete_name': bin.complete_name,
            'state': bin.state,
            'is_blocked': bin.is_blocked,
            'block_reason': bin.block_reason or '',
            'current_sku': bin.current_sku or '',
            'current_lot': bin.current_lot_id.name if bin.current_lot_id else '',
            'total_quantity': bin.total_quantity,
            'capacity': bin.capacity,
            'used_capacity': bin.used_capacity,
            'utilization': bin.capacity_utilization,
            'quants': quants_data,
        }
    
    @http.route('/warehouse_map/highlight_bins', type='json', auth='user')
    def highlight_bins(self, bin_ids, **kwargs):
        """Get highlighting information for specific bins"""
        
        Bin = request.env['warehouse.bin']
        bins = Bin.browse(bin_ids)
        
        result = []
        for bin in bins:
            result.append({
                'id': bin.id,
                'complete_name': bin.complete_name,
                'coordinate_x': bin.coordinate_x,
                'coordinate_y': bin.coordinate_y,
                'coordinate_z': bin.coordinate_z,
            })
        
        return result
