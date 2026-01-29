# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta
import json


class WarehouseHeatmap(models.Model):
    """Real-time heatmap showing picking frequency per bin"""
    _name = 'warehouse.heatmap'
    _description = 'Warehouse Pick Heatmap'
    _order = 'date desc'
    
    # Add SQL constraints
    _sql_constraints = [
        ('unique_layout_date', 'UNIQUE(layout_id, date)', 'Only one heatmap per layout per day!')
    ]

    layout_id = fields.Many2one('warehouse.layout', string='Bố trí', required=True, ondelete='cascade')
    date = fields.Date(string='Ngày', required=True, default=fields.Date.today)
    
    # Heatmap data: {bin_id: pick_count}
    heatmap_data = fields.Json(string='Dữ liệu bản đồ nhiệt', default={})
    
    total_picks = fields.Integer(
        string='Tổng số lần lấy hàng',
        compute='_compute_statistics',
        store=False
    )
    
    max_picks = fields.Integer(
        string='Số lần lấy nhiều nhất',
        compute='_compute_statistics',
        store=False
    )
    
    avg_picks = fields.Float(
        string='Trung bình lần lấy mỗi ngăn',
        compute='_compute_statistics',
        store=False
    )
    
    @api.depends('heatmap_data')
    def _compute_statistics(self):
        """Calculate heatmap statistics"""
        for heatmap in self:
            if not heatmap.heatmap_data:
                heatmap.total_picks = 0
                heatmap.max_picks = 0
                heatmap.avg_picks = 0
                continue
            
            picks = list(heatmap.heatmap_data.values())
            heatmap.total_picks = sum(picks)
            heatmap.max_picks = max(picks) if picks else 0
            heatmap.avg_picks = heatmap.total_picks / len(picks) if picks else 0
    
    def generate_heatmap(self, days=30):
        """Generate heatmap data from stock.move for last N days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        heatmap_data = {}
        
        # Get all moves in last N days
        moves = self.env['stock.move'].search([
            ('location_dest_id', 'in', self.layout_id.zone_ids.location_ids.ids),
            ('state', '=', 'done'),
            ('date_expected', '>=', cutoff_date)
        ])
        
        # Count picks per location/bin
        for move in moves:
            bin_rec = self.env['warehouse.bin'].search(
                [('location_id', '=', move.location_dest_id.id)],
                limit=1
            )
            if bin_rec:
                bin_id = str(bin_rec.id)
                heatmap_data[bin_id] = heatmap_data.get(bin_id, 0) + 1
        
        self.heatmap_data = heatmap_data
        return heatmap_data
    
    @api.model
    def _cron_generate_daily_heatmap(self):
        """
        Cron job: Generate heatmap for all active layouts
        Runs daily at midnight
        """
        layouts = self.env['warehouse.layout'].search([])
        today = fields.Date.today()
        
        for layout in layouts:
            # Check if heatmap already exists for today
            existing = self.search([
                ('layout_id', '=', layout.id),
                ('date', '=', today)
            ], limit=1)
            
            if not existing:
                heatmap = self.create({
                    'layout_id': layout.id,
                    'date': today
                })
                heatmap.generate_heatmap(days=30)
        
        return True
    
    @api.model
    def _cron_cleanup_old_data(self, days=90):
        """
        Cron job: Delete heatmap data older than N days
        Runs weekly
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        old_records = self.search([('date', '<', cutoff_date.date())])
        count = len(old_records)
        old_records.unlink()
        return count


class WarehouseMetrics(models.Model):
    """Daily warehouse performance metrics"""
    _name = 'warehouse.metrics'
    _description = 'Warehouse Performance Metrics'
    _order = 'date desc'
    
    # Add SQL constraints
    _sql_constraints = [
        ('unique_layout_date', 'UNIQUE(layout_id, date)', 'Only one metric record per layout per day!')
    ]

    layout_id = fields.Many2one('warehouse.layout', string='Bố trí', required=True, ondelete='cascade')
    date = fields.Date(string='Ngày', required=True, default=fields.Date.today)
    
    # Picking Metrics
    total_picks = fields.Integer(string='Tổng số lần lấy hàng')
    avg_pick_time = fields.Float(string='Thời gian lấy hàng TB (phút)')
    total_distance = fields.Float(string='Tổng quãng đường (m)')
    
    # Inventory Metrics
    empty_bins = fields.Integer(string='Số ngăn trống')
    partial_bins = fields.Integer(string='Số ngăn một phần')
    full_bins = fields.Integer(string='Số ngăn đầy')
    
    bin_utilization_percentage = fields.Float(string='Tỷ lệ sử dụng ngăn %')
    
    # Efficiency
    efficiency_score = fields.Float(
        string='Điểm hiệu suất (0-100)',
        compute='_compute_efficiency_score',
        store=False
    )
    
    bottleneck_zones = fields.Json(
        string='Khu vực tắc nghẽ',
        compute='_find_bottleneck_zones',
        store=False
    )
    
    @api.depends('total_picks', 'avg_pick_time', 'total_distance', 'bin_utilization_percentage')
    def _compute_efficiency_score(self):
        """Calculate efficiency score (0-100)"""
        for metric in self:
            # 40% utilization, 40% distribution, 20% speed
            utilization_score = metric.bin_utilization_percentage / 100 * 40
            
            # Distribution score: favor medium-high utilization
            if 40 <= metric.bin_utilization_percentage <= 80:
                distribution_score = 40
            elif 20 <= metric.bin_utilization_percentage < 40:
                distribution_score = 30
            elif 80 < metric.bin_utilization_percentage <= 95:
                distribution_score = 30
            else:
                distribution_score = 10
            
            # Speed score: based on avg pick time
            if metric.avg_pick_time <= 2:
                speed_score = 20
            elif metric.avg_pick_time <= 5:
                speed_score = 15
            else:
                speed_score = 5
            
            metric.efficiency_score = utilization_score + distribution_score + speed_score
    
    @api.depends('layout_id')
    def _find_bottleneck_zones(self):
        """Identify zones with high picking load"""
        for metric in self:
            zones = metric.layout_id.zone_ids
            bottlenecks = []
            
            for zone in zones:
                # Count picks in zone
                zone_bins = self.env['warehouse.bin'].search(
                    [('location_id', 'in', zone.location_ids.ids)]
                )
                zone_picks = sum(
                    self.env['stock.move'].search_count([
                        ('location_dest_id', 'in', zone.location_ids.ids),
                        ('state', '=', 'done'),
                        ('date_expected', '>=', metric.date),
                        ('date_expected', '<', metric.date + timedelta(days=1))
                    ]) for _ in zone_bins
                )
                
                if zone_picks > metric.total_picks * 0.3:  # >30% of picks
                    bottlenecks.append({
                        'zone_id': zone.id,
                        'zone_name': zone.name,
                        'pick_percentage': (zone_picks / metric.total_picks * 100) if metric.total_picks else 0
                    })
            
            metric.bottleneck_zones = bottlenecks
    
    def generate_metrics(self, date=None):
        """Generate metrics snapshot for given date"""
        if not date:
            date = fields.Date.today()
        
        # Picking metrics
        cutoff_date = datetime.combine(date, datetime.min.time())
        end_date = datetime.combine(date + timedelta(days=1), datetime.min.time())
        
        moves = self.env['stock.move'].search([
            ('location_dest_id', 'in', self.layout_id.zone_ids.location_ids.ids),
            ('state', '=', 'done'),
            ('date_expected', '>=', cutoff_date),
            ('date_expected', '<', end_date)
        ])
        
        self.total_picks = len(moves)
        
        # Inventory metrics
        bins = self.env['warehouse.bin'].search(
            [('location_id', 'in', self.layout_id.zone_ids.location_ids.ids)]
        )
        
        empty = len([b for b in bins if b.bin_status == 'empty'])
        partial = len([b for b in bins if b.bin_status == 'partial'])
        full = len([b for b in bins if b.bin_status == 'full'])
        
        self.empty_bins = empty
        self.partial_bins = partial
        self.full_bins = full
        
        # Utilization
        total_weight = sum(b.total_weight for b in bins)
        max_weight = sum(b.max_weight for b in bins)
        self.bin_utilization_percentage = (total_weight / max_weight * 100) if max_weight > 0 else 0
        
        # Time metrics (estimate from routes if available)
        routes = self.env['stock.picking.route'].search(
            [('picking_id.date_priority', '>=', cutoff_date),
             ('picking_id.date_priority', '<', end_date)]
        )
        
        if routes:
            avg_time = sum(r.estimated_time for r in routes) / len(routes)
            total_dist = sum(r.route_distance for r in routes)
        else:
            avg_time = 0
            total_dist = 0
        
        self.avg_pick_time = avg_time
        self.total_distance = total_dist
        
        return self
    
    @api.model
    def _cron_generate_daily_metrics(self):
        """
        Cron job: Generate metrics for all active layouts
        Runs daily at midnight
        """
        layouts = self.env['warehouse.layout'].search([])
        today = fields.Date.today()
        
        for layout in layouts:
            # Check if metrics already exist for today
            existing = self.search([
                ('layout_id', '=', layout.id),
                ('date', '=', today)
            ], limit=1)
            
            if not existing:
                metrics = self.create({
                    'layout_id': layout.id,
                    'date': today
                })
                metrics.generate_metrics(date=today)
        
        return True
    
    @api.model
    def _cron_cleanup_old_data(self, days=90):
        """
        Cron job: Delete metrics data older than N days
        Runs weekly
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        old_records = self.search([('date', '<', cutoff_date.date())])
        count = len(old_records)
        old_records.unlink()
        return count
