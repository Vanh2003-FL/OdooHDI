{
    'name': 'Warehouse Diagram',
    'version': '18.0.1.0',
    'category': 'Inventory',
    'description': """
        Module Sơ đồ Kho cho hệ thống quản lý tồn kho.
        Cho phép thiết kế sơ đồ 2D kho, quản lý kệ (Shelves), ô hàng (Bins), 
        và khu vực không lưu trữ (Areas).
    """,
    'author': 'HDI',
    'license': 'LGPL-3',
    'depends': ['stock', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/warehouse_view_views.xml',
        'views/warehouse_area_views.xml',
        'views/warehouse_shelves_views.xml',
        'views/warehouse_bin_views.xml',
        'views/warehouse_diagram_menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
