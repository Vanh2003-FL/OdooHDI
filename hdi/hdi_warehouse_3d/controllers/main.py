# -*- coding: utf-8 -*-
"""
API Controllers for Warehouse 3D Visualization
Provides HTTP endpoints for 3D viewer, heatmap, and route data
"""
from odoo import http
from odoo.http import request
import json


class Warehouse3DController(http.Controller):
    """HTTP API for warehouse 3D visualization"""
    
    @http.route('/warehouse_3d/layout/<int:layout_id>', type='json', auth='user')
    def get_layout_data(self, layout_id, **kwargs):
        """
        Get complete warehouse layout structure for 3D rendering
        
        Returns:
            dict: Layout with zones, aisles, racks, shelves, bins
        """
        Layout = request.env['warehouse.layout'].sudo()
        layout = Layout.browse(layout_id)
        
        if not layout.exists():
            return {'error': 'Layout not found', 'code': 404}
        
        return layout.get_layout_info()
    
    @http.route('/warehouse_3d/bins/<int:layout_id>', type='json', auth='user')
    def get_bins_data(self, layout_id, limit=5000, **kwargs):
        """
        Get all bins with current stock status
        
        Args:
            layout_id: warehouse.layout ID
            limit: max bins to return (performance)
        
        Returns:
            list: [{bin_id, name, position, status, quantity, weight}, ...]
        """
        Layout = request.env['warehouse.layout'].sudo()
        Bin = request.env['warehouse.bin'].sudo()
        
        layout = Layout.browse(layout_id)
        if not layout.exists():
            return {'error': 'Layout not found', 'code': 404}
        
        # Get all locations in layout zones
        location_ids = layout.zone_ids.location_ids.ids
        
        # Get bins for these locations
        bins = Bin.search([('location_id', 'in', location_ids)], limit=limit)
        
        bin_data = []
        for bin_rec in bins:
            bin_data.append({
                'id': bin_rec.id,
                'name': bin_rec.name,
                'position': {
                    'x': bin_rec.pos_x,
                    'y': bin_rec.pos_y,
                    'z': bin_rec.shelf_id.pos_z if bin_rec.shelf_id else 0
                },
                'dimensions': {
                    'width': bin_rec.bin_width,
                    'depth': bin_rec.bin_depth,
                    'height': bin_rec.bin_height
                },
                'status': bin_rec.bin_status,
                'quantity': bin_rec.total_quantity,
                'weight': bin_rec.total_weight,
                'utilization': (bin_rec.total_weight / bin_rec.max_weight * 100) if bin_rec.max_weight > 0 else 0,
                'location_id': bin_rec.location_id.id,
                'location_name': bin_rec.location_id.name
            })
        
        return {
            'bins': bin_data,
            'total_count': len(bins),
            'truncated': len(bins) >= limit
        }
    
    @http.route('/warehouse_3d/heatmap/<int:layout_id>', type='json', auth='user')
    def get_heatmap_data(self, layout_id, days=30, **kwargs):
        """
        Get heatmap data showing pick frequency
        
        Args:
            layout_id: warehouse.layout ID
            days: number of days to analyze
        
        Returns:
            dict: {heatmap_data: {bin_id: pick_count}, statistics: {...}}
        """
        Layout = request.env['warehouse.layout'].sudo()
        Heatmap = request.env['warehouse.heatmap'].sudo()
        
        layout = Layout.browse(layout_id)
        if not layout.exists():
            return {'error': 'Layout not found', 'code': 404}
        
        # Get or create today's heatmap
        today = http.request.env.context.get('today') or request.env['ir.fields'].Date.today()
        heatmap = Heatmap.search([
            ('layout_id', '=', layout_id),
            ('date', '=', today)
        ], limit=1)
        
        if not heatmap:
            heatmap = Heatmap.create({
                'layout_id': layout_id,
                'date': today
            })
            heatmap.generate_heatmap(days=days)
        
        return {
            'heatmap_data': heatmap.heatmap_data or {},
            'statistics': {
                'total_picks': heatmap.total_picks,
                'max_picks': heatmap.max_picks,
                'avg_picks': heatmap.avg_picks,
                'date': str(heatmap.date)
            }
        }
    
    @http.route('/warehouse_3d/metrics/<int:layout_id>', type='json', auth='user')
    def get_metrics_data(self, layout_id, **kwargs):
        """
        Get warehouse performance metrics
        
        Returns:
            dict: Daily metrics including efficiency score, utilization, bottlenecks
        """
        Layout = request.env['warehouse.layout'].sudo()
        Metrics = request.env['warehouse.metrics'].sudo()
        
        layout = Layout.browse(layout_id)
        if not layout.exists():
            return {'error': 'Layout not found', 'code': 404}
        
        # Get today's metrics
        today = request.env['ir.fields'].Date.today()
        metrics = Metrics.search([
            ('layout_id', '=', layout_id),
            ('date', '=', today)
        ], limit=1)
        
        if not metrics:
            metrics = Metrics.create({
                'layout_id': layout_id,
                'date': today
            })
            metrics.generate_metrics(date=today)
        
        return {
            'date': str(metrics.date),
            'picking_metrics': {
                'total_picks': metrics.total_picks,
                'avg_pick_time': metrics.avg_pick_time,
                'total_distance': metrics.total_distance
            },
            'inventory_metrics': {
                'empty_bins': metrics.empty_bins,
                'partial_bins': metrics.partial_bins,
                'full_bins': metrics.full_bins,
                'utilization_percentage': metrics.bin_utilization_percentage
            },
            'efficiency': {
                'score': metrics.efficiency_score,
                'bottleneck_zones': metrics.bottleneck_zones or []
            }
        }
    
    @http.route('/warehouse_3d/route/<int:picking_id>', type='json', auth='user')
    def get_picking_route(self, picking_id, **kwargs):
        """
        Get optimized picking route for a picking order
        
        Returns:
            dict: Route with sequence, distance, estimated time
        """
        Picking = request.env['stock.picking'].sudo()
        
        picking = Picking.browse(picking_id)
        if not picking.exists():
            return {'error': 'Picking not found', 'code': 404}
        
        # Optimize route if not already done
        if not picking.route_id:
            picking.optimize_picking_route()
        
        if not picking.route_id:
            return {'error': 'No route generated', 'code': 400}
        
        route = picking.route_id
        route_display = route.get_route_display()
        
        return {
            'picking_id': picking.id,
            'picking_name': picking.name,
            'route_type': route.route_type,
            'route_sequence': route_display,
            'distance': route.route_distance,
            'estimated_time': route.estimated_time,
            'bin_count': route.bin_count
        }
    
    @http.route('/warehouse_3d/optimize_route/<int:picking_id>', type='json', auth='user', methods=['POST'])
    def optimize_picking_route(self, picking_id, route_type='optimal', **kwargs):
        """
        Trigger route optimization for a picking order
        
        Args:
            picking_id: stock.picking ID
            route_type: 'fifo', 'lifo', 'optimal', 'zone'
        
        Returns:
            dict: Optimized route data
        """
        Picking = request.env['stock.picking'].sudo()
        
        picking = Picking.browse(picking_id)
        if not picking.exists():
            return {'error': 'Picking not found', 'code': 404}
        
        # Set optimization type
        picking.route_optimization_type = route_type
        picking.optimize_picking_route()
        
        if picking.route_id:
            return self.get_picking_route(picking_id)
        else:
            return {'error': 'Route optimization failed', 'code': 500}
    
    @http.route('/warehouse_3d/bin/<int:bin_id>/stock', type='json', auth='user')
    def get_bin_stock_info(self, bin_id, **kwargs):
        """
        Get detailed stock information for a bin
        
        Returns:
            dict: Bin stock details with products, lots, quantities
        """
        Bin = request.env['warehouse.bin'].sudo()
        
        bin_rec = Bin.browse(bin_id)
        if not bin_rec.exists():
            return {'error': 'Bin not found', 'code': 404}
        
        return bin_rec.get_stock_info()
    
    @http.route('/warehouse_3d/warehouse/<int:warehouse_id>/create_layout', type='json', auth='user', methods=['POST'])
    def create_default_layout(self, warehouse_id, **kwargs):
        """
        Create default layout for a warehouse
        
        Returns:
            dict: Created layout info
        """
        Warehouse = request.env['stock.warehouse'].sudo()
        
        warehouse = Warehouse.browse(warehouse_id)
        if not warehouse.exists():
            return {'error': 'Warehouse not found', 'code': 404}
        
        layout = warehouse.create_default_layout()
        return layout.get_layout_info()
