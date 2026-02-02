# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json

class Warehouse3DController(http.Controller):

    @http.route('/warehouse_3d/get_layout', type='json', auth='user')
    def get_warehouse_layout(self, area_id=None, shelf_id=None):
        """Get complete warehouse layout with bins and inventory"""
        Location = request.env['stock.location']
        
        domain = [('usage', '=', 'internal'), ('shelf_id', '!=', False)]
        if area_id:
            domain.append(('area_id', '=', int(area_id)))
        if shelf_id:
            domain.append(('shelf_id', '=', int(shelf_id)))
        
        bins = Location.search(domain)
        
        return {
            'bins': [bin.get_bin_details() for bin in bins],
            'areas': self._get_areas(),
            'shelves': self._get_shelves(area_id),
        }

    @http.route('/warehouse_3d/get_bin_detail', type='json', auth='user')
    def get_bin_detail(self, bin_id):
        """Get detailed information for a specific bin"""
        bin = request.env['stock.location'].browse(int(bin_id))
        if not bin.exists():
            return {'error': 'Bin not found'}
        return bin.get_bin_details()

    @http.route('/warehouse_3d/save_layout', type='json', auth='user')
    def save_warehouse_layout(self, areas=None, shelves=None):
        """Save warehouse layout changes (2D Designer)
        📌 SKUSavvy rule: Persist structure, DO NOT touch inventory (stock.quant)"""
        result = {'success': True, 'errors': []}
        
        # Save area changes
        if areas:
            for area_data in areas:
                try:
                    if area_data.get('id'):
                        area = request.env['warehouse.area'].browse(area_data['id'])
                        area.write({
                            'position_x': area_data.get('position_x'),
                            'position_y': area_data.get('position_y'),
                            'width': area_data.get('width'),
                            'height': area_data.get('height'),
                            'boundary': area_data.get('boundary'),
                        })
                except Exception as e:
                    result['errors'].append(f"Area {area_data.get('id')}: {str(e)}")
        
        # Save shelf changes
        if shelves:
            for shelf_data in shelves:
                try:
                    if shelf_data.get('id'):
                        shelf = request.env['warehouse.shelf'].browse(shelf_data['id'])
                        shelf.write({
                            'position_x': shelf_data.get('position_x'),
                            'position_y': shelf_data.get('position_y'),
                            'orientation': shelf_data.get('orientation'),
                            'rotation': shelf_data.get('rotation'),
                        })
                except Exception as e:
                    result['errors'].append(f"Shelf {shelf_data.get('id')}: {str(e)}")
        
        return result

    @http.route('/warehouse_3d/create_area', type='json', auth='user')
    def create_area(self, name, code, warehouse_id, area_type, **kwargs):
        """Create new warehouse area"""
        try:
            area = request.env['warehouse.area'].create({
                'name': name,
                'code': code,
                'warehouse_id': int(warehouse_id),
                'area_type': area_type,
                'position_x': kwargs.get('position_x', 0),
                'position_y': kwargs.get('position_y', 0),
                'width': kwargs.get('width', 10),
                'height': kwargs.get('height', 10),
                'boundary': kwargs.get('boundary'),
            })
            return {'success': True, 'area_id': area.id}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/warehouse_3d/create_shelf', type='json', auth='user')
    def create_shelf(self, name, code, area_id, **kwargs):
        """Create new shelf with auto-bin generation"""
        try:
            shelf = request.env['warehouse.shelf'].create({
                'name': name,
                'code': code,
                'area_id': int(area_id),
                'position_x': kwargs.get('position_x', 0),
                'position_y': kwargs.get('position_y', 0),
                'width': kwargs.get('width', 1.2),
                'depth': kwargs.get('depth', 1.0),
                'height': kwargs.get('height', 2.5),
                'orientation': kwargs.get('orientation', 'horizontal'),
                'level_count': kwargs.get('level_count', 4),
                'bins_per_level': kwargs.get('bins_per_level', 2),
            })
            # Bins are auto-created by _create_bins() in create() method
            return {'success': True, 'shelf_id': shelf.id, 'bin_count': shelf.bin_count}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _get_areas(self):
        """Get all warehouse areas"""
        areas = request.env['warehouse.area'].search([('active', '=', True)])
        return [{
            'id': area.id,
            'name': area.name,
            'code': area.code,
            'area_type': area.area_type,
            'color': area.color,
            'position_x': area.position_x,
            'position_y': area.position_y,
            'width': area.width,
            'height': area.height,
            'boundary': area.boundary,
        } for area in areas]

    def _get_shelves(self, area_id=None):
        """Get shelves for specified area"""
        domain = [('active', '=', True)]
        if area_id:
            domain.append(('area_id', '=', int(area_id)))
        
        shelves = request.env['warehouse.shelf'].search(domain)
        return [{
            'id': shelf.id,
            'name': shelf.name,
            'code': shelf.code,
            'area_id': shelf.area_id.id,
            'area_type': shelf.area_id.area_type,
            'position_x': shelf.position_x,
            'position_y': shelf.position_y,
            'width': shelf.width,
            'depth': shelf.depth,
            'height': shelf.height,
            'orientation': shelf.orientation,
            'rotation': shelf.rotation,
            'level_count': shelf.level_count,
            'bins_per_level': shelf.bins_per_level,
            'bin_count': shelf.bin_count,
        } for shelf in shelves]

    @http.route('/warehouse_3d/putaway', type='json', auth='user')
    def putaway_product(self, bin_id, product_id, quantity, lot_id=None, **kwargs):
        """Putaway operation: Assign product to bin
        📌 3D Edit = Manipulate stock.quant, NOT layout"""
        try:
            bin_location = request.env['stock.location'].browse(int(bin_id))
            if not bin_location.exists() or bin_location.usage != 'internal':
                return {'success': False, 'error': 'Invalid bin location'}
            
            if bin_location.is_blocked:
                return {'success': False, 'error': f'Bin is blocked: {bin_location.block_reason}'}
            
            # Check if bin has capacity
            current_qty = sum(bin_location.quant_ids.mapped('quantity'))
            if current_qty + quantity > bin_location.max_capacity:
                return {'success': False, 'error': 'Bin capacity exceeded'}
            
            # Create or update stock.quant
            Quant = request.env['stock.quant']
            domain = [
                ('location_id', '=', bin_location.id),
                ('product_id', '=', int(product_id)),
            ]
            if lot_id:
                domain.append(('lot_id', '=', int(lot_id)))
            
            quant = Quant.search(domain, limit=1)
            if quant:
                quant.quantity += quantity
            else:
                Quant.create({
                    'location_id': bin_location.id,
                    'product_id': int(product_id),
                    'lot_id': int(lot_id) if lot_id else False,
                    'quantity': quantity,
                })
            
            return {
                'success': True,
                'bin_state': bin_location.bin_state,
                'message': f'Putaway {quantity} units to {bin_location.name}'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/warehouse_3d/pick', type='json', auth='user')
    def pick_product(self, bin_id, product_id, quantity, lot_id=None):
        """Pick operation: Remove product from bin
        📌 3D Edit = Manipulate stock.quant"""
        try:
            bin_location = request.env['stock.location'].browse(int(bin_id))
            if not bin_location.exists():
                return {'success': False, 'error': 'Bin not found'}
            
            # Find quant
            Quant = request.env['stock.quant']
            domain = [
                ('location_id', '=', bin_location.id),
                ('product_id', '=', int(product_id)),
            ]
            if lot_id:
                domain.append(('lot_id', '=', int(lot_id)))
            
            quant = Quant.search(domain, limit=1)
            if not quant:
                return {'success': False, 'error': 'Product not found in bin'}
            
            if quant.available_quantity < quantity:
                return {'success': False, 'error': f'Insufficient quantity (available: {quant.available_quantity})'}
            
            # Reduce quantity
            quant.quantity -= quantity
            if quant.quantity <= 0:
                quant.unlink()
            
            return {
                'success': True,
                'bin_state': bin_location.bin_state,
                'message': f'Picked {quantity} units from {bin_location.name}'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/warehouse_3d/move_inventory', type='json', auth='user')
    def move_inventory(self, from_bin_id, to_bin_id, product_id, quantity, lot_id=None):
        """Move inventory between bins
        📌 3D Edit = Manipulate stock.quant between locations"""
        try:
            # Pick from source
            pick_result = self.pick_product(from_bin_id, product_id, quantity, lot_id)
            if not pick_result['success']:
                return pick_result
            
            # Putaway to destination
            putaway_result = self.putaway_product(to_bin_id, product_id, quantity, lot_id)
            if not putaway_result['success']:
                # Rollback: put back to source
                self.putaway_product(from_bin_id, product_id, quantity, lot_id)
                return putaway_result
            
            from_bin = request.env['stock.location'].browse(int(from_bin_id))
            to_bin = request.env['stock.location'].browse(int(to_bin_id))
            
            return {
                'success': True,
                'message': f'Moved {quantity} units from {from_bin.name} to {to_bin.name}'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/warehouse_3d/block_bin', type='json', auth='user')
    def block_bin(self, bin_id, reason):
        """Block bin from receiving inventory (business logic operation)"""
        try:
            bin_location = request.env['stock.location'].browse(int(bin_id))
            if not bin_location.exists():
                return {'success': False, 'error': 'Bin not found'}
            
            bin_location.write({
                'is_blocked': True,
                'block_reason': reason,
            })
            
            return {
                'success': True,
                'message': f'Bin {bin_location.name} blocked',
                'bin_state': bin_location.bin_state
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/warehouse_3d/unblock_bin', type='json', auth='user')
    def unblock_bin(self, bin_id):
        """Unblock bin"""
        try:
            bin_location = request.env['stock.location'].browse(int(bin_id))
            if not bin_location.exists():
                return {'success': False, 'error': 'Bin not found'}
            
            bin_location.write({
                'is_blocked': False,
                'block_reason': False,
            })
            
            return {
                'success': True,
                'message': f'Bin {bin_location.name} unblocked',
                'bin_state': bin_location.bin_state
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/warehouse_3d/assign_move_line_to_bin', type='json', auth='user')
    def assign_move_line_to_bin(self, move_line_id, bin_id):
        """Assign stock.move.line to specific bin
        📌 Integration with Odoo 18 Incoming Picking workflow
        📌 This sets destination, does NOT validate picking
        
        Flow:
        1. User opens picking
        2. Clicks "🏗️ 3D Putaway" button
        3. Selects product + bin in 3D view
        4. This endpoint updates move_line.location_dest_id
        5. User validates picking normally
        6. Odoo creates stock.quant at assigned bin
        7. 3D view shows updated bin color
        """
        try:
            MoveLine = request.env['stock.move.line']
            move_line = MoveLine.browse(int(move_line_id))
            
            if not move_line.exists():
                return {'success': False, 'error': 'Move line not found'}
            
            # Call move line method to assign bin
            result = move_line.action_assign_to_bin_3d(int(bin_id))
            
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
