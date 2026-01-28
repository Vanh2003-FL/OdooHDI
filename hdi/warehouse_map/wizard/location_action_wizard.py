# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class LocationActionWizard(models.TransientModel):
    _name = 'location.action.wizard'
    _description = 'Wizard thực hiện action trên vị trí kho'

    location_id = fields.Many2one('stock.location', string='Vị trí nguồn', required=True)
    action_type = fields.Selection([
        ('pick', 'Lấy hàng'),
        ('move', 'Chuyển vị trí'),
        ('transfer', 'Chuyển kho'),
    ], string='Loại thao tác', required=True, default='pick')
    
    quant_ids = fields.Many2many('stock.quant', string='Chọn lot/sản phẩm',
                                  domain="[('location_id', '=', location_id), ('quantity', '>', 0)]")
    
    dest_location_id = fields.Many2one('stock.location', string='Vị trí đích',
                                        domain="[('usage', '=', 'internal')]")
    
    product_id = fields.Many2one('product.product', string='Sản phẩm')
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial')
    quantity = fields.Float(string='Số lượng', default=1.0)
    available_qty = fields.Float(string='Số lượng có sẵn', compute='_compute_available_qty', readonly=True)
    
    picking_type_id = fields.Many2one('stock.picking.type', string='Loại phiếu')
    
    # Barcode scanning
    barcode_lot_input = fields.Char(string='Quét Barcode Lot/Serial')
    product_barcode_input = fields.Char(string='Quét Barcode Sản phẩm')
    serial_barcode_input = fields.Char(string='Quét Serial Number Sản phẩm')
    
    # Serial tracking
    scanned_serial_ids = fields.Many2many('stock.serial.item', string='Serial đã quét')
    available_serial_ids = fields.Many2many('stock.serial.item', 'wizard_available_serial_rel', 
                                            string='Serial có sẵn', compute='_compute_available_serials')
    scanned_serial_count = fields.Integer(string='Số serial đã quét', compute='_compute_scanned_count')
    product_tracking = fields.Selection(related='product_id.tracking', string='Loại tracking')
    
    @api.depends('product_id', 'lot_id', 'location_id')
    def _compute_available_qty(self):
        """Tính số lượng có sẵn tại location"""
        for record in self:
            if record.product_id and record.location_id and record.lot_id:
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', record.product_id.id),
                    ('location_id', '=', record.location_id.id),
                    ('lot_id', '=', record.lot_id.id),
                    ('display_on_map', '=', True),
                ])
                # Tính available = quantity (không trừ reserved_quantity)
                record.available_qty = sum(q.quantity for q in quants)
            else:
                record.available_qty = 0.0
    
    @api.depends('lot_id')
    def _compute_available_serials(self):
        """Lấy danh sách serial có sẵn trong lot"""
        for record in self:
            if record.lot_id:
                serials = self.env['stock.serial.item'].search([
                    ('lot_id', '=', record.lot_id.id),
                    ('is_picked', '=', False),  # Chưa được pick
                ])
                record.available_serial_ids = serials
            else:
                record.available_serial_ids = False
    
    @api.depends('scanned_serial_ids')
    def _compute_scanned_count(self):
        """Đếm số serial đã quét"""
        for record in self:
            record.scanned_serial_count = len(record.scanned_serial_ids)
    
    @api.onchange('barcode_lot_input')
    def _onchange_barcode_lot_input(self):
        """Scan barcode lot để auto-fill thông tin"""
        if self.barcode_lot_input:
            lot = self.env['stock.lot'].search([
                ('barcode', '=', self.barcode_lot_input),
            ], limit=1)
            
            if lot:
                self.lot_id = lot.id
                self.product_id = lot.product_id.id
                # Auto-fill available quantity
                self.quantity = self.available_qty if self.available_qty > 0 else 1.0
                self.barcode_lot_input = ''  # Clear sau khi scan
            else:
                raise UserError(_(f'Không tìm thấy Lot với barcode "{self.barcode_lot_input}"!'))
    
    @api.onchange('product_barcode_input')
    def _onchange_product_barcode_input(self):
        """Scan barcode sản phẩm để xác nhận sản phẩm xuất"""
        if self.product_barcode_input:
            product = self.env['product.product'].search([
                ('barcode', '=', self.product_barcode_input),
            ], limit=1)
            
            if product:
                # Nếu đã có product_id từ context (chọn lot từ sơ đồ)
                if self.product_id:
                    # Kiểm tra barcode có khớp với product đã chọn không
                    if product.id != self.product_id.id:
                        raise UserError(_(
                            f'Barcode không khớp!\n'
                            f'Sản phẩm từ lot: {self.product_id.name}\n'
                            f'Sản phẩm từ barcode: {product.name}\n'
                            f'Vui lòng quét đúng barcode sản phẩm.'
                        ))
                    # Nếu khớp, thông báo thành công
                    self.product_barcode_input = ''
                    # Không cần làm gì thêm, chỉ xác nhận
                else:
                    # Nếu chưa có product (chọn thủ công), set product
                    self.product_id = product.id
                    self.product_barcode_input = ''
            else:
                raise UserError(_(f'Không tìm thấy sản phẩm với barcode "{self.product_barcode_input}"!'))
    
    @api.onchange('serial_barcode_input')
    def _onchange_serial_barcode_input(self):
        """Quét serial number của từng sản phẩm trong lot"""
        if self.serial_barcode_input:
            if not self.lot_id:
                raise UserError(_('Vui lòng chọn lot trước khi quét serial!'))
            
            # Tìm serial trong lot bằng serial_number HOẶC barcode
            serial = self.env['stock.serial.item'].search([
                ('lot_id', '=', self.lot_id.id),
                '|',
                ('serial_number', '=', self.serial_barcode_input),
                ('barcode', '=', self.serial_barcode_input),
            ], limit=1)
            
            if not serial:
                raise UserError(_(
                    f'Serial/Barcode "{self.serial_barcode_input}" không tồn tại trong Lot {self.lot_id.name}!\n'
                    f'Vui lòng kiểm tra lại hoặc quét barcode/QR khác.'
                ))
            
            # Kiểm tra sản phẩm có khớp không
            if serial.product_id != self.product_id:
                raise UserError(_(
                    f'Barcode không khớp với sản phẩm!\n'
                    f'Sản phẩm từ lot: {self.product_id.name}\n'
                    f'Sản phẩm từ barcode: {serial.product_id.name}\n'
                    f'Serial: {serial.serial_number}\n'
                    f'Vui lòng quét đúng barcode sản phẩm đã nhập.'
                ))
            
            # Kiểm tra serial đã được quét chưa
            if serial in self.scanned_serial_ids:
                raise UserError(_(
                    f'Serial "{serial.serial_number}" đã được quét rồi!\n'
                    f'Vui lòng quét serial khác.'
                ))
            
            # Kiểm tra serial đã được pick chưa
            if serial.is_picked:
                raise UserError(_(
                    f'Serial "{serial.serial_number}" đã được xuất kho!\n'
                    f'Không thể xuất lại.'
                ))
            
            # Thêm serial vào danh sách đã quét
            self.scanned_serial_ids = [(4, serial.id)]
            self.serial_barcode_input = ''  # Clear field
            
            # Auto-update quantity
            self.quantity = len(self.scanned_serial_ids)
    
    @api.onchange('location_id', 'action_type')
    def _onchange_location_action(self):
        """Tự động chọn picking type phù hợp"""
        if self.location_id and self.action_type:
            warehouse = self.env['stock.warehouse'].search([
                ('lot_stock_id', 'parent_of', self.location_id.id)
            ], limit=1)
            
            if warehouse:
                if self.action_type == 'pick':
                    self.picking_type_id = warehouse.out_type_id
                elif self.action_type == 'move':
                    self.picking_type_id = warehouse.int_type_id
                elif self.action_type == 'transfer':
                    self.picking_type_id = warehouse.int_type_id
    
    def action_confirm(self):
        """Xác nhận và tạo stock picking"""
        self.ensure_one()
        
        if not self.picking_type_id:
            raise UserError(_('Vui lòng chọn loại phiếu!'))
        
        if not self.product_id and not self.quant_ids:
            raise UserError(_('Vui lòng chọn sản phẩm từ sơ đồ hoặc chọn thủ công!'))
        
        # Validate tracking by serial
        if self.product_id and self.product_id.tracking == 'serial':
            if not self.scanned_serial_ids:
                raise UserError(_(
                    'Sản phẩm này yêu cầu tracking theo Serial Number!\n'
                    'Vui lòng quét barcode/QR của từng sản phẩm cần xuất.'
                ))
            
            if len(self.scanned_serial_ids) != int(self.quantity):
                raise UserError(_(
                    f'Số serial đã quét ({len(self.scanned_serial_ids)}) '
                    f'không khớp với số lượng ({int(self.quantity)})!\n'
                    f'Vui lòng quét đủ số lượng serial cần xuất.'
                ))
        
        # Validate số lượng
        if self.product_id and self.quantity <= 0:
            raise UserError(_('Số lượng phải lớn hơn 0!'))
        
        # Validate số lượng không vượt available
        available = max(0, self.available_qty)  # Đảm bảo không âm
        if self.product_id and self.quantity > available:
            raise UserError(_(
                f'Số lượng yêu cầu ({self.quantity:.2f}) vượt quá số lượng có sẵn ({available:.2f})!\n'
                f'Vui lòng kiểm tra lại.'
            ))
        
        # Tạo picking
        picking_vals = {
            'picking_type_id': self.picking_type_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': self._get_dest_location().id,
            'origin': f'{self.action_type.upper()} - {self.location_id.name}',
        }
        
        picking = self.env['stock.picking'].create(picking_vals)
        
        # Tạo stock moves
        if self.quant_ids:
            # Nếu đã chọn quants cụ thể
            for quant in self.quant_ids:
                self._create_stock_move(picking, quant.product_id, quant.lot_id, 
                                       min(quant.quantity, quant.quantity - quant.reserved_quantity))
        elif self.product_id:
            # Nếu chọn sản phẩm/lot cụ thể
            self._create_stock_move(picking, self.product_id, self.lot_id, self.quantity)
        else:
            raise UserError(_('Vui lòng chọn sản phẩm hoặc lot để di chuyển!'))
        
        # Confirm picking
        picking.action_confirm()
        
        # Đánh dấu serial đã được pick (nếu có)
        if self.scanned_serial_ids:
            self.scanned_serial_ids.write({'is_picked': True})
        
        # Auto-validate nếu là pick (xuất kho) hoặc transfer (chuyển kho)
        if self.action_type in ('pick', 'transfer'):
            try:
                # Validate picking để trigger update quantity
                picking.button_validate()
                return {
                    'type': 'ir.actions.act_window_close',
                }
            except Exception as e:
                # Nếu có lỗi, mở form để user xử lý
                return {
                    'name': _('Phiếu kho'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'stock.picking',
                    'res_id': picking.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
        else:
            # Move thì mở form
            return {
                'name': _('Phiếu kho'),
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'res_id': picking.id,
                'view_mode': 'form',
                'target': 'current',
            }
    
    def _get_dest_location(self):
        """Lấy vị trí đích dựa vào loại action"""
        if self.action_type == 'pick':
            # Lấy hàng -> customer location
            if self.dest_location_id:
                return self.dest_location_id
            return self.picking_type_id.default_location_dest_id
        elif self.action_type in ('move', 'transfer'):
            # Chuyển vị trí/kho
            if not self.dest_location_id:
                raise UserError(_('Vui lòng chọn vị trí đích!'))
            return self.dest_location_id
        
        return self.location_id
    
    def _create_stock_move(self, picking, product, lot, quantity):
        """Tạo stock move line"""
        move_vals = {
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': quantity,
            'product_uom': product.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
        }
        
        move = self.env['stock.move'].create(move_vals)
        
        # Nếu có lot thì gán vào move line
        if lot:
            move_line_vals = {
                'move_id': move.id,
                'product_id': product.id,
                'location_id': self.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'lot_id': lot.id,
                'quantity': quantity,
                'product_uom_id': product.uom_id.id,
                'picking_id': picking.id,
            }
            self.env['stock.move.line'].create(move_line_vals)
        
        return move
