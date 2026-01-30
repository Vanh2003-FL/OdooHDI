# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class StockMove(models.Model):
    _inherit = 'stock.move'
    
    # Bin information
    source_bin_id = fields.Many2one('warehouse.bin', string='Source Bin', 
                                     compute='_compute_bin_ids', store=True, index=True)
    dest_bin_id = fields.Many2one('warehouse.bin', string='Destination Bin', 
                                   compute='_compute_bin_ids', store=True, index=True)
    
    # FR-8, FR-10: Suggested/Selected bins
    suggested_bin_id = fields.Many2one('warehouse.bin', string='Suggested Bin',
                                        help='Hệ thống đề xuất Bin dựa trên putaway strategy')
    selected_bin_id = fields.Many2one('warehouse.bin', string='Selected Bin',
                                       help='Bin được chọn bởi người dùng hoặc hệ thống')
    
    @api.depends('location_id', 'location_id.bin_id', 'location_dest_id', 'location_dest_id.bin_id')
    def _compute_bin_ids(self):
        for move in self:
            move.source_bin_id = move.location_id.bin_id if move.location_id else False
            move.dest_bin_id = move.location_dest_id.bin_id if move.location_dest_id else False
    
    # FR-6: Không cho phép phát sinh stock move vi phạm ràng buộc Bin
    @api.constrains('product_id', 'location_dest_id', 'lot_ids')
    def _check_bin_constraints(self):
        """Validate bin constraints before move"""
        for move in self:
            dest_bin = move.location_dest_id.bin_id
            if not dest_bin:
                continue
            
            # FR-16: Check if bin is blocked
            if dest_bin.is_blocked:
                raise ValidationError(_(
                    'Cannot move to blocked bin %s!\n'
                    'Reason: %s'
                ) % (dest_bin.complete_name, dest_bin.block_reason or 'N/A'))
            
            # FR-4: Check SKU constraint (only if bin already has different product)
            if dest_bin.current_product_id and dest_bin.current_product_id != move.product_id:
                raise ValidationError(_(
                    'Bin %s already contains a different product (%s)!\n'
                    'Cannot add %s to this bin.'
                ) % (dest_bin.complete_name, 
                     dest_bin.current_product_id.display_name,
                     move.product_id.display_name))
            
            # FR-5: Check lot constraint if enforced
            if dest_bin.enforce_single_lot and dest_bin.current_lot_id:
                move_lots = move.lot_ids
                if move_lots and dest_bin.current_lot_id not in move_lots:
                    raise ValidationError(_(
                        'Bin %s is configured for single lot only!\n'
                        'Current lot: %s\n'
                        'Cannot add different lot to this bin.'
                    ) % (dest_bin.complete_name, dest_bin.current_lot_id.name))
    
    def _action_done(self, cancel_backorder=False):
        """Override to create bin history after move is done"""
        result = super()._action_done(cancel_backorder=cancel_backorder)
        
        # Create bin history records
        for move in self:
            if move.source_bin_id:
                self.env['bin.history'].create({
                    'bin_id': move.source_bin_id.id,
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'lot_id': move.lot_ids[0].id if move.lot_ids else False,
                    'quantity': move.product_uom_qty,
                    'uom_id': move.product_uom.id,
                    'operation_type': 'out',
                    'reference': move.reference or move.picking_id.name,
                })
            
            if move.dest_bin_id:
                self.env['bin.history'].create({
                    'bin_id': move.dest_bin_id.id,
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'lot_id': move.lot_ids[0].id if move.lot_ids else False,
                    'quantity': move.product_uom_qty,
                    'uom_id': move.product_uom.id,
                    'operation_type': 'in',
                    'reference': move.reference or move.picking_id.name,
                })
        
        return result
    
    # FR-7: Suggest putaway bin based on product and category
    def _get_suggested_putaway_bin(self):
        """Get suggested bin for putaway based on product, category, and zone"""
        self.ensure_one()
        
        Bin = self.env['warehouse.bin']
        product = self.product_id
        category = product.categ_id
        warehouse = self.warehouse_id
        
        if not warehouse:
            return False
        
        # Find suitable bins
        domain = [
            ('warehouse_id', '=', warehouse.id),
            ('is_blocked', '=', False),
            ('state', 'in', ['empty', 'available']),
        ]
        
        # Filter by allowed categories in zone
        zones = self.env['warehouse.zone'].search([
            ('warehouse_id', '=', warehouse.id),
            '|',
            ('allowed_category_ids', '=', False),
            ('allowed_category_ids', 'in', category.ids),
        ])
        
        if zones:
            domain.append(('zone_id', 'in', zones.ids))
        
        bins = Bin.search(domain)
        
        if not bins:
            return False
        
        # Priority 1: Empty bin in same zone as existing product stock
        existing_quants = self.env['stock.quant'].search([
            ('product_id', '=', product.id),
            ('location_id.bin_id', '!=', False),
            ('quantity', '>', 0),
        ], limit=1)
        
        if existing_quants and existing_quants.location_id.bin_id:
            same_zone_bins = bins.filtered(
                lambda b: b.zone_id == existing_quants.location_id.bin_id.zone_id and b.state == 'empty'
            )
            if same_zone_bins:
                return same_zone_bins[0]
        
        # Priority 2: Bin with same product but not full
        same_product_bins = bins.filtered(
            lambda b: b.current_product_id == product and b.state == 'available'
        )
        if same_product_bins:
            return same_product_bins[0]
        
        # Priority 3: Any empty bin
        empty_bins = bins.filtered(lambda b: b.state == 'empty')
        if empty_bins:
            return empty_bins[0]
        
        # Priority 4: Any available bin
        return bins[0] if bins else False
