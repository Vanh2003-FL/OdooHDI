# HDI WMS - Tính Năng Kho 3D (Phiên Bản MVP)

## 📋 Tổng Quan

Hệ thống quản lý kho 3D đơn giản cho module `hdi_wms`, cho phép:
- 📍 Gán tọa độ 3D (X, Y, Z) cho các vị trí kho
- 🗺️ Tạo sơ đồ kho 3D (warehouse layout)
- 📊 Theo dõi dung lượng vị trí
- 🎯 Tính điểm tiếp cận vị trí
- 📦 Visualize lô hàng trên sơ đồ

## 🚀 Tính Năng

### 1. **Warehouse Layout - Sơ Đồ Kho**
- Quản lý sơ đồ kho với kích thước max (max_x, max_y, max_z)
- Theo dõi tất cả vị trí và lô hàng trong sơ đồ
- Thống kê dung lượng tổng thể
- Nút "Xem Sơ Đồ 3D" (sẵn sàng mở rộng)

**Model:** `warehouse.layout`

```
Trường chính:
- name: Tên sơ đồ
- warehouse_id: Kho liên kết
- max_x, max_y, max_z: Kích thước kho
- is_3d_enabled: Bật/tắt tính năng 3D
- location_ids: O2M - Tất cả vị trí
- layout_data_json: JSON dữ liệu visualization
```

### 2. **Stock Location - Mở Rộng Tọa Độ 3D**
Thêm fields vào stock.location:
- `coordinate_x, coordinate_y, coordinate_z`: Tọa độ 3D
- `coordinate_display`: Hiển thị dạng "X-Y-Z"
- `warehouse_layout_id`: Gán cho sơ đồ kho
- `color_code_hex`: Màu hiển thị (#RRGGBB)
- `accessibility_score`: Điểm tiếp cận (0-100)
- `location_3d_type`: Loại vị trí (regular/aisle/rack_section/door/hazard)

```python
# Ví dụ:
location.coordinate_x = 5      # Aisle 5
location.coordinate_y = 2      # Row 2
location.coordinate_z = 3      # Level 3
location.color_code_hex = '#4CAF50'  # Green
```

### 3. **Warehouse 3D Service**
Service tính toán 3D với các phương thức:

```python
# Khoảng cách 3D
service.calculate_distance_3d(loc1, loc2)       # Euclid
service.calculate_manhattan_distance(loc1, loc2) # Manhattan

# Tìm vị trí tốt nhất
closest = service.find_closest_available_location(
    product, quantity, from_location, warehouse_layout_id
)

# Sắp xếp theo tiếp cận
service.get_locations_by_accessibility(layout_id, limit=10)

# Tối ưu route lấy hàng
optimized_lines = service.optimize_picking_route_simple(picking_lines)

# Heatmap dung lượng
heatmap = service.get_heatmap_data(layout_id)
```

## 📊 Tính Điểm Tiếp Cận (Accessibility Score)

```
Score = 100 - (z * 5) - (capacity% * 0.3)

Ví dụ:
- Vị trí Z=0, 20% capacity: Score = 100 - 0 - 6 = 94
- Vị trí Z=3, 50% capacity: Score = 100 - 15 - 15 = 70
- Vị trí Z=5, 100% capacity: Score = 100 - 25 - 30 = 45
```

**Lợi ích:** Ưu tiên các vị trí thấp và ít chứa hàng → Lấy hàng nhanh hơn

## 🎨 UI/UX

### Warehouse Layout Form
- Tab "Vị Trí" - Danh sách tất cả locations với tọa độ
- Tab "Lô Hàng" - Tất cả batches
- Tab "Dữ Liệu JSON" - Xem raw data
- Nút "🗺️ Xem Sơ Đồ 3D" (ready for future integration)
- Gauge widget hiển thị % dung lượng

### Stock Location View
- Form thêm fields: warehouse_layout_id, color_code_hex, accessibility_score
- Tree view: Hiển thị tọa độ, accessibility_score, batch_count

### Menu
- **Sơ Đồ Kho 3D** (🗺️) → Kanban/List/Form warehouse.layout

## 📦 Demo Data

Tập tin: `data/warehouse_3d_demo.xml`

Tạo sẵn:
- 1 warehouse layout "Kho Chính" (30×20×6 mét)
- 3 aisle với các vị trí sample:
  - **Aisle A** (Z=1-3): Rack storage - Class A (nhanh)
  - **Aisle B** (Z=1): Pallet - Class B (trung bình)
  - **Aisle C** (Z=1): Bulk - Class C (chậm)
- 2 lối đi: Nhập hàng, Xuất hàng

## 🔧 Cách Sử Dụng

### Bước 1: Tạo Warehouse Layout
```
Menu > Quản lý Kho > Sơ Đồ Kho 3D > Tạo Mới
- Tên: "Kho Chính"
- Warehouse: Chọn kho
- Max X/Y/Z: 30/20/6
```

### Bước 2: Gán Tọa Độ cho Vị Trí
```
Menu > Stock > Locations > Chọn location > Form
- Sơ Đồ Kho 3D: Chọn layout
- Coordinate X/Y/Z: Nhập tọa độ
- Mã Màu: #4CAF50 (optional)
- Loại Vị Trí 3D: rack_section / pallet / bulk
```

### Bước 3: Xem Dữ Liệu
```
Warehouse Layout Form > Tab "Dữ Liệu JSON"
→ Xem JSON đầy đủ của layout (locations + batches)
```

## 🚀 Mở Rộng Trong Tương Lai

### Phase 2: Visualization 3D
- [ ] Three.js viewer (hiển thị 3D interactive)
- [ ] Drag-drop vị trí trên sơ đồ
- [ ] Real-time update batch locations

### Phase 3: Route Optimization
- [ ] Thuật toán S-curve picking
- [ ] Tính thời gian dự kiến
- [ ] Route heatmap

### Phase 4: Advanced Features
- [ ] Equipment management (xe nâng, thang)
- [ ] Aisle optimization
- [ ] Pathfinding A* algorithm
- [ ] Picking performance analytics

## 📝 API Service Examples

```python
# Lấy service
service = self.env['warehouse.3d.service']

# Tính khoảng cách
dist = service.calculate_distance_3d(loc1, loc2)
manhattan = service.calculate_manhattan_distance(loc1, loc2)

# Tìm vị trí gần nhất với dung lượng đủ
best_loc = service.find_closest_available_location(
    product=product,
    quantity=10,
    from_location=current_location,
    warehouse_layout_id=layout.id
)

# Lấy vị trí dễ tiếp cận nhất
accessible_locs = service.get_locations_by_accessibility(layout.id, limit=5)

# Tối ưu route lấy hàng
picking_lines_optimized = service.optimize_picking_route_simple(picking_lines)

# Xem heatmap capacity
heatmap = service.get_heatmap_data(layout.id)
for item in heatmap:
    print(f"{item['location_name']}: {item['capacity_percentage']}% ({item['color']})")
```

## 🎯 KPI/Metrics

Có thể theo dõi:
- **Accessibility Distribution**: % vị trí ở từng level Z
- **Capacity Utilization**: % dung lượng sử dụng
- **Picking Time**: Thời gian lấy hàng dự kiến (khi có route)
- **Distance Traveled**: Tổng khoảng cách lấy hàng

## 📋 Cấu Trúc File

```
hdi_wms/
├── models/
│   ├── warehouse_layout.py       ← Model sơ đồ kho
│   ├── warehouse_3d_service.py   ← Service tính toán 3D
│   ├── stock_location.py         ← Mở rộng stock.location
│   └── __init__.py               ← Đăng ký imports
├── views/
│   ├── warehouse_layout_views.xml ← Form/List/Kanban
│   ├── stock_location_views.xml   ← Extend location
│   └── wms_menus.xml             ← Menu items
├── data/
│   └── warehouse_3d_demo.xml     ← Sample data
└── __manifest__.py               ← Cập nhật manifest
```

## ✅ Checklist Implementation

- ✅ Model `warehouse.layout`
- ✅ Mở rộng `stock.location` với 3D fields
- ✅ Service `warehouse_3d_service` (4 phương thức)
- ✅ View form/list/kanban warehouse layout
- ✅ Extend location views
- ✅ Menu item
- ✅ Demo data
- ✅ Security groups

## ⚠️ Notes

- Service hiện chỉ tính toán, UI visualization sẽ thêm sau
- Nút "Xem Sơ Đồ 3D" chỉ show notification (ready for integration)
- Demo data tạo 10 locations + 2 doors
- Accessibility score auto-compute dựa trên Z + capacity%

## 🔗 Liên Kết Với Putaway Suggestion

Khi cải tiến, có thể tích hợp service vào:
- `HdiPutawaySuggestion`: Score thêm yếu tố distance & accessibility
- `HdiPickingList`: Optimize route tự động

---

**Version:** 1.0 MVP  
**Status:** Ready for Phase 2 Visualization
