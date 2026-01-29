# Warehouse Layout Editor - Hướng Dẫn Sử Dụng

## 🎯 Tính Năng Chính

Module **Stock 3D Custom View** mở rộng cung cấp công cụ **Warehouse Layout Editor** cho phép bạn:
1. **Thiết kế layout kho 2D** - Vẽ shelves, bins trên canvas
2. **Xem trước 3D** - Tự động render warehouse 3D từ dữ liệu 2D
3. **Quản lý inventory** - Xem tồn kho theo vị trí
4. **Real-time sync** - 2D changes tự động cập nhật 3D

---

## 🚀 Cách Sử Dụng

### **Bước 1: Mở Layout Editor**

```
Warehouses → Chọn warehouse → [Layout Editor (2D/3D)] button
```

Giao diện sẽ hiển thị **3 cột**:
- **Left**: 2D Canvas Editor
- **Center**: 3D Viewer
- **Right**: Inventory Items

### **Bước 2: Thiết Kế Layout 2D (Left Panel)**

#### **Draw Shelves**
1. Click **[+]** (Draw Shelf button)
2. Click và drag trên canvas để vẽ shelf
3. Hệ thống tự động tạo `stock.location` record

#### **Draw Bins**
1. Click **[#]** (Draw Bin button)
2. Click và drag để vẽ bin (nhỏ hơn shelf)

#### **Drag-Drop để Điều Chỉnh Vị Trí**
1. Click chọn một shelf/bin
2. Nó sẽ highlight (border màu đỏ)
3. Drag để di chuyển vị trí
4. **Auto-save** khi thả chuột

#### **Chỉnh Sửa Properties**
1. Click vào shelf/bin để chọn
2. Modal sẽ hiện lên:
   - Location Code (mã duy nhất)
   - Position X, Y, Z (pixel/3D coords)
   - Length, Width, Height (kích thước)
   - Max Capacity (dung tích)
3. Cập nhật → Click **Save Changes**

#### **Xóa Location**
1. Chọn location
2. Click **[🗑️]** (Delete button)
3. Confirm → Xóa khỏi kho

### **Bước 3: Xem Trước 3D (Center Panel)**

- **Tự động render** từ dữ liệu 2D
- **Rotate**: Click + drag chuột
- **Zoom**: Scroll wheel
- **Pan**: Right-click + drag
- **Reset View**: Click **[🔄]** button
- **Fit View**: Click **[⛶]** button
- **Toggle 2D/3D**: Click **[2D/3D]** button trên top

#### **Cách Hoạt Động**
```
Bạn vẽ/edit 2D → Database save → 3D auto refresh
```

### **Bước 4: Quản Lý Inventory (Right Panel)**

#### **Xem Sản Phẩm**
- Danh sách tất cả products trong warehouse
- Hiển thị: Hình ảnh, SKU, Tồn kho, Reserved quantity
- **Tồn kho** = số lượng sẵn
- **Reserved** = số lượng đã được order

#### **Search Sản Phẩm**
- Nhập tên product hoặc SKU
- **Real-time filter**

#### **Xem Chi Tiết**
1. Click **[👁️]** button trên product card
2. Modal hiển thị:
   - Tên, SKU, hình ảnh
   - Total stock, Reserved, Available
   - **Vị trí**: Locations nào có sản phẩm này?

---

## 💾 Lưu Lại

### **Auto-Save**
- ✅ Khi drag-drop location → **Auto save**
- ✅ Khi edit properties → **Save Changes** button

### **Manual Save**
- Click **[💾] Save Layout** button
- Lưu tất cả changes cùng lúc
- Notification: "Layout saved successfully"

---

## 📊 Luồng Dữ Liệu

```
2D Canvas                Database                 3D Viewer
┌─────────┐             ┌──────────┐            ┌───────┐
│ Draw    │──auto save──│ Warehouse│──auto load─│Three. │
│ Shelves │             │Locations │            │ js    │
│ & Bins  │──drag/drop──│          │            │       │
└─────────┘             └──────────┘            └───────┘
   (left)                (backend)               (center)
```

### **Dữ Liệu Lưu**
Mỗi location lưu:
- `pos_x`, `pos_y`, `pos_z` - Vị trí
- `length`, `width`, `height` - Kích thước  
- `unique_code` - Mã duy nhất
- `max_capacity` - Dung tích tối đa
- `warehouse_id` - Kho chứa

---

## ⚙️ Features Chi Tiết

### **2D Canvas**
| Tính Năng | Mô Tả |
|-----------|-------|
| **Grid** | Lưới 20px để căn chỉnh |
| **Draw** | Vẽ rectangles (shelves/bins) |
| **Drag** | Di chuyển bằng chuột |
| **Delete** | Xóa selected items |
| **Clear** | Xóa tất cả (confirm required) |

### **3D Viewer**
| Tính Năng | Mô Tả |
|-----------|-------|
| **Rotate** | Click + drag |
| **Zoom** | Scroll wheel |
| **Pan** | Right-click + drag |
| **Grid** | Helper grid 20x20 |
| **Lighting** | Ambient + Directional |
| **Auto-render** | Real-time từ 2D changes |

### **Inventory Panel**
| Tính Năng | Mô Tả |
|-----------|-------|
| **List** | Tất cả products |
| **Search** | Filter by name/SKU |
| **Cards** | Image, SKU, quantities |
| **Details** | Modal with location breakdown |

---

## 🎮 Keyboard Shortcuts (Future)

| Phím | Chức Năng |
|------|----------|
| `Ctrl+S` | Save Layout |
| `Delete` | Delete selected |
| `Ctrl+Z` | Undo (coming soon) |
| `Ctrl+Y` | Redo (coming soon) |

---

## ⚠️ Lưu Ý Quan Trọng

### **Backward Compatibility**
- ✅ Location form **vẫn hoạt động** bình thường
- ✅ 3D Preview button **vẫn có**
- ✅ Không ảnh hưởng workflow cũ

### **Permission Required**
- Yêu cầu quyền **Administrator (Inventory/Stock)**
- Có thể mở rộng sau

### **Data Validation**
- `unique_code` phải **duy nhất**
- Positions phải **≥ 0**
- Sizes phải **> 0**

---

## 📝 Ví Dụ Thực Tế

### **Scenario: Thiết Kế Kho Quần Áo**

1. **Mở Layout Editor** cho warehouse "Austin Warehouse"

2. **Vẽ shelves (2D)**:
   - Shelf A: 5m × 3m, pos (0, 0)
   - Shelf B: 5m × 3m, pos (6, 0)
   - Shelf C: 5m × 3m, pos (12, 0)

3. **Vẽ bins trong mỗi shelf**:
   - Shelf A → Bin A1, A2, A3, A4, A5
   - Mỗi bin 1m × 1m

4. **Xem 3D preview** - toàn bộ kho hiển thị 3D

5. **Check inventory** - Xem sản phẩm nào ở đâu
   - "VARSITY TEE (BLACK)" → Medium → Bin A1

6. **Save layout** - Lưu config

7. **Tiếp tục picking/packing** dựa vào layout

---

## 🐛 Troubleshooting

| Vấn đề | Giải Pháp |
|--------|----------|
| **3D không render** | Kiểm tra Three.js CDN, reload page |
| **Drag không work** | Canvas phải focus, không có conflicting events |
| **Data không save** | Check network, lỗi database |
| **Inventory list trống** | Warehouse chưa có stock quants |

---

## 📈 Future Enhancements

- [ ] Undo/Redo functionality
- [ ] Drag bins từ 2D → 3D
- [ ] Heat map dung tích sử dụng
- [ ] Export/import layout
- [ ] Mobile-friendly canvas
- [ ] Rotation 3D objects
- [ ] Multi-level (floors) support

---

## 📞 Support

Có câu hỏi? Xem [Stock 3D Custom View README](../README.rst)
