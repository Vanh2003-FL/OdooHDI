# -*- coding: utf-8 -*-
from odoo import models, fields, api
import json


class StockPickingRoute(models.Model):
    """Optimized picking route for a picking order"""
    _name = 'stock.picking.route'
    _description = 'Picking Route Optimization'
    
    # Add SQL constraints and indices
    _sql_constraints = [
        ('unique_picking', 'UNIQUE(picking_id)', 'Each picking can only have one route!')
    ]

    picking_id = fields.Many2one(
        'stock.picking',
        string='Đơn lấy hàng',
        required=True,
        ondelete='cascade',
        unique=True
    )
    
    route_type = fields.Selection(
        [('fifo', 'FIFO - Vào trước ra trước'),
         ('lifo', 'LIFO - Vào sau ra trước'),
         ('optimal', 'Tối ưu khoảng cách'),
         ('zone', 'Theo khu vực')],
        string='Loại lộ trình',
        default='optimal'
    )
    
    # Optimized sequence of bins to pick
    optimized_sequence = fields.Json(
        string='Thứ tự ngăn kho tối ưu',
        help='Danh sách ID ngăn kho theo thứ tự lấy hàng tối ưu'
    )
    
    route_distance = fields.Float(
        string='Quãng đường lộ trình (mét)',
        compute='_compute_route_distance',
        store=False
    )
    
    estimated_time = fields.Float(
        string='Thời gian ước tính (phút)',
        compute='_compute_estimated_time',
        store=False
    )
    
    bin_count = fields.Integer(
        string='Số ngăn kho',
        compute='_compute_bin_count',
        store=False
    )
    
    @api.depends('optimized_sequence')
    def _compute_bin_count(self):
        """Count number of bins in route"""
        for route in self:
            route.bin_count = len(route.optimized_sequence) if route.optimized_sequence else 0
    
    @api.depends('optimized_sequence')
    def _compute_route_distance(self):
        """Calculate total route distance"""
        for route in self:
            if not route.optimized_sequence:
                route.route_distance = 0
                continue
            
            total_distance = 0
            bin_ids = route.optimized_sequence
            
            if len(bin_ids) > 1:
                bins = self.env['warehouse.bin'].browse(bin_ids)
                positions = [(b.pos_x, b.pos_y) for b in bins]
                
                # Calculate Euclidean distance between consecutive bins
                for i in range(len(positions) - 1):
                    x1, y1 = positions[i]
                    x2, y2 = positions[i + 1]
                    distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                    total_distance += distance
            
            route.route_distance = total_distance
    
    @api.depends('route_distance', 'bin_count')
    def _compute_estimated_time(self):
        """Estimate picking time (distance + picking time)"""
        for route in self:
            # Assume: 1.5 m/s walking speed + 30 seconds per bin picking
            walking_time = (route.route_distance / 1.5) / 60  # Convert to minutes
            picking_time = route.bin_count * 0.5  # 30 seconds per bin
            route.estimated_time = walking_time + picking_time
    
    def get_route_display(self):
        """Return formatted route info for UI"""
        if not self.optimized_sequence:
            return []
        
        bins = self.env['warehouse.bin'].browse(self.optimized_sequence)
        return [
            {
                'sequence': i + 1,
                'bin_id': bin.id,
                'bin_name': bin.name,
                'location': f"{bin.location_id.name}" if bin.location_id else 'N/A',
                'quantity': sum(q.quantity for q in bin.quant_ids),
                'position': [bin.pos_x, bin.pos_y, 0]
            }
            for i, bin in enumerate(bins)
        ]


class StockPickingExtended(models.Model):
    """Extend stock.picking with route optimization"""
    _inherit = 'stock.picking'

    route_id = fields.Many2one(
        'stock.picking.route',
        string='Lộ trình tối ưu',
        ondelete='cascade',
        readonly=True
    )
    
    route_sequence = fields.Json(
        string='Thứ tự lộ trình',
        readonly=True,
        help='Thứ tự ngăn kho được cache để hiển thị'
    )
    
    use_optimized_route = fields.Boolean(
        string='Sử dụng lộ trình tối ưu',
        default=True
    )
    
    route_optimization_type = fields.Selection(
        [('fifo', 'FIFO - Vào trước ra trước'),
         ('lifo', 'LIFO - Vào sau ra trước'),
         ('optimal', 'Tối ưu khoảng cách'),
         ('zone', 'Theo khu vực')],
        string='Loại tối ưu hóa',
        default='optimal'
    )
    
    def optimize_picking_route(self):
        """Calculate and store optimized picking route"""
        for picking in self:
            if not picking.use_optimized_route:
                continue
            
            # Get bins to pick
            bins = picking._get_bins_to_pick()
            if not bins:
                continue
            
            # Import routing algorithm
            from .routing_algorithm import PickingRouteOptimizer
            
            # Get warehouse layout
            layout = picking.warehouse_id.layout_id
            
            # Optimize route
            optimizer = PickingRouteOptimizer()
            optimized_bins = optimizer.calculate_optimal_route(
                bins,
                layout,
                picking.route_optimization_type
            )
            
            # Create or update route
            if picking.route_id:
                picking.route_id.write({
                    'optimized_sequence': [b.id for b in optimized_bins],
                    'route_type': picking.route_optimization_type
                })
            else:
                route = self.env['stock.picking.route'].create({
                    'picking_id': picking.id,
                    'optimized_sequence': [b.id for b in optimized_bins],
                    'route_type': picking.route_optimization_type
                })
                picking.route_id = route
            
            # Update cached sequence
            picking.route_sequence = [b.id for b in optimized_bins]
    
    def _get_bins_to_pick(self):
        """Extract all warehouse.bins from move_lines"""
        bins = self.env['warehouse.bin']
        
        for move in self.move_ids:
            if move.location_dest_id:
                # Find bin for destination location
                bin_rec = self.env['warehouse.bin'].search(
                    [('location_id', '=', move.location_dest_id.id)],
                    limit=1
                )
                if bin_rec:
                    bins |= bin_rec
        
        return bins
    
    def action_open_route_viewer(self):
        """Open route visualization in web client"""
        self.optimize_picking_route()
        
        if not self.route_id:
            return {'type': 'ir.actions.client', 'tag': 'do_action'}
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking.route',
            'res_id': self.route_id.id,
            'view_mode': 'form',
            'target': 'current'
        }
    
    def _create_bin_movements(self):
        """Create bin movement records when picking is done"""
        self.ensure_one()
        
        if not self.picking_type_code in ['outgoing', 'internal']:
            return
        
        BinMovement = self.env['warehouse.bin.movement']
        
        for move_line in self.move_line_ids:
            # Determine source and destination bins
            source_bin = False
            dest_bin = False
            
            # Try to find bins from locations
            if move_line.location_id:
                source_bin = self.env['warehouse.bin'].search([
                    ('location_id', '=', move_line.location_id.id)
                ], limit=1)
            
            if move_line.location_dest_id:
                dest_bin = self.env['warehouse.bin'].search([
                    ('location_id', '=', move_line.location_dest_id.id)
                ], limit=1)
            
            # Determine movement type
            if self.picking_type_code == 'outgoing':
                movement_type = 'pick'
            elif self.picking_type_code == 'incoming':
                movement_type = 'putaway'
            else:
                movement_type = 'transfer'
            
            # Create movement record if we have at least destination
            if dest_bin:
                BinMovement.create({
                    'product_id': move_line.product_id.id,
                    'quantity': move_line.quantity,
                    'source_bin_id': source_bin.id if source_bin else False,
                    'dest_bin_id': dest_bin.id,
                    'movement_type': movement_type,
                    'picking_id': self.id,
                    'move_line_id': move_line.id,
                })
        
        return True
    
    def button_validate(self):
        """Override to create bin movements on validation"""
        res = super(StockPicking, self).button_validate()
        
        # Create bin movements after successful validation
        for picking in self:
            if picking.state == 'done':
                picking._create_bin_movements()
        
        return res

