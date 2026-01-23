# Warehouse Map 3D - Sơ đồ Kho 3D

## Tổng quan

Module mở rộng chức năng warehouse map từ 2D lên 3D, cho phép quản lý vị trí hàng hóa trong không gian 3 chiều.

## Các file đã tạo

### Models
- `models/warehouse_map_3d.py`: Model chính cho sơ đồ 3D
  - `warehouse.map.3d`: Quản lý cấu hình sơ đồ 3D
  - `warehouse.map.blocked.cell.3d`: Quản lý ô bị chặn trong 3D

### Views
- `views/warehouse_map_3d_views.xml`: Views cho sơ đồ 3D
  - Form view với đầy đủ cấu hình
  - List view
  - Kanban view với nút xem 3D

### Wizards
- `wizard/assign_lot_position_3d_wizard.py`: Wizard gán tọa độ 3D
- `wizard/assign_lot_position_3d_wizard_views.xml`: View của wizard

### Frontend (JavaScript/CSS/XML)
- `static/src/js/warehouse_map_3d_view.js`: Component OWL render 3D với Three.js
- `static/src/css/warehouse_map_3d.css`: Styles cho giao diện 3D
- `static/src/xml/warehouse_map_3d.xml`: Template OWL cho view 3D

### Documentation
- `USAGE_GUIDE_3D.md`: Hướng dẫn sử dụng chi tiết
- `README_3D.md`: File này

## Tính năng

### 1. Cấu hình Sơ đồ 3D
- **Kích thước**: X (cột), Y (hàng), Z (tầng)
- **Kích thước thực tế**: Rộng, sâu, cao (mét)
- **Phân vùng**: Spacing intervals cho mỗi chiều
- **Cài đặt hiển thị**: Grid, axes, labels

### 2. Nhập Tọa Độ
- Wizard gán tọa độ (X, Y, Z) cho lot/serial
- Kiểm tra tự động:
  - Ô đã bị chiếm
  - Ô bị chặn
  - Tọa độ vượt quá giới hạn
- Tương thích với workflow 2D hiện tại

### 3. Hiển Thị 3D
- Render 3D tương tác với Three.js
- Màu sắc theo mức độ khả dụng
- Điều khiển camera (xoay, zoom, pan)
- Click để xem chi tiết ô
- Lọc theo tầng

### 4. Quản Lý Ô Bị Chặn
- Chặn/bỏ chặn ô theo tọa độ 3D
- Lý do chặn
- Hiển thị màu xám trên sơ đồ

## Cấu trúc Database

### warehouse.map.3d
```
- id
- name (Tên sơ đồ)
- warehouse_id (FK: stock.warehouse)
- location_id (FK: stock.location)
- rows (Số hàng - Y)
- columns (Số cột - X)
- levels (Số tầng - Z)
- cell_width (Độ rộng ô - m)
- cell_depth (Độ sâu ô - m)
- cell_height (Độ cao ô - m)
- row_spacing_interval
- column_spacing_interval
- level_spacing_interval
- show_grid
- show_axes
- show_labels
- sequence
- active
```

### warehouse.map.blocked.cell.3d
```
- id
- warehouse_map_3d_id (FK: warehouse.map.3d)
- posx (Vị trí X)
- posy (Vị trí Y)
- posz (Vị trí Z)
- reason (Lý do chặn)
- display_name (Computed)
```

### Sử dụng lại fields từ stock.quant
```
- posx (Đã có trong 2D)
- posy (Đã có trong 2D)
- posz (Đã có trong 2D)
- display_on_map (Đã có trong 2D)
```

## Workflow Tích Hợp

### 1. Nhập Hàng
```
Phiếu nhập → Xác nhận → Wizard gán tọa độ 3D → Xem trên sơ đồ 3D
```

### 2. Xuất Hàng
```
Xem sơ đồ 3D → Tìm lot theo vị trí → Tạo phiếu xuất → Tự động cập nhật
```

### 3. Kiểm Kê
```
Sơ đồ 3D → Lọc theo tầng → Kiểm tra từng tầng → Đối chiếu
```

## API Methods

### warehouse.map.3d

#### get_map_3d_data(map_id)
Lấy toàn bộ dữ liệu sơ đồ 3D bao gồm lots, blocked cells, configurations.

**Returns:**
```python
{
    'id': int,
    'name': str,
    'rows': int,
    'columns': int,
    'levels': int,
    'cell_width': float,
    'cell_depth': float,
    'cell_height': float,
    'row_spacing_interval': int,
    'column_spacing_interval': int,
    'level_spacing_interval': int,
    'show_grid': bool,
    'show_axes': bool,
    'show_labels': bool,
    'warehouse_id': int,
    'warehouse_name': str,
    'lots': {
        'x_y_z': {
            'quant_id': int,
            'product_id': int,
            'product_name': str,
            'lot_name': str,
            'quantity': float,
            'available_quantity': float,
            'x': int,
            'y': int,
            'z': int,
            ...
        }
    },
    'blocked_cells': {
        'x_y_z': {
            'id': int,
            'posx': int,
            'posy': int,
            'posz': int,
            'reason': str
        }
    }
}
```

#### action_view_map_3d()
Mở client action để hiển thị sơ đồ 3D.

#### action_open_block_cell_3d_wizard(posx, posy, posz)
Mở wizard để chặn/bỏ chặn ô tại tọa độ chỉ định.

### warehouse.map.blocked.cell.3d

#### get_blocked_cells_dict(map_3d_id)
Trả về dictionary các ô bị chặn với key là 'x_y_z'.

## Three.js Integration

### Load từ CDN
```javascript
https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js
https://cdn.jsdelivr.net/npm/three@0.160.0/examples/js/controls/OrbitControls.js
```

### Components
- **Scene**: Môi trường 3D
- **Camera**: PerspectiveCamera với FOV 60°
- **Renderer**: WebGLRenderer với antialias
- **Controls**: OrbitControls cho tương tác
- **Raycaster**: Cho mouse picking
- **Lights**: Ambient + Directional

### Rendering
- BoxGeometry cho mỗi ô
- MeshPhongMaterial với màu theo trạng thái
- EdgesGeometry cho đường viền
- Sprite cho labels

## Menu Structure
```
Kho hàng
  └── Sơ đồ kho
       ├── Sơ đồ kho 2D (existing)
       └── Sơ đồ kho 3D (new)
```

## Security
- Access rights cho stock users & managers
- Model: `warehouse.map.3d`
- Model: `warehouse.map.blocked.cell.3d`
- Wizard: `assign.lot.position.3d.wizard`

## Dependencies
- `stock`: Odoo stock module
- `product`: Product management
- Tương thích với module `warehouse_map` 2D hiện tại

## Browser Requirements
- WebGL support
- Modern browser (Chrome, Firefox, Edge)
- JavaScript enabled

## Performance Considerations
- Kho lớn (>1000 ô):
  - Xem theo tầng thay vì tất cả
  - Tắt labels
  - Giảm số ô render
- Optimize geometry với BufferGeometry
- Reuse materials

## Future Enhancements
- [ ] Export sơ đồ 3D sang PDF/Image
- [ ] VR/AR support
- [ ] Heatmap theo turnover
- [ ] Path finding tối ưu
- [ ] Integration với barcode scanner
- [ ] Mobile responsive
- [ ] Batch assign positions
- [ ] Import/Export coordinates từ Excel

## Changelog

### Version 1.0.0 (2026-01-23)
- Initial release
- 3D warehouse map with Three.js
- Coordinate assignment wizard
- Blocked cells management
- Interactive 3D visualization
- Level filtering
- Click to view cell details

## Support
- Email: quochuy.software@gmail.com
- Developed with Claude.ai assistance

## License
LGPL-3
