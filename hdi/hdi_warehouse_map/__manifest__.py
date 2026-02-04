# -*- coding: utf-8 -*-
{
    'name': 'HDI Warehouse Map 2D/3D',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Warehouse',
    'summary': 'Warehouse visualization with 2D/3D layout mapping',
    'description': """
        HDI Warehouse Map - Visual Warehouse Management
        ================================================
        * 2D/3D warehouse layout visualization
        * Location mapping with coordinates (x, y, z)
        * Drag & drop layout editor
        * Real-time stock quantity visualization
        * Barcode scanning with bin highlighting
        * Lot/Serial tracking on warehouse map
        * Compatible with SKUSavvy workflow
        
        Location Structure:
        - Stock > Zone > Rack > Bin
        - Bin = stock.location (usage=internal)
        - Lot/Serial stored in Bins
    """,
    'author': 'HDI',
    'website': 'https://www.hdi.com',
    'depends': [
        'stock',
        'barcodes',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_location_layout_views.xml',
        'views/stock_location_views.xml',
        'views/warehouse_map_views.xml',
        'views/warehouse_map_templates.xml',
        'data/location_demo_data.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hdi_warehouse_map/static/src/js/warehouse_map_2d.js',
            'hdi_warehouse_map/static/src/js/warehouse_map_3d.js',
            'hdi_warehouse_map/static/src/js/warehouse_map_controller.js',
            'hdi_warehouse_map/static/src/xml/warehouse_map.xml',
            'hdi_warehouse_map/static/src/css/warehouse_map.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
