# Stock 3D Custom View - Odoo 18 Upgrade

## Tổng quan

Module **Stock 3D Custom View** đã được nâng cấp lên **Odoo 18** và tích hợp với module **warehouse_map** để hiển thị vị trí thực tế của sản phẩm/lot trong kho 3D.

### Version: 18.0.1.0.0

## Các thay đổi chính

### 1. **Tích hợp với warehouse_map**

Module hiện sử dụng dữ liệu vị trí từ `warehouse_map` module:
- Vị trí sản phẩm/lot lấy từ `stock.quant` (fields: `posx`, `posy`, `posz`)
- Hiển thị sản phẩm trong 3D theo vị trí thực tế đã gán từ wizard picking
- Không còn xung đột fields giữa 2 modules

### 2. **Đổi tên fields để tránh xung đột**

Module này dùng các fields riêng cho **location boxes** (kệ/giá đỡ):

| Field cũ | Field mới | Mục đích |
|----------|-----------|----------|
| `pos_x` | `loc_pos_x` | Vị trí X của location box trong 3D |
| `pos_y` | `loc_pos_y` | Vị trí Y của location box trong 3D |
| `pos_z` | `loc_pos_z` | Vị trí Z của location box trong 3D |
| `length` | `loc_length` | Chiều dài location box |
| `width` | `loc_width` | Chiều rộng location box |
| `height` | `loc_height` | Chiều cao location box |
| `unique_code` | `loc_3d_code` | Mã định danh location |
| `max_capacity` | `loc_max_capacity` | Sức chứa tối đa |

**Lưu ý**: Fields `posx`, `posy`, `posz` trên `stock.quant` từ `warehouse_map` module dùng cho **vị trí sản phẩm/lot**.

### 3. **Kiến trúc 2 lớp**

#### Layer 1: Location Boxes (Background)
- Hiển thị cấu trúc kho (kệ, giá đỡ) bằng boxes 3D bán trong suốt
- Lấy từ `stock.location` với fields `loc_pos_x/y/z`, `loc_length/width/height`
- Tùy chọn - không bắt buộc

#### Layer 2: Product Positions (Foreground)
- Hiển thị sản phẩm/lot thực tế với vị trí từ `warehouse_map`
- Lấy từ `stock.quant` với fields `posx`, `posy`, `posz`
- Màu sắc theo số lượng: Xanh (>100), Vàng (50-100), Đỏ (<50)
- Click vào product box để xem chi tiết

### 4. **API Controllers mới**

#### `/3Dstock/data/products` (NEW)
Lấy danh sách products/lots với vị trí 3D từ `warehouse_map`:
```json
[
  {
    "id": 123,
    "product_name": "Product A",
    "lot_name": "LOT001",
    "quantity": 75,
    "pos_x": 150,
    "pos_y": 60,
    "pos_z": 90,
    "location_name": "WH/Stock/Shelf-A",
    "color": 0xe6b800
  }
]
```

#### `/3Dstock/data` (UPDATED)
Lấy location boxes (legacy + updated fields):
- Sử dụng fields mới: `loc_pos_x/y/z`, `loc_length/width/height`
- Lọc locations có `loc_3d_code` không rỗng

## Cách sử dụng

### 1. Cài đặt

```bash
# Cập nhật module
odoo-bin -u stock_3d_custom_view -d your_database
```

**Dependencies**: 
- `stock`
- `web`
- `warehouse_map` (bắt buộc)

### 2. Cấu hình Location Boxes (Tùy chọn)

Nếu muốn hiển thị cấu trúc kho (kệ/giá):

1. Vào **Inventory > Configuration > Locations**
2. Chọn location (VD: WH/Stock/Shelf-A)
3. Tab **"3D Visualization Properties"**:
   - **3D Box Dimensions**: Nhập `loc_length`, `loc_width`, `loc_height`
   - **3D Box Position**: Nhập `loc_pos_x`, `loc_pos_y`, `loc_pos_z`
   - **3D Location Code**: Mã duy nhất (VD: "SHELF-A-01")
   - **Capacity**: Sức chứa (dùng cho color coding)

### 3. Gán vị trí sản phẩm (warehouse_map workflow)

Theo workflow hiện tại của bạn:

1. Tạo phiếu nhập kho (Receipt)
2. Thêm sản phẩm có tracking (lot/serial)
3. Click **"📍 Gán vị trí"** trên move line
4. Chọn vị trí từ sơ đồ 2D hoặc nhập tọa độ X, Y, Z
5. Validate picking → Hệ thống tự động tạo quant với `posx`, `posy`, `posz`

### 4. Xem 3D View

#### Cách 1: Menu
**Inventory > Warehouse > Warehouse 3D View**

#### Cách 2: Từ Location
1. Vào location form
2. Click **"View Warehouse 3D Map"**

#### Cách 3: Từ Warehouse Map
- Module `warehouse_map` có thể thêm nút link đến 3D view

### 5. Tương tác trong 3D View

- **Xoay**: Kéo chuột trái
- **Pan**: Kéo chuột phải hoặc Shift + kéo trái
- **Zoom**: Scroll chuột
- **Click product box**: Xem thông tin chi tiết
- **Sidebar**: Danh sách tất cả products
- **Dropdown**: Chuyển đổi giữa các warehouses

## Color Coding

### Location Boxes (kệ/giá)
- Xám mờ (opacity 0.3): Cấu trúc kho

### Product Boxes
- 🟢 **Xanh lá** (#00802b): Số lượng > 100
- 🟡 **Vàng** (#e6b800): Số lượng 50-100
- 🔴 **Đỏ** (#cc0000): Số lượng < 50
- ⚪ **Xám** (#8c8c8c): Không có hàng

## Migration từ version cũ

### Data Migration

Nếu bạn đã sử dụng version cũ với fields `pos_x`, `length`, v.v.:

```python
# Script migration (chạy trong Odoo shell)
locations = env['stock.location'].search([
    ('pos_x', '!=', False)
])

for loc in locations:
    loc.write({
        'loc_pos_x': loc.pos_x,
        'loc_pos_y': loc.pos_y,
        'loc_pos_z': loc.pos_z,
        'loc_length': loc.length,
        'loc_width': loc.width,
        'loc_height': loc.height,
        'loc_3d_code': loc.unique_code,
        'loc_max_capacity': loc.max_capacity,
    })
```

**Lưu ý**: Fields cũ có thể bị conflict nếu module khác cũng định nghĩa. Nên xóa fields cũ sau khi migrate.

## Odoo 18 Compatibility

### JavaScript (OWL Framework)
- ✅ Sử dụng OWL Components
- ✅ Service-based architecture (`useService`)
- ✅ Modern state management (`useState`)
- ✅ Proper lifecycle hooks (`onMounted`, `onWillUnmount`)

### Python
- ✅ Compatible với Odoo 18 ORM
- ✅ Updated HTTP routes
- ✅ Modern field definitions

### XML
- ✅ Updated view syntax
- ✅ Modern domain expressions
- ✅ Client action tags

## Troubleshooting

### Không thấy products trong 3D view?

**Kiểm tra**:
1. Sản phẩm có tracking (lot/serial) không?
2. Quant có `display_on_map = True` không?
3. Quant có `posx`, `posy` khác 0 không?
4. Location là con của warehouse đã chọn không?

### Location boxes không hiển thị?

**Kiểm tra**:
1. Location có `loc_3d_code` không rỗng không?
2. Có nhập `loc_length`, `loc_width`, `loc_height` không?
3. Location có `usage = 'internal'` không?

### Lỗi "warehouse_map not found"?

**Giải pháp**:
```bash
# Cài đặt warehouse_map trước
odoo-bin -i warehouse_map -d your_database

# Sau đó cài stock_3d_custom_view
odoo-bin -i stock_3d_custom_view -d your_database
```

## Technical Details

### Stack
- **Frontend**: OWL Components + Three.js r128
- **Backend**: Python 3.10+ / Odoo 18
- **3D Library**: Three.js + OrbitControls

### Performance
- Tối ưu với < 1000 products
- Lazy loading cho sidebar
- Efficient raycasting cho click events

### Browser Support
- Chrome/Edge: ✅ Full support
- Firefox: ✅ Full support
- Safari: ⚠️ Partial (WebGL required)

## Credits

- **Original Module**: Cybrosys Technologies
- **Odoo 18 Upgrade**: Wokwy (quochuy.software@gmail.com)
- **Integration**: warehouse_map module
- **Support**: Claude.ai

## License

LGPL-3

## Support

For issues or questions:
- Email: quochuy.software@gmail.com
- GitHub: Create issue in repository
