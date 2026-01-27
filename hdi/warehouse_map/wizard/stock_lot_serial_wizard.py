# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime


class StockLotSerialWizard(models.TransientModel):
    _name = 'stock.lot.serial.wizard'
    _description = 'Wizard gom Serial vào Lot - Bước 1: Nhập Serial'

    picking_id = fields.Many2one('stock.picking', string='Phiếu nhập kho', required=True, readonly=True)
    move_line_ids = fields.Many2many('stock.move.line', string='Move Line (Serial)', required=True)
    
    # Chọn sản phẩm - auto detect hoặc cho user chọn
    product_id = fields.Many2one('product.product', string='Sản phẩm', 
                                  domain="[('tracking', 'in', ('lot', 'serial'))]")
    
    # Danh sách move_line với serial_number để user nhập
    wizard_move_line_ids = fields.One2many('stock.wizard.move.line', 'wizard_id', 
                                            string='Sản phẩm')
    
    @api.model
    def default_get(self, fields_list):
        """Auto-detect product và populate wizard_move_line"""
        result = super().default_get(fields_list)
        
        # Lấy move_line từ context
        move_line_data = self._context.get('default_move_line_ids')
        if move_line_data:
            move_line_ids = []
            
            # Handle tuple format (6, 0, [ids]) from context
            # The format comes as: [(6, 0, [id1, id2, id3])]
            if isinstance(move_line_data, list) and move_line_data:
                first_item = move_line_data[0]
                if isinstance(first_item, tuple) and len(first_item) == 3:
                    # This is the command format (6, 0, list_of_ids)
                    move_line_ids = first_item[2]
                else:
                    # Direct list of ids: [id1, id2, id3]
                    move_line_ids = move_line_data
            
            # Ensure move_line_ids is a proper list of integers
            if move_line_ids and isinstance(move_line_ids, list):
                try:
                    # Convert any non-integer values to integers
                    move_line_ids = [int(mid) for mid in move_line_ids if mid]
                    
                    if move_line_ids:
                        # Lấy danh sách move_line record
                        move_lines = self.env['stock.move.line'].browse(move_line_ids)
                        
                        # Filter valid move_lines
                        move_lines = move_lines.exists()
                        
                        if move_lines:
                            # *** IMPORTANT: Populate move_line_ids Many2many field ***
                            result['move_line_ids'] = [(6, 0, move_lines.ids)]
                            
                            # Kiểm tra tất cả cùng product không
                            products = move_lines.mapped('product_id').ids
                            if len(set(products)) == 1:
                                # Tất cả cùng product → auto detect
                                result['product_id'] = products[0]
                            
                            # Populate wizard_move_line với TẤT CẢ move_lines
                            wizard_lines = []
                            for idx, move_line in enumerate(move_lines, 1):
                                wizard_lines.append((0, 0, {
                                    'move_line_id': move_line.id,
                                    'product_id': move_line.product_id.id,
                                    'sequence': idx * 10,
                                }))
                            result['wizard_move_line_ids'] = wizard_lines
                except (TypeError, ValueError):
                    # If conversion fails, silently skip
                    pass
        
        return result
    
    total_serials = fields.Integer(string='Tổng serial', compute='_compute_total_serials')
    
    @api.depends('wizard_move_line_ids')
    def _compute_total_serials(self):
        """Đếm số serial được chọn"""
        for wizard in self:
            wizard.total_serials = len(wizard.wizard_move_line_ids)
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Cập nhật wizard_move_line khi thay đổi product"""
        if self.product_id and self.move_line_ids:
            # Filter move_line theo product được chọn
            filtered_move_lines = self.move_line_ids.filtered(
                lambda x: x.product_id.id == self.product_id.id
            )
            
            if filtered_move_lines:
                # Cập nhật wizard_move_line_ids
                wizard_lines = []
                for idx, move_line in enumerate(filtered_move_lines, 1):
                    wizard_lines.append((0, 0, {
                        'move_line_id': move_line.id,
                        'product_id': move_line.product_id.id,
                        'sequence': idx * 10,
                    }))
                self.wizard_move_line_ids = wizard_lines
    
    def action_confirm_serials(self):
        """Xác nhận serial đã nhập và mở popup chọn lot"""
        self.ensure_one()
        
        if not self.move_line_ids:
            raise UserError(_('Vui lòng chọn ít nhất 1 move_line!'))
        
        if not self.product_id:
            raise UserError(_('Vui lòng chọn sản phẩm!'))
        
        if not self.wizard_move_line_ids:
            raise UserError(_('Không có sản phẩm nào để xử lý!'))
        
        # Kiểm tra tất cả serial đã được nhập
        for wml in self.wizard_move_line_ids:
            if not wml.serial_number or not wml.serial_number.strip():
                raise UserError(_(
                    f'❌ Serial chưa được nhập cho sản phẩm: {wml.product_id.name}'
                ))
        
        # Kiểm tra serial không trùng
        serial_numbers = [wml.serial_number.strip() for wml in self.wizard_move_line_ids]
        if len(serial_numbers) != len(set(serial_numbers)):
            raise UserError(_('❌ Có serial bị trùng lặp!'))
        
        # Mở popup chọn lot (bước 2)
        lot_wizard = self.env['stock.lot.selection.wizard'].create({
            'picking_id': self.picking_id.id,
            'move_line_ids': [(6, 0, self.move_line_ids.ids)],
            'product_id': self.product_id.id,
            'wizard_move_line_ids': [(6, 0, self.wizard_move_line_ids.ids)],
        })
        
        return {
            'name': _('Chọn Lot'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot.selection.wizard',
            'res_id': lot_wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }


class StockWizardMoveLine(models.TransientModel):
    _name = 'stock.wizard.move.line'
    _description = 'Move Line trong Wizard Gom Serial'
    _order = 'sequence'
    
    wizard_id = fields.Many2one('stock.lot.serial.wizard', string='Wizard', ondelete='cascade')
    move_line_id = fields.Many2one('stock.move.line', string='Move Line', readonly=True)
    product_id = fields.Many2one('product.product', string='Sản phẩm', readonly=True)
    product_name = fields.Char(string='Sản phẩm', compute='_compute_product_name', readonly=True)
    serial_number = fields.Char(string='Serial/Barcode', required=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
    
    @api.depends('product_id')
    def _compute_product_name(self):
        """Hiển thị tên sản phẩm"""
        for line in self:
            line.product_name = line.product_id.display_name if line.product_id else ''


class StockLotSelectionWizard(models.TransientModel):
    _name = 'stock.lot.selection.wizard'
    _description = 'Wizard gom Serial vào Lot - Bước 2: Chọn Lot'

    picking_id = fields.Many2one('stock.picking', string='Phiếu nhập kho', required=True, readonly=True)
    move_line_ids = fields.Many2many('stock.move.line', string='Move Line (Serial)', required=True, readonly=True)
    product_id = fields.Many2one('product.product', string='Sản phẩm', required=True, readonly=True)
    
    # Lưu tạm wizard_move_line_ids từ popup trước
    wizard_move_line_ids = fields.Many2many('stock.wizard.move.line', 'lot_selection_wizard_move_line_rel',
                                             string='Serial đã nhập', readonly=True)
    
    # Tạo hoặc chọn lot
    lot_create_option = fields.Selection([
        ('create_new', 'Tạo lot mới'),
        ('select_existing', 'Chọn lot đã tạo'),
    ], string='Tùy chọn', default='create_new', required=True)
    
    # Option: Tạo lot mới
    lot_name = fields.Char(string='Tên Lot mới')
    lot_barcode = fields.Char(string='Barcode Lot')
    
    # Option: Chọn lot từ dropdown
    existing_lot_id = fields.Many2one('stock.lot', string='Chọn Lot đã tạo',
                                       domain="[('product_id', '=', product_id)]")
    
    @api.onchange('lot_create_option')
    def _onchange_lot_create_option(self):
        """Clear fields khi switch giữa các option"""
        if self.lot_create_option == 'create_new':
            self.existing_lot_id = False
        else:
            self.lot_name = ''
            self.lot_barcode = ''
    
    def action_confirm_assign_serials(self):
        """Gom serial vào lot và cập nhật move_line"""
        self.ensure_one()
        
        # Bước 1: Tạo hoặc lấy lot_id
        if self.lot_create_option == 'create_new':
            if not self.lot_name:
                raise UserError(_('Vui lòng nhập tên lot!'))
            
            # Tạo lot mới
            lot_vals = {
                'product_id': self.product_id.id,
                'name': self.lot_name,
            }
            
            if self.lot_barcode:
                lot_vals['barcode'] = self.lot_barcode
            
            lot = self.env['stock.lot'].create(lot_vals)
        else:
            if not self.existing_lot_id:
                raise UserError(_('Vui lòng chọn lot!'))
            lot = self.existing_lot_id
        
        # Bước 2: Cập nhật tất cả move_line với lot_id này
        filtered_move_lines = self.move_line_ids.filtered(
            lambda x: x.product_id.id == self.product_id.id
        )
        filtered_move_lines.write({'lot_id': lot.id})
        
        # Bước 3: Tạo stock.serial.item records từ wizard_move_line_ids
        for wml in self.wizard_move_line_ids:
            self.env['stock.serial.item'].create({
                'lot_id': lot.id,
                'serial_number': wml.serial_number.strip(),
                'sequence': wml.sequence,
            })
        
        # Reload picking để cập nhật data
        self.picking_id._onchange_picking_type()
        
        # Quay lại phiếu nhập kho
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'current',
        }


class StockLotDetailWizard(models.TransientModel):
    _name = 'stock.lot.detail.wizard'
    _description = 'Xem chi tiết Lot với Serial'

    quant_id = fields.Many2one('stock.quant', string='Quant', required=True, readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Lot', required=True, readonly=True, related='quant_id.lot_id')
    product_id = fields.Many2one('product.product', string='Sản phẩm', required=True, readonly=True, related='quant_id.product_id')
    location_id = fields.Many2one('stock.location', string='Vị trí', readonly=True, related='quant_id.location_id')
    quantity = fields.Float(string='Số lượng', readonly=True, related='quant_id.quantity')
    
    # Danh sách serial của lot
    serial_item_ids = fields.One2many('stock.serial.item', compute='_compute_serial_items',
                                        string='Danh sách Serial')
    
    @api.depends('lot_id')
    def _compute_serial_items(self):
        """Lấy danh sách serial từ lot"""
        for wizard in self:
            if wizard.lot_id:
                wizard.serial_item_ids = self.env['stock.serial.item'].search([
                    ('lot_id', '=', wizard.lot_id.id)
                ], order='sequence asc')
            else:
                wizard.serial_item_ids = False
    
    @api.model
    def default_get(self, fields_list):
        """Auto-load từ context"""
        result = super().default_get(fields_list)
        
        quant_id = self._context.get('default_quant_id')
        if quant_id:
            quant = self.env['stock.quant'].browse(quant_id)
            if quant.exists():
                result['quant_id'] = quant.id
                if quant.lot_id:
                    result['lot_id'] = quant.lot_id.id
        
        return result
