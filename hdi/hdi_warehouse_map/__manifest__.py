# -*- coding: utf-8 -*-
{
    'name': 'HDI Warehouse Map & Bin Management',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Quản lý sơ đồ kho 2D/3D với cấu trúc Zone-Aisle-Rack-Level-Bin',
    'description': """
        Warehouse Map & Bin Management
        ===============================
        * Quản lý cấu trúc kho: Zone → Aisle → Rack → Level → Bin
        * Ràng buộc SKU và Lot/Sê-ri theo Bin
        * Đề xuất vị trí Putaway thông minh
        * Picking strategy với highlight visualization
        * Hiển thị sơ đồ kho 2D/3D tương tác
        * Block Bin/Lot không hợp lệ
        * Truy xuất lịch sử di chuyển
    """,
    'author': 'HDI',
    'website': 'https://www.hdi.com',
    'depends': [
        'stock',
        'web',
    ],
    'data': [
        # Security
        'security/warehouse_map_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/warehouse_map_data.xml',
        
        # Views - Structure
        'views/warehouse_zone_views.xml',
        'views/warehouse_aisle_views.xml',
        'views/warehouse_rack_views.xml',
        'views/warehouse_level_views.xml',
        'views/warehouse_bin_views.xml',
        
        # Views - Operations
        'views/stock_location_views.xml',
        'views/stock_quant_views.xml',
        'views/stock_move_views.xml',
        'views/stock_picking_views.xml',
        
        # Views - History & Reports
        'views/bin_history_views.xml',
        'views/lot_history_views.xml',
        
        # Wizard
        'wizard/bin_block_wizard_views.xml',
        'wizard/putaway_suggestion_views.xml',
        
        # Menu
        'views/menu_views.xml',
        
        # Assets
        'views/warehouse_map_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hdi_warehouse_map/static/src/js/warehouse_map_2d.js',
            'hdi_warehouse_map/static/src/js/warehouse_map_3d.js',
            'hdi_warehouse_map/static/src/js/warehouse_map_widget.js',
            'hdi_warehouse_map/static/src/xml/warehouse_map_templates.xml',
            'hdi_warehouse_map/static/src/css/warehouse_map.css',
        ],
    },
    'demo': [
        'demo/warehouse_map_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
