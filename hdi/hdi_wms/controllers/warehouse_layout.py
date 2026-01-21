# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import json


class WarehouseLayoutController(http.Controller):

    @http.route('/hdi_wms/warehouse_3d/<int:layout_id>', auth='user', type='http')
    def warehouse_3d_view(self, layout_id, **kwargs):
        """Display 3D warehouse viewer"""
        layout = request.env['warehouse.layout'].browse(layout_id)
        
        if not layout.exists():
            return request.not_found()
        
        # Generate 3D data
        data_3d = layout.generate_3d_data()
        
        # Convert to JSON string
        data_json = json.dumps(data_3d)
        
        # Create HTML response
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8"/>
            <title>Sơ Đồ Kho 3D - {layout.name}</title>
            <link rel="stylesheet" href="/web/static/lib/bootstrap/css/bootstrap.min.css"/>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; }}
                #warehouse-3d-container {{ display: flex; align-items: center; justify-content: center; width: 100%; }}
                .card {{ border: 1px solid #ddd; border-radius: 4px; }}
                .card-header {{ padding: 10px 15px; border-bottom: 1px solid #ddd; }}
                .card-body {{ padding: 15px; }}
            </style>
        </head>
        <body>
            <div class="container-fluid" style="padding: 20px; height: 100vh; display: flex; flex-direction: column;">
                <!-- Header -->
                <div class="row mb-3">
                    <div class="col-md-8">
                        <h2>Sơ Đồ Kho 3D - {layout.name}</h2>
                        <p class="text-muted">{layout.warehouse_id.name} | Kích thước: {layout.max_x}×{layout.max_y}×{layout.max_z} m</p>
                    </div>
                    <div class="col-md-4 text-end">
                        <button class="btn btn-secondary" id="btn-reset">Reset View</button>
                        <button class="btn btn-info" id="btn-refresh">Cập Nhật</button>
                    </div>
                </div>

                <!-- Main Content -->
                <div class="row" style="flex: 1; overflow: hidden;">
                    <!-- Canvas Area -->
                    <div class="col-md-9" style="border: 1px solid #ddd; border-radius: 5px; background: #fafafa; overflow: hidden;">
                        <div id="warehouse-3d-container" style="width: 100%; height: 100%; position: relative;"></div>
                    </div>

                    <!-- Info Panel -->
                    <div class="col-md-3" style="padding-left: 10px;">
                        <!-- Statistics -->
                        <div class="card mb-3">
                            <div class="card-header bg-primary text-white">
                                <strong>Thống Kê</strong>
                            </div>
                            <div class="card-body">
                                <div class="mb-2">
                                    <small class="text-muted">Vị Trí:</small>
                                    <h5><span id="stat-locations">0</span></h5>
                                </div>
                                <div class="mb-2">
                                    <small class="text-muted">Lô Hàng:</small>
                                    <h5><span id="stat-batches">0</span></h5>
                                </div>
                                <div class="mb-2">
                                    <small class="text-muted">Dung Lượng Sử Dụng:</small>
                                    <div class="progress" style="height: 20px;">
                                        <div id="stat-capacity-bar" class="progress-bar bg-success" style="width: 0%;">
                                            <span id="stat-capacity-pct">0%</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Location Details -->
                        <div class="card">
                            <div class="card-header bg-info text-white">
                                <strong>Chi Tiết Vị Trí</strong>
                            </div>
                            <div class="card-body" id="location-info">
                                <p class="text-muted text-center">Nhấn vào vị trí để xem chi tiết</p>
                            </div>
                        </div>

                        <!-- Legend -->
                        <div class="card mt-3">
                            <div class="card-header bg-secondary text-white">
                                <strong>Hướng Dẫn</strong>
                            </div>
                            <div class="card-body">
                                <div class="mb-2">
                                    <small><strong>Kéo:</strong> Di chuyển sơ đồ</small>
                                </div>
                                <div class="mb-2">
                                    <small><strong>Cuộn:</strong> Phóng to/Thu nhỏ</small>
                                </div>
                                <div>
                                    <small><strong>Nhấn:</strong> Xem chi tiết vị trí</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <div class="row mt-3">
                    <div class="col-12">
                        <small class="text-muted">
                        Dùng chuột để di chuyển | Cuộn để zoom | Nhấn vị trí để xem chi tiết
                        </small>
                    </div>
                </div>
            </div>

            <!-- Script -->
            <script src="/web/static/lib/bootstrap/js/bootstrap.min.js"></script>
            <script src="/hdi_wms/static/src/js/warehouse_3d_viewer.js"></script>
            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    const warehouseData = {data_json};

                    const viewer = new Warehouse3DViewer('warehouse-3d-container', warehouseData);

                    document.getElementById('stat-locations').textContent = warehouseData.locations.length;
                    document.getElementById('stat-batches').textContent = warehouseData.batches.length;
                    
                    const avgCapacity = warehouseData.locations.length > 0 
                        ? warehouseData.locations.reduce((sum, loc) => sum + loc.capacity_pct, 0) / warehouseData.locations.length
                        : 0;
                    
                    document.getElementById('stat-capacity-pct').textContent = avgCapacity.toFixed(1) + '%';
                    document.getElementById('stat-capacity-bar').style.width = avgCapacity + '%';
                    
                    const capacityBar = document.getElementById('stat-capacity-bar');
                    if (avgCapacity < 50) {{
                        capacityBar.className = 'progress-bar bg-success';
                    }} else if (avgCapacity < 80) {{
                        capacityBar.className = 'progress-bar bg-warning';
                    }} else {{
                        capacityBar.className = 'progress-bar bg-danger';
                    }}

                    document.getElementById('btn-reset').addEventListener('click', function() {{
                        viewer.reset();
                    }});

                    document.getElementById('btn-refresh').addEventListener('click', function() {{
                        location.reload();
                    }});
                }});
            </script>
        </body>
        </html>
        """
        
        return request.make_response(html, [('Content-Type', 'text/html; charset=utf-8')])

