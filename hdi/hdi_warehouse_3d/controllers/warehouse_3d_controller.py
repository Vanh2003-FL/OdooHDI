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

    def _get_areas(self):
        """Get all warehouse areas"""
        areas = request.env['warehouse.area'].search([('active', '=', True)])
        return [{
            'id': area.id,
            'name': area.name,
            'code': area.code,
            'color': area.color,
            'position_x': area.position_x,
            'position_y': area.position_y,
            'width': area.width,
            'height': area.height,
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
            'position_x': shelf.position_x,
            'position_y': shelf.position_y,
            'width': shelf.width,
            'depth': shelf.depth,
            'height': shelf.height,
            'level_count': shelf.level_count,
        } for shelf in shelves]
