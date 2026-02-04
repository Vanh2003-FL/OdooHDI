# -*- coding: utf-8 -*-
"""
🧪 Test Warehouse Map API Controllers
======================================
Tests for JSON API endpoints
"""

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install', 'warehouse_map')
class TestWarehouseMapAPI(HttpCase):
    
    def setUp(self):
        super().setUp()
        
        # Authenticate
        self.authenticate('admin', 'admin')
        
        # Create test data
        self.warehouse = self.env['stock.warehouse'].create({
            'name': 'API Test Warehouse',
            'code': 'ATWH',
        })
        
        self.zone = self.env['stock.location'].create({
            'name': 'Zone-API',
            'location_id': self.warehouse.lot_stock_id.id,
            'usage': 'view',
            'location_type': 'zone',
        })
        
        self.bin = self.env['stock.location'].create({
            'name': 'Bin-API-01',
            'location_id': self.zone.id,
            'usage': 'internal',
            'location_type': 'bin',
        })
        
        self.layout = self.env['stock.location.layout'].create({
            'warehouse_id': self.warehouse.id,
            'location_id': self.bin.id,
            'location_type': 'bin',
            'x': 100.0,
            'y': 150.0,
        })
        
        self.product = self.env['product.product'].create({
            'name': 'API Test Product',
            'type': 'product',
            'tracking': 'serial',
        })
        
        self.serial = self.env['stock.lot'].create({
            'name': 'API-SERIAL-001',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })
        
        # Add stock
        self.env['stock.quant']._update_available_quantity(
            self.product,
            self.bin,
            1.0,
            lot_id=self.serial
        )
    
    def test_get_warehouse_layout_api(self):
        """Test GET /warehouse_map/layout/<warehouse_id>"""
        response = self.url_open(
            f'/warehouse_map/layout/{self.warehouse.id}',
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data['warehouse_id'], self.warehouse.id)
        self.assertTrue('zones' in data)
    
    def test_scan_serial_api(self):
        """Test POST /warehouse_map/scan_serial"""
        response = self.url_open(
            '/warehouse_map/scan_serial',
            data={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'serial_number': 'API-SERIAL-001'
                }
            },
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        result = data.get('result', {})
        
        self.assertEqual(result['lot_name'], 'API-SERIAL-001')
        self.assertTrue(len(result['bins']) > 0)
    
    def test_get_bin_details_api(self):
        """Test GET /warehouse_map/bin_details/<location_id>"""
        response = self.url_open(
            f'/warehouse_map/bin_details/{self.bin.id}',
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data['location_id'], self.bin.id)
        self.assertTrue('quants' in data)
        self.assertEqual(data['lot_count'], 1)
    
    def test_update_layout_api(self):
        """Test POST /warehouse_map/update_layout"""
        new_x = 200.0
        new_y = 250.0
        
        response = self.url_open(
            '/warehouse_map/update_layout',
            data={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'layout_id': self.layout.id,
                    'x': new_x,
                    'y': new_y
                }
            },
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        result = data.get('result', {})
        
        self.assertTrue(result.get('success'))
        
        # Verify database updated
        self.layout.refresh()
        self.assertEqual(self.layout.x, new_x)
        self.assertEqual(self.layout.y, new_y)
    
    def test_search_product_api(self):
        """Test POST /warehouse_map/search_product"""
        response = self.url_open(
            '/warehouse_map/search_product',
            data={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'warehouse_id': self.warehouse.id,
                    'product_name': 'API Test Product'
                }
            },
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        result = data.get('result', {})
        
        self.assertTrue('bins' in result)
        self.assertTrue(len(result['bins']) > 0)
    
    def test_get_heatmap_api(self):
        """Test GET /warehouse_map/heatmap/<warehouse_id>"""
        response = self.url_open(
            f'/warehouse_map/heatmap/{self.warehouse.id}',
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should return location_id: percentage mapping
        self.assertIsInstance(data, dict)
