# -*- coding: utf-8 -*-

from odoo import models, _
import math


class Warehouse3DService(models.AbstractModel):
    _name = 'warehouse.3d.service'
    _description = 'Service Tính Toán 3D Kho'

    def calculate_distance_3d(self, location1, location2):
        """
        Tính khoảng cách 3D Euclid giữa 2 vị trí
        distance = sqrt((x2-x1)² + (y2-y1)² + (z2-z1)²)
        """
        x1 = location1.coordinate_x or 0
        y1 = location1.coordinate_y or 0
        z1 = location1.coordinate_z or 0
        
        x2 = location2.coordinate_x or 0
        y2 = location2.coordinate_y or 0
        z2 = location2.coordinate_z or 0
        
        distance = math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
        return round(distance, 2)

    def calculate_manhattan_distance(self, location1, location2):
        """
        Tính khoảng cách Manhattan (thực tế di chuyển trong kho)
        distance = |x2-x1| + |y2-y1| + |z2-z1|
        """
        x1 = location1.coordinate_x or 0
        y1 = location1.coordinate_y or 0
        z1 = location1.coordinate_z or 0
        
        x2 = location2.coordinate_x or 0
        y2 = location2.coordinate_y or 0
        z2 = location2.coordinate_z or 0
        
        distance = abs(x2-x1) + abs(y2-y1) + abs(z2-z1)
        return distance

    def find_closest_available_location(self, product, quantity, from_location=None, warehouse_layout_id=None):
        """
        Tìm vị trí khả dụng gần nhất để đặt hàng
        """
        Location = self.env['stock.location']
        
        # Lấy danh sách vị trí để đặt hàng
        domain = [('is_putable', '=', True), ('usage', '=', 'internal')]
        
        if warehouse_layout_id:
            domain.append(('warehouse_layout_id', '=', warehouse_layout_id))
        
        locations = Location.search(domain)
        
        if not locations:
            return None
        
        # Lọc vị trí có dung lượng đủ
        available_locations = []
        for loc in locations:
            if loc.get_available_capacity_for_product(product, quantity):
                available_locations.append(loc)
        
        if not available_locations:
            return None
        
        # Sắp xếp theo khoảng cách từ vị trí hiện tại
        if from_location:
            available_locations.sort(
                key=lambda loc: self.calculate_manhattan_distance(from_location, loc)
            )
        
        return available_locations[0]

    def get_locations_by_accessibility(self, warehouse_layout_id, limit=None):
        """
        Lấy danh sách vị trí sắp xếp theo điểm tiếp cận (cao nhất trước)
        """
        locations = self.env['stock.location'].search([
            ('warehouse_layout_id', '=', warehouse_layout_id),
            ('is_putable', '=', True),
            ('usage', '=', 'internal'),
        ], order='accessibility_score desc')
        
        if limit:
            locations = locations[:limit]
        
        return locations

    def calculate_route_distance(self, locations):
        """
        Tính tổng khoảng cách cho một tuyến đường (danh sách vị trí theo thứ tự)
        """
        if len(locations) < 2:
            return 0
        
        total_distance = 0
        for i in range(len(locations) - 1):
            total_distance += self.calculate_manhattan_distance(locations[i], locations[i+1])
        
        return total_distance

    def optimize_picking_route_simple(self, picking_lines):
        """
        Tối ưu hóa đơn giản: Sắp xếp vị trí theo Z (từ cao xuống thấp) rồi theo Y
        Phù hợp với picking theo hàng ngang (S-curve)
        """
        # Group by Z level
        by_z = {}
        for line in picking_lines:
            z = line.location_id.coordinate_z or 0
            if z not in by_z:
                by_z[z] = []
            by_z[z].append(line)
        
        # Sort Z levels descending
        sorted_z = sorted(by_z.keys(), reverse=True)
        
        # Sort each level by Y coordinate
        optimized = []
        for z in sorted_z:
            level_items = sorted(by_z[z], key=lambda l: l.location_id.coordinate_y or 0)
            optimized.extend(level_items)
        
        return optimized

    def get_heatmap_data(self, warehouse_layout_id):
        """
        Tạo dữ liệu heatmap dung lượng cho hiển thị
        Returns: list[{location_id, x, y, z, capacity_percentage, color}]
        """
        locations = self.env['stock.location'].search([
            ('warehouse_layout_id', '=', warehouse_layout_id),
            ('usage', '=', 'internal'),
        ])
        
        heatmap_data = []
        for loc in locations:
            # Tính màu dựa trên capacity (green → yellow → red)
            capacity = loc.capacity_percentage or 0
            if capacity < 50:
                color = '#4CAF50'  # Green
            elif capacity < 80:
                color = '#FFC107'  # Yellow
            else:
                color = '#F44336'  # Red
            
            heatmap_data.append({
                'location_id': loc.id,
                'location_name': loc.complete_name,
                'x': loc.coordinate_x or 0,
                'y': loc.coordinate_y or 0,
                'z': loc.coordinate_z or 0,
                'capacity_percentage': capacity,
                'color': color,
                'available_volume': loc.available_volume or 0,
            })
        
        return heatmap_data
