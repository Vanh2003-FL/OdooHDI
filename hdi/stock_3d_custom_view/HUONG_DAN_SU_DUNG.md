# Hướng dẫn sử dụng Kho 3D - Stock 3D Custom View

## 🎯 Tổng quan

Module **Stock 3D Custom View** hiện đã được nâng cấp lên **Odoo 18** và tích hợp hoàn toàn với **warehouse_map** module để hiển thị sản phẩm/lot trong kho dưới dạng 3D.

### ✨ Tính năng chính

- 📦 Hiển thị sản phẩm/lot theo vị trí thực tế trong kho 3D
- 🎨 Mã màu theo số lượng tồn kho (Xanh/Vàng/Đỏ)
- 🖱️ Tương tác: xoay, zoom, click xem chi tiết
- 📊 Sidebar hiển thị danh sách sản phẩm
- 🏢 Hỗ trợ nhiều warehouse
- 🔄 Tự động đồng bộ với warehouse_map

---

## 🚀 Cài đặt

### Bước 1: Cài đặt module

```bash
# Update module trong Odoo
odoo-bin -u stock_3d_custom_view -d your_database
```

**Yêu cầu**: Module `warehouse_map` phải được cài đặt trước.

### Bước 2: Kiểm tra

Vào **Inventory > Warehouse > Warehouse 3D View**

Nếu thấy menu này → Cài đặt thành công! ✅

---

## 📝 Workflow sử dụng

### 1️⃣ Gán vị trí cho sản phẩm (Qua warehouse_map)

Theo workflow hiện tại của bạn:

1. **Tạo phiếu nhập kho**
   - Inventory > Operations > Receipts
   - Tạo mới hoặc chọn phiếu có sẵn

2. **Thêm sản phẩm có tracking**
   - Sản phẩm phải có Lot/Serial tracking
   - Nhập lot name

3. **Gán vị trí từ wizard**
   - Click nút **"📍 Gán vị trí"** trên dòng sản phẩm
   - Chọn warehouse map
   - Nhập hoặc chọn vị trí X, Y, Z
   - Xác nhận

4. **Validate phiếu**
   - Click **"Validate"**
   - Hệ thống tự động tạo quant với vị trí (posx, posy, posz)

### 2️⃣ Xem trong 3D View

#### Cách 1: Từ Menu (Khuyến nghị)
```
Inventory > Warehouse > Warehouse 3D View
```

#### Cách 2: Từ Location Form
1. Vào **Inventory > Configuration > Locations**
2. Mở location (VD: WH/Stock)
3. Click nút **"View Warehouse 3D Map"**

### 3️⃣ Tương tác với 3D View

| Thao tác | Cách thực hiện |
|----------|---------------|
| **Xoay camera** | Kéo chuột trái |
| **Di chuyển** | Kéo chuột phải hoặc Shift + kéo trái |
| **Zoom** | Scroll chuột |
| **Xem chi tiết** | Click vào hộp sản phẩm (product box) |
| **Đổi warehouse** | Chọn từ dropdown ở góc trên |

---

## 🎨 Ý nghĩa màu sắc

### Product Boxes (Hộp sản phẩm)

| Màu | Ý nghĩa | Số lượng |
|-----|---------|----------|
| 🟢 Xanh lá | Tồn kho cao | > 100 units |
| 🟡 Vàng | Tồn kho trung bình | 50-100 units |
| 🔴 Đỏ | Tồn kho thấp | 0-50 units |
| ⚪ Xám | Trống/không có hàng | 0 units |

### Location Boxes (Kệ/Giá - Tùy chọn)

- **Xám mờ**: Cấu trúc kho (nếu đã cấu hình)

---

## ⚙️ Cấu hình nâng cao (Tùy chọn)

### Hiển thị cấu trúc kho (Location Boxes)

Nếu muốn hiển thị kệ/giá đỡ trong 3D:

1. Vào **Inventory > Configuration > Locations**
2. Chọn location (VD: Shelf-A)
3. Tab **"3D Visualization Properties"**:

#### Thông số cần nhập:

**3D Box Dimensions**:
- `3D Length (M)`: Chiều dài (meters) - VD: 2.0
- `3D Width (M)`: Chiều rộng (meters) - VD: 1.5
- `3D Height (M)`: Chiều cao (meters) - VD: 2.5

**3D Box Position**:
- `3D X Position (px)`: Vị trí X trong scene - VD: 100
- `3D Y Position (px)`: Vị trí Y trong scene - VD: 0
- `3D Z Position (px)`: Vị trí Z trong scene - VD: 50

**Other Properties**:
- `3D Location Code`: Mã duy nhất - VD: "SHELF-A-01"
- `3D Capacity (Units)`: Sức chứa - VD: 500

**Lưu ý**: Đây chỉ là cấu trúc nền, sản phẩm vẫn lấy vị trí từ `warehouse_map`.

---

## 🔧 Khắc phục sự cố

### ❌ Không thấy sản phẩm trong 3D?

**Nguyên nhân & giải pháp**:

1. **Sản phẩm không có tracking**
   - ✅ Vào product form > Inventory tab
   - Set **Tracking** = "By Unique Serial Number" hoặc "By Lots"

2. **Chưa gán vị trí**
   - ✅ Gán vị trí qua wizard khi nhập kho
   - ✅ Hoặc sửa trực tiếp trên quant: Inventory > Reporting > Inventory

3. **Quant không được hiển thị**
   - ✅ Kiểm tra field `display_on_map` = True
   - ✅ Vào Inventory, tìm quant, check box "Display on map"

4. **Vị trí = [0, 0, 0]**
   - ✅ Đây là vị trí mặc định, không hiển thị trong 3D
   - ✅ Gán lại vị trí khác [0, 0]

### ❌ Không thấy menu "Warehouse 3D View"?

**Giải pháp**:

1. Kiểm tra module đã cài:
```bash
# Vào Settings > Apps > search "stock_3d_custom_view"
# Phải có trạng thái "Installed"
```

2. Clear cache browser (Ctrl + Shift + R)

3. Restart Odoo server:
```bash
sudo systemctl restart odoo
```

### ❌ Lỗi "warehouse_map module not found"?

**Giải pháp**:
```bash
# Cài warehouse_map trước
odoo-bin -i warehouse_map -d your_database

# Sau đó update stock_3d_custom_view
odoo-bin -u stock_3d_custom_view -d your_database
```

### ❌ 3D View bị lag/chậm?

**Nguyên nhân**: Quá nhiều products hiển thị (> 1000)

**Giải pháp**:
- Chọn warehouse nhỏ hơn
- Lọc products theo location cụ thể
- Nâng cấp phần cứng (GPU)

---

## 💡 Tips & Tricks

### 1. Sử dụng với Tablet/Mobile
- Dùng 2 ngón để zoom
- Vuốt để xoay
- Tap vào product để xem chi tiết

### 2. Tối ưu hiệu suất
- Chỉ hiển thị products có `quantity > 0`
- Tắt location boxes nếu không cần (không nhập `loc_3d_code`)

### 3. Export dữ liệu
- Sidebar có danh sách đầy đủ products
- Có thể copy/export từ đây

### 4. Integration với báo cáo
- 3D view có thể embed vào dashboard
- Dùng client action `open_warehouse_3d_view`

---

## 📞 Hỗ trợ

**Liên hệ**:
- Email: quochuy.software@gmail.com
- Module: stock_3d_custom_view v18.0.1.0.0

**Tài liệu kỹ thuật**: Xem file `UPGRADE_NOTES.md`

---

## 📚 Tham khảo

- [Odoo 18 Documentation](https://www.odoo.com/documentation/18.0/)
- [Three.js Documentation](https://threejs.org/docs/)
- [Warehouse Map Module](../warehouse_map/USAGE_GUIDE.md)

---

**Chúc bạn sử dụng hiệu quả! 🎉**
