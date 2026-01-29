# -*- coding: utf-8 -*-
"""
Utility functions for warehouse 3D module
Performance helpers, caching, and common operations
"""
from functools import wraps
from odoo import fields
import logging

_logger = logging.getLogger(__name__)


def cached_property(ttl=300):
    """
    Cache computed property for TTL seconds
    Use for expensive computations that don't change often
    
    Args:
        ttl: Time to live in seconds (default 5 minutes)
    
    Usage:
        @cached_property(ttl=600)
        def expensive_computation(self):
            return heavy_calculation()
    """
    def decorator(func):
        cache_attr = f'_cache_{func.__name__}'
        cache_time_attr = f'_cache_time_{func.__name__}'
        
        @wraps(func)
        def wrapper(self):
            import time
            current_time = time.time()
            
            # Check if cache exists and is valid
            if hasattr(self, cache_attr) and hasattr(self, cache_time_attr):
                cache_time = getattr(self, cache_time_attr)
                if current_time - cache_time < ttl:
                    return getattr(self, cache_attr)
            
            # Compute and cache
            result = func(self)
            setattr(self, cache_attr, result)
            setattr(self, cache_time_attr, current_time)
            return result
        
        return wrapper
    return decorator


class WarehousePerformanceHelper:
    """Helper class for performance optimization"""
    
    @staticmethod
    def batch_compute_bin_status(bins):
        """
        Batch compute bin status for multiple bins
        More efficient than computing one by one
        
        Args:
            bins: recordset of warehouse.bin
        
        Returns:
            dict: {bin_id: status}
        """
        if not bins:
            return {}
        
        # Get all quants in one query
        location_ids = bins.mapped('location_id').ids
        quants = bins.env['stock.quant'].search([
            ('location_id', 'in', location_ids)
        ])
        
        # Group quants by location
        quants_by_location = {}
        for quant in quants:
            loc_id = quant.location_id.id
            if loc_id not in quants_by_location:
                quants_by_location[loc_id] = []
            quants_by_location[loc_id].append(quant)
        
        # Compute status for each bin
        result = {}
        for bin_rec in bins:
            loc_quants = quants_by_location.get(bin_rec.location_id.id, [])
            
            if not loc_quants:
                result[bin_rec.id] = 'empty'
            else:
                total_weight = sum(
                    q.quantity * (q.product_id.weight or 0)
                    for q in loc_quants
                )
                if total_weight >= bin_rec.max_weight * 0.9:
                    result[bin_rec.id] = 'full'
                else:
                    result[bin_rec.id] = 'partial'
        
        return result
    
    @staticmethod
    def batch_compute_pick_frequency(bins, days=30):
        """
        Batch compute pick frequency for multiple bins
        
        Args:
            bins: recordset of warehouse.bin
            days: number of days to look back
        
        Returns:
            dict: {bin_id: pick_count}
        """
        from datetime import datetime, timedelta
        
        if not bins:
            return {}
        
        cutoff_date = datetime.now() - timedelta(days=days)
        location_ids = bins.mapped('location_id').ids
        
        # Use SQL for better performance
        bins.env.cr.execute("""
            SELECT location_dest_id, COUNT(*) as pick_count
            FROM stock_move
            WHERE location_dest_id IN %s
            AND state = 'done'
            AND date_expected >= %s
            GROUP BY location_dest_id
        """, (tuple(location_ids), cutoff_date))
        
        picks_by_location = {row[0]: row[1] for row in bins.env.cr.fetchall()}
        
        result = {}
        for bin_rec in bins:
            result[bin_rec.id] = picks_by_location.get(bin_rec.location_id.id, 0)
        
        return result
    
    @staticmethod
    def optimize_large_layout_query(layout, max_bins=5000):
        """
        Optimize query for large layouts with many bins
        Return only most important bins first
        
        Args:
            layout: warehouse.layout record
            max_bins: maximum bins to return
        
        Returns:
            recordset: warehouse.bin records (limited and ordered)
        """
        Bin = layout.env['warehouse.bin']
        location_ids = layout.zone_ids.location_ids.ids
        
        if not location_ids:
            return Bin.browse([])
        
        # Query with limit and order by pick frequency (computed field)
        # For performance, we'll order by last_picked_date instead
        bins = Bin.search(
            [('location_id', 'in', location_ids)],
            order='last_picked_date DESC NULLS LAST',
            limit=max_bins
        )
        
        return bins
    
    @staticmethod
    def get_zone_summary(zone):
        """
        Get summary statistics for a zone
        Uses efficient SQL queries
        
        Args:
            zone: warehouse.zone record
        
        Returns:
            dict: {bin_count, empty_bins, full_bins, total_items, utilization}
        """
        if not zone.location_ids:
            return {
                'bin_count': 0,
                'empty_bins': 0,
                'full_bins': 0,
                'total_items': 0,
                'utilization': 0
            }
        
        location_ids = zone.location_ids.ids
        
        # Count bins
        bin_count = zone.env['warehouse.bin'].search_count([
            ('location_id', 'in', location_ids)
        ])
        
        # Get quant statistics
        zone.env.cr.execute("""
            SELECT 
                COUNT(DISTINCT location_id) as locations_with_stock,
                SUM(quantity) as total_quantity
            FROM stock_quant
            WHERE location_id IN %s
        """, (tuple(location_ids),))
        
        result = zone.env.cr.fetchone()
        locations_with_stock = result[0] or 0
        total_quantity = result[1] or 0
        
        empty_bins = bin_count - locations_with_stock
        
        return {
            'bin_count': bin_count,
            'empty_bins': empty_bins,
            'full_bins': 0,  # Computed separately if needed
            'partial_bins': locations_with_stock,
            'total_items': total_quantity,
            'utilization': (locations_with_stock / bin_count * 100) if bin_count > 0 else 0
        }
