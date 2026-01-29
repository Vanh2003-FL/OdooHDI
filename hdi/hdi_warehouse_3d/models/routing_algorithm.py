# -*- coding: utf-8 -*-
"""
Picking Route Optimization Algorithm
Implements multiple routing strategies: FIFO, LIFO, Zone-based, and Optimal (TSP)
"""
from datetime import datetime, timedelta
import math


class PickingRouteOptimizer:
    """Optimize picking routes for warehouse efficiency"""
    
    def calculate_optimal_route(self, bins, layout, route_type):
        """
        Main method to calculate optimal route
        
        Args:
            bins: list of warehouse.bin records to pick
            layout: warehouse.layout record
            route_type: str - 'fifo', 'lifo', 'optimal', 'zone'
        
        Returns:
            list of warehouse.bin records in optimal order
        """
        if not bins:
            return []
        
        if route_type == 'fifo':
            return self._fifo_route(bins)
        elif route_type == 'lifo':
            return self._lifo_route(bins)
        elif route_type == 'zone':
            return self._zone_based_route(bins, layout)
        else:  # optimal or default
            return self._optimal_distance_route(bins)
    
    def _fifo_route(self, bins):
        """First-In-First-Out: pick oldest stock first"""
        return sorted(bins, key=lambda b: b.last_picked_date or datetime.min)
    
    def _lifo_route(self, bins):
        """Last-In-First-Out: pick newest stock first"""
        return sorted(bins, key=lambda b: b.last_picked_date or datetime.min, reverse=True)
    
    def _zone_based_route(self, bins, layout):
        """Zone-based routing: optimize within zones, then by zone sequence"""
        if not layout:
            return bins
        
        zones = layout.zone_ids
        zone_bins = {zone.id: [] for zone in zones}
        unzoned_bins = []
        
        # Group bins by zone
        for bin_rec in bins:
            zone_found = False
            for zone in zones:
                if bin_rec.location_id in zone.location_ids:
                    zone_bins[zone.id].append(bin_rec)
                    zone_found = True
                    break
            if not zone_found:
                unzoned_bins.append(bin_rec)
        
        # Optimize each zone, then concat in sequence order
        result = []
        for zone in zones:
            if zone_bins[zone.id]:
                zone_optimized = self._nearest_neighbor(
                    zone_bins[zone.id],
                    (zone.pos_x, zone.pos_y, zone.pos_z)
                )
                result.extend(zone_optimized)
        
        result.extend(unzoned_bins)
        return result
    
    def _optimal_distance_route(self, bins):
        """Optimal distance routing using nearest neighbor TSP heuristic"""
        if not bins:
            return []
        
        # Start from first bin
        start_pos = (bins[0].pos_x, bins[0].pos_y, bins[0].pos_z or 0)
        return self._nearest_neighbor(bins, start_pos)
    
    def _nearest_neighbor(self, bins, start_pos):
        """
        Nearest Neighbor algorithm for TSP (greedy approximation)
        
        Args:
            bins: list of warehouse.bin records
            start_pos: tuple (x, y, z) starting position
        
        Returns:
            list of bins in order of nearest neighbor traversal
        """
        if not bins:
            return []
        
        if len(bins) == 1:
            return bins
        
        unvisited = list(bins)
        visited = []
        current_pos = start_pos
        
        while unvisited:
            # Find nearest bin
            nearest_bin = None
            nearest_distance = float('inf')
            
            for bin_rec in unvisited:
                bin_pos = (bin_rec.pos_x, bin_rec.pos_y, bin_rec.pos_z or 0)
                distance = self._distance(current_pos, bin_pos)
                
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_bin = bin_rec
            
            if nearest_bin:
                visited.append(nearest_bin)
                unvisited.remove(nearest_bin)
                current_pos = (nearest_bin.pos_x, nearest_bin.pos_y, nearest_bin.pos_z or 0)
        
        return visited
    
    @staticmethod
    def _distance(pos1, pos2):
        """Calculate Euclidean distance between two 3D positions"""
        x1, y1, z1 = pos1
        x2, y2, z2 = pos2
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)
    
    def optimize_with_lot_tracking(self, bins, lots_data):
        """
        Advanced optimization considering lot/expiry dates
        Prioritize picking by lot expiry (FEFO: First-Expired-First-Out)
        
        Args:
            bins: list of warehouse.bin records
            lots_data: dict of {lot_id: expiry_date}
        
        Returns:
            list of bins sorted by lot expiry then distance
        """
        if not bins or not lots_data:
            return self._optimal_distance_route(bins)
        
        # Sort by expiry date, then by distance
        def sort_key(bin_rec):
            # Get earliest expiry for any lot in this bin
            earliest_expiry = None
            for quant in bin_rec.quant_ids:
                if quant.lot_id and quant.lot_id.id in lots_data:
                    expiry = lots_data[quant.lot_id.id]
                    if not earliest_expiry or expiry < earliest_expiry:
                        earliest_expiry = expiry
            
            # Return tuple: (has_expiry, expiry_date, distance_from_start)
            if earliest_expiry:
                dist = self._distance((0, 0, 0), (bin_rec.pos_x, bin_rec.pos_y, bin_rec.pos_z or 0))
                return (0, earliest_expiry, dist)  # 0 sorts before 1
            else:
                dist = self._distance((0, 0, 0), (bin_rec.pos_x, bin_rec.pos_y, bin_rec.pos_z or 0))
                return (1, datetime.max, dist)  # No expiry = lower priority
        
        return sorted(bins, key=sort_key)
