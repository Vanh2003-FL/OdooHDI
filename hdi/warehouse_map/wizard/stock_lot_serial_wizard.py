# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime


class StockLotSerialWizard(models.TransientModel):
    _name = 'stock.lot.serial.wizard'
    _description = 'Wizard gom Serial vào Lot'

    picking_id = fields.Many2one('stock.picking', string='Phiếu nhập kho', required=True, readonly=True)
    move_line_ids = fields.Many2many('stock.move.line', string='Move Line (Serial)', required=True)
    product_id = fields.Many2one('product.product', string='Sản phẩm', related='move_line_ids.product_id', readonly=True)
    
    # Quét barcode serial
    barcode_input = fields.Char(string='🔍 Quét Barcode Serial')
    scanned_serial_ids = fields.One2many('stock.scanned.serial', 'wizard_id', string='Serial đã quét')
    scanned_count = fields.Integer(string='Số serial đã quét', compute='_compute_scanned_count')
    
    @api.depends('scanned_serial_ids')
    def _compute_scanned_count(self):
        """Đếm số serial đã quét"""
        for wizard in self:
            wizard.scanned_count = len(wizard.scanned_serial_ids)
    
    @api.onchange('barcode_input')
    def _onchange_barcode_input(self):
        """Quét barcode: tìm product từ barcode và thêm vào danh sách serial"""
        if not self.barcode_input:
            return
        
        barcode = self.barcode_input.strip()
        
        # Tìm product từ barcode
        product = self.env['product.product'].search([
            ('barcode', '=', barcode)
        ], limit=1)
        
        if not product:
            raise UserError(_('❌ Không tìm thấy sản phẩm với barcode: %s') % barcode)
        
        # Kiểm tra sản phẩm có tracking không
        if product.tracking == 'none':
            raise UserError(_('❌ Sản phẩm này không có tracking lot/serial!'))
        
        # Kiểm tra sản phẩm có khớp với move_line không
        if self.product_id and product.id != self.product_id.id:
            raise UserError(_('❌ Barcode không khớp! Phải quét sản phẩm: %s') % self.product_id.name)
        
        # Kiểm tra barcode đã quét chưa
        existing = self.env['stock.scanned.serial'].search([
            ('wizard_id', '=', self.id),
            ('serial_number', '=', barcode)
        ], limit=1)
        
        if existing:
            raise UserError(_('⚠️ Barcode này đã quét rồi: %s') % barcode)
        
        # Thêm serial vào danh sách
        self.env['stock.scanned.serial'].create({
            'wizard_id': self.id,
            'product_id': product.id,
            'serial_number': barcode,
            'sequence': (len(self.scanned_serial_ids) + 1) * 10,
        })
        
        # Clear input field
        self.barcode_input = ''
    
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
    
    total_serials = fields.Integer(string='Tổng serial', compute='_compute_total_serials')
    
    @api.depends('move_line_ids')
    def _compute_total_serials(self):
        """Đếm số serial được chọn"""
        for wizard in self:
            wizard.total_serials = len(wizard.move_line_ids)
    
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
        
        if not self.move_line_ids:
            raise UserError(_('Vui lòng chọn ít nhất 1 move_line!'))
        
        # Kiểm tra đã quét serial chưa
        if not self.scanned_serial_ids:
            raise UserError(_('⚠️ Vui lòng quét ít nhất 1 serial!'))
        
        # Kiểm tra số serial quét khớp với số move_line không
        if len(self.scanned_serial_ids) != len(self.move_line_ids):
            raise UserError(_(
                f'❌ Số serial quét ({len(self.scanned_serial_ids)}) không khớp '
                f'với số move_line ({len(self.move_line_ids)})!'
            ))
        
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
        self.move_line_ids.write({'lot_id': lot.id})
        
        # Bước 3: Tạo stock.serial.item records từ scanned_serial_ids
        for scanned in self.scanned_serial_ids:
            self.env['stock.serial.item'].create({
                'lot_id': lot.id,
                'serial_number': scanned.serial_number,
                'sequence': scanned.sequence,
            })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot',
            'res_id': lot.id,
            'view_mode': 'form',
            'target': 'current',
        }


class StockScannedSerial(models.TransientModel):
    _name = 'stock.scanned.serial'
    _description = 'Serial Đã Quét (Temp)'
    _order = 'sequence, id'
    
    wizard_id = fields.Many2one('stock.lot.serial.wizard', string='Wizard', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Sản phẩm')
    product_code = fields.Char(string='Mã sản phẩm', related='product_id.default_code', readonly=True)
    serial_number = fields.Char(string='Barcode/Serial', required=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
    
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.product_code} - {record.serial_number}" if record.product_code else record.serial_number
            result.append((record.id, name))
        return result
