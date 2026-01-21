# Warehouse Layout Grid - Hướng Dẫn Sử Dụng

## 📋 Tổng Quan

Phần **Warehouse Layout Grid** cung cấp trực quan hóa sơ đồ kho theo lưới (grid) 3D, cho phép:
- Hiển thị sơ đồ kho dạng grid 3D (hàng × cột × tầng)
- Quản lý vị trí hàng trong kho một cách trực quan
- Thực hiện các tác vụ (lấy hàng, chuyển vị trí, chuyển kho) bằng click chuột
- Theo dõi thống kê sử dụng kho realtime

---

## 🚀 Bắt Đầu

### 1. Tạo Sơ Đồ Kho

**Menu:** Quản lý Kho → Sơ đồ Kho → Sơ đồ Kho

#### Bước 1: Tạo Layout mới
```
Kho: Chọn kho muốn tạo sơ đồ
Tên sơ đồ: Ví dụ "Main Warehouse Layout"
Số hàng: 5 (Y-axis)
Số cột: 10 (X-axis)
Số tầng: 3 (Z-axis - kế chứa hàng)
```

#### Bước 2: Cấu hình kích thước ô
```
Chiều rộng ô: 100 px (mặc định)
Chiều cao ô: 80 px (mặc định)
```

#### Bước 3: Tạo Grid tự động
- Nhấp nút **"Generate Grid"**
- Hệ thống sẽ tạo tự động tất cả vị trí (5 × 10 × 3 = 150 slots)

---

## 🎯 Các Tính Năng Chính

### A. Hiển Thị Sơ Đồ Kho

#### Mở sơ đồ kho:
```
Menu → Quản lý Kho → Sơ đồ Kho
→ Chọn sơ đồ → Nút "View Layout"
```

#### Cấu trúc hiển thị:
- **3 tầng** (Level 1, 2, 3)
- Mỗi tầng có **lưới 5 hàng × 10 cột**
- **Mã vị trí**: L{Tầng}-R{Hàng}-C{Cột}
  - Ví dụ: L1-R2-C3 = Tầng 1, Hàng 2, Cột 3

#### Chỉ báo màu sắc:
```
🟩 Xám (Empty)      - Vị trí trống
🟧 Cam (Partial)    - Chứa hàng một phần
🟥 Đỏ (Full)        - Kệ/Pallet đầy
🟦 Xanh (Reserved)  - Dành riêng cho SP nào đó
⬛ Đen (Blocked)    - Vị trí bị chặn
```

---

### B. Đặt Hàng Vào Vị Trí (Putaway)

Khi nhập hàng (Incoming), hệ thống sẽ gợi ý vị trí:

#### Cách 1: Click vào ô trống
```
1. Mở sơ đồ kho
2. Click vào ô có màu xám (Empty)
3. Chọn "Place Batch"
4. Chọn lô hàng cần đặt
5. Hệ thống kiểm tra dung tích
6. Nhấp "Place Batch"
```

#### Cách 2: Từ Putaway Wizard
```
Nhập kho → Tạo Batch → Nút "Suggest Putaway"
→ Chọn vị trí từ gợi ý
```

#### Kiểm tra dung tích:
- Hệ thống kiểm tra **weight, volume, quantity**
- Chỉ cho phép đặt nếu không vượt quá giới hạn

---

### C. Click Vào Lô Hàng (Batch Cell) - 5 Tác Vụ

#### Menu Context (Right-click hoặc Left-click):

**🔸 1. Lấy Hàng (Pick Batch)**
```
- Mục đích: Tạo phiếu xuất kho
- Hành động: Tạo stock.picking loại Outgoing
- Sẽ mở form picking để lấy hàng
```

**🔸 2. Chuyển Vị Trí (Move Batch)**
```
- Mục đích: Di chuyển batch trong cùng kho
- Hành động: Mở wizard chọn vị trí đích
- Ghi nhận lý do chuyển:
  • Capacity optimization (tối ưu dung tích)
  • Consolidation (gộp hàng)
  • Zone change (chuyển vùng)
  • Damage relocation (chuyển vì hư hỏng)
  • Picking optimization (tối ưu lấy hàng)
  • Other (khác)
```

**🔸 3. Chuyển Kho (Transfer Warehouse)**
```
- Mục đích: Di chuyển batch sang kho khác
- Hành động: Tạo Internal Transfer
- Nhập lý do:
  • Stock balancing (cân bằng tồn kho)
  • Fulfillment (thực hiện đơn)
  • Return to supplier (trả lại NCC)
  • Consolidation (gộp hàng)
  • Other (khác)
- Sẽ tạo stock.picking loại Internal Transfer
```

**🔸 4. Xem Chi Tiết Lô (View Batch Details)**
```
- Mục đích: Xem thông tin chi tiết batch
- Hiển thị:
  • Batch name, barcode, type
  • Sản phẩm, số lượng, trọng lượng
  • Vị trí hiện tại
  • Lịch sử hoạt động
  • Quants liên kết
```

**🔸 5. Chi Tiết Vị Trí (Location Details)**
```
- Mục đích: Xem/chỉnh sửa thông tin vị trí
- Chỉnh sửa được:
  • Dung tích (max weight, volume, items)
  • Loại dung tích (weight, volume, count, unlimited)
  • Dành riêng cho sản phẩm nào (if reserved)
  • Ghi chú vị trí
  • Thông tin lịch sử
```

---

## 📊 Quản Lý Vị Trí (Location Grid)

### Truy cập:
```
Menu → Quản lý Kho → Sơ đồ Kho → Vị trí Lưới
```

### Danh sách vị trí:
- Hiển thị tất cả **150 slots** (5×10×3)
- Sắp xếp theo: Tầng → Hàng → Cột
- Lọc theo: Trạng thái, Khu vực, Loại dung tích

### Thông tin mỗi vị trí:
| Thông tin | Mô tả |
|-----------|-------|
| Position Code | L1-R2-C3 |
| Row / Column / Level | Vị trí trong lưới |
| Batch ID | Lô hàng hiện tại |
| Status | Empty/Partial/Full/Reserved/Blocked |
| Utilization % | % sử dụng dung tích |
| Available | Có sẵn để đặt hàng mới? |
| Zone | Khu vực (Zone A, B, C) |
| Capacity Type | Loại giới hạn |
| Max Weight/Volume/Count | Giới hạn dung tích |
| Current Weight/Volume/Items | Tình trạng hiện tại |
| Reserved Products | Sản phẩm dành riêng |
| Last Batch | Batch trước đó |
| Last Change Date | Thời gian thay đổi |

---

## 🎨 Khu Vực (Zones)

### Tạo khu vực trong sơ đồ:

```
Tab "Zones" trong form sơ đồ kho
→ Thêm dòng mới
```

### Thông tin khu vực:
```
Tên: Zone A, Zone B, Zone C, ...
Loại: General, Reserved, Hazmat, Cold, Quarantine
Màu: Mã hex (#3498db)
Boundaries: Hàng bắt đầu/kết thúc, Cột bắt đầu/kết thúc
```

### Ví dụ:
```
Zone A (Tầng 1, Hàng 1-2, Cột 1-5) - Hàng nóng
Zone B (Tầng 1, Hàng 1-2, Cột 6-10) - Hàng lạnh
Zone C (Tầng 2-3, Tất cả) - Hàng dự trữ
```

---

## 📈 Thống Kê & Giám Sát

### Dashboard sơ đồ kho:

```
Hiển thị realtime:
- Total Slots: 150
- Occupied: 45 (30%)
- Empty: 105 (70%)
- Utilization Rate: 30%
```

### Thống kê chi tiết:
```
Mở form sơ đồ → Tab "Grid Map"
Xem visual grid + statistics
```

---

## ⚙️ Cấu Hình Dung Tích

### Loại giới hạn:
```
1. Weight-based: Giới hạn trọng lượng (kg)
   VD: Max 500kg/slot
   
2. Volume-based: Giới hạn thể tích (m³)
   VD: Max 1.5m³/slot
   
3. Count-based: Giới hạn số lượng
   VD: Max 100 items/slot
   
4. Unlimited: Không giới hạn
```

### Cấu hình vị trí dành riêng:

```
Mở vị trí → "Reserved Products"
Chọn: Dành riêng? = True
Chọn sản phẩm: Chỉ những SP này mới được phép
```

---

## 🔄 Luồng Hoàn Chỉnh

### Khi nhập hàng (Incoming):
```
1. Tạo Phiếu Nhập
2. Tạo Batch (Lô hàng)
3. Hệ thống gợi ý vị trí từ sơ đồ kho
4. Chọn vị trí và đặt batch
5. Batch chuyển sang trạng thái "in_receiving"
6. QC và xác nhận
7. Batch chuyển sang "stored" (đã vào vị trí)
```

### Khi lấy hàng (Outgoing):
```
1. Tạo Phiếu Xuất
2. Click vào batch trong sơ đồ kho
3. Chọn "Pick Batch"
4. Tạo phiếu lấy hàng tự động
5. Lấy hàng và xác nhận
6. Batch chuyển sang "in_picking" → "shipped"
```

### Khi chuyển vị trí:
```
1. Mở sơ đồ kho
2. Click batch cần chuyển
3. Chọn "Move Batch"
4. Chọn vị trí đích
5. Ghi lý do chuyển
6. Xác nhận → Batch di chuyển ngay lập tức
```

---

## 🔐 Quyền Hạn

```
Group: WMS User (Người dùng kho)
- Xem sơ đồ: ✓
- Đặt hàng: ✓
- Di chuyển: ✓
- Lấy hàng: ✓

Group: WMS Manager (Quản lý kho)
- Tất cả quyền WMS User + 
- Chỉnh sửa cấu hình: ✓
- Tạo/xóa vị trí: ✓
- Tạo/xóa khu vực: ✓
```

---

## 📝 Lưu Ý

1. **Grid 3D**: Mỗi tầng hiển thị riêng biệt, dễ dàng phân biệt
2. **Scroll**: Nếu grid lớn, có scrollbar để cuộn
3. **Responsive**: Tự điều chỉnh trên màn hình nhỏ
4. **Context Menu**: Click chuột phải hoặc click trái trên batch để hiển thị menu
5. **Lịch sử**: Mỗi lần di chuyển batch đều được ghi lại với lý do

---

## 🆘 Troubleshooting

| Vấn đề | Giải pháp |
|--------|----------|
| Grid không hiển thị | Check dung tích khoảng trống, regenerate grid |
| Không thể đặt batch | Check dung tích có phù hợp không |
| Batch không hiển thị | Check batch có được link đúng grid không |
| Menu không hiện | Refresh page, check browser console |

---

## 📞 Hỗ Trợ

Liên hệ: support@hdi.vn
