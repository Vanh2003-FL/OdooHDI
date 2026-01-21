# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DeliveryPickWizard(models.TransientModel):
    """Wizard cho luồng xuất kho - hiển thị vị trí pick trên map"""
    _name = 'delivery.pick.wizard'
    _description = 'Delivery Picking Wizard'
    
    picking_id = fields.Many2one('stock.picking', string='Delivery Order', required=True,
                                 domain="[('picking_type_code', '=', 'outgoing')]")
    warehouse_map_id = fields.Many2one('warehouse.map', string='Warehouse Map')
    
    pick_line_ids = fields.One2many(
        'delivery.pick.line',
        'wizard_id',
        string='Pick Lines'
    )
    
    picking_strategy = fields.Selection([
        ('fifo', 'FIFO - First In First Out'),
        ('lifo', 'LIFO - Last In First Out'),
        ('fefo', 'FEFO - First Expired First Out'),
        ('nearest', 'Nearest Location'),
    ], string='Picking Strategy', default='fifo')
    
    show_on_map = fields.Boolean(string='Show Locations on Map', default=True)
    
    @api.onchange('picking_id', 'picking_strategy')
    def _onchange_picking_id(self):
        """Generate pick lines from delivery"""
        if self.picking_id:
            # Find warehouse map
            warehouse = self.picking_id.picking_type_id.warehouse_id
            if warehouse:
                self.warehouse_map_id = self.env['warehouse.map'].search([
                    ('warehouse_id', '=', warehouse.id)
                ], limit=1)
            
            lines = []
            
            for move in self.picking_id.move_ids_without_package:
                # Find best source location based on strategy
                source_location, quant = self._find_best_source_location(
                    move.product_id, 
                    move.product_uom_qty,
                    move.location_id
                )
                
                lines.append((0, 0, {
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'quantity_needed': move.product_uom_qty,
                    'suggested_location_id': source_location.id if source_location else False,
                    'source_location_id': source_location.id if source_location else move.location_id.id,
                    'lot_id': quant.lot_id.id if quant and quant.lot_id else False,
                    'available_qty': quant.quantity if quant else 0,
                }))
            
            self.pick_line_ids = lines
    
    def _find_best_source_location(self, product, quantity, parent_location):
        """Find best source location based on strategy"""
        # Search for quants
        domain = [
            ('product_id', '=', product.id),
            ('location_id', 'child_of', parent_location.id),
            ('quantity', '>', 0),
            ('reserved_quantity', '<', fields.Float('quantity')),
        ]
        
        order = 'in_date asc'  # Default FIFO
        
        if self.picking_strategy == 'lifo':
            order = 'in_date desc'
        elif self.picking_strategy == 'fefo':
            # Order by lot expiration date
            order = 'lot_id.expiration_date asc'
        elif self.picking_strategy == 'nearest':
            # Order by location priority and map distance
            order = 'location_id.location_priority asc, location_id.coordinate_x asc'
        
        quant = self.env['stock.quant'].search(domain, order=order, limit=1)
        
        if quant:
            return quant.location_id, quant
        
        return False, False
    
    def action_apply_picking_locations(self):
        """Apply source locations to delivery"""
        self.ensure_one()
        
        for line in self.pick_line_ids:
            if line.source_location_id:
                # Update move source location
                line.move_id.write({
                    'location_id': line.source_location_id.id
                })
                
                # Update or create move lines with specific lot
                if line.move_id.move_line_ids:
                    line.move_id.move_line_ids.write({
                        'location_id': line.source_location_id.id,
                        'lot_id': line.lot_id.id if line.lot_id else False,
                    })
                else:
                    # Create move line
                    self.env['stock.move.line'].create({
                        'move_id': line.move_id.id,
                        'product_id': line.product_id.id,
                        'location_id': line.source_location_id.id,
                        'location_dest_id': line.move_id.location_dest_id.id,
                        'lot_id': line.lot_id.id if line.lot_id else False,
                        'quantity': min(line.quantity_needed, line.available_qty),
                        'product_uom_id': line.product_id.uom_id.id,
                        'picking_id': self.picking_id.id,
                    })
        
        # Mark as picking ready in WMS
        self.picking_id.write({'wms_state': 'picking_ready'})
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_show_on_map(self):
        """Show pick locations on warehouse map"""
        self.ensure_one()
        
        if not self.warehouse_map_id:
            raise UserError(_('No warehouse map found!'))
        
        # Collect all source locations
        location_ids = self.pick_line_ids.mapped('source_location_id').ids
        
        return {
            'type': 'ir.actions.client',
            'tag': 'warehouse_map_view',
            'name': f'Pick Locations - {self.picking_id.name}',
            'context': {
                'active_id': self.warehouse_map_id.id,
                'highlight_location_ids': location_ids,
                'picking_id': self.picking_id.id,
                'mode': 'picking',
            }
        }


class DeliveryPickLine(models.TransientModel):
    """Pick line for delivery"""
    _name = 'delivery.pick.line'
    _description = 'Delivery Pick Line'
    
    wizard_id = fields.Many2one('delivery.pick.wizard', required=True, ondelete='cascade')
    move_id = fields.Many2one('stock.move', string='Move', required=True)
    
    product_id = fields.Many2one('product.product', string='Product')
    quantity_needed = fields.Float(string='Qty Needed')
    available_qty = fields.Float(string='Available Qty')
    
    suggested_location_id = fields.Many2one('stock.location', string='Suggested Location')
    source_location_id = fields.Many2one('stock.location', string='Pick From', required=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial')
    
    # Map info
    map_x = fields.Integer(related='source_location_id.coordinate_x', string='Map X')
    map_y = fields.Integer(related='source_location_id.coordinate_y', string='Map Y')
    map_z = fields.Integer(related='source_location_id.coordinate_z', string='Map Z')
    
    location_priority = fields.Integer(related='source_location_id.location_priority', string='Priority')
    days_in_stock = fields.Integer(compute='_compute_days_in_stock', string='Days in Stock')
    
    # Vendor info from track_vendor_by_lot
    vendor_name = fields.Char(related='lot_id.partner_id.name', string='Vendor', readonly=True)
    
    # Display
    location_display = fields.Char(compute='_compute_location_display')
    
    @api.depends('lot_id', 'lot_id.create_date')
    def _compute_days_in_stock(self):
        """Calculate days in stock"""
        from datetime import datetime
        today = datetime.now()
        
        for line in self:
            if line.lot_id and line.lot_id.create_date:
                delta = today - line.lot_id.create_date
                line.days_in_stock = delta.days
            else:
                line.days_in_stock = 0
    
    @api.depends('source_location_id', 'map_x', 'map_y', 'lot_id', 'vendor_name')
    def _compute_location_display(self):
        """Generate display text"""
        for line in self:
            if line.source_location_id:
                display = line.source_location_id.complete_name
                if line.map_x or line.map_y:
                    display += f" [{line.map_x},{line.map_y}]"
                if line.lot_id:
                    display += f" (Lot: {line.lot_id.name})"
                if line.vendor_name:
                    display += f" [Vendor: {line.vendor_name}]"
                line.location_display = display
            else:
                line.location_display = ''
