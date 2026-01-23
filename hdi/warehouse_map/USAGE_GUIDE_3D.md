# Hướng dẫn sử dụng Sơ đồ Kho 3D

## Tổng quan

Module Warehouse Map 3D mở rộng chức năng sơ đồ kho 2D, cho phép quản lý vị trí hàng hóa trong không gian 3 chiều với tọa độ X, Y, Z.

## Tính năng chính

### 1. Quản lý Sơ đồ Kho 3D
- Tạo và cấu hình sơ đồ kho với 3 chiều: X (cột), Y (hàng), Z (tầng)
- Cấu hình kích thước thực tế (mét) cho mỗi ô
- Phân vùng không gian với spacing intervals
- Hiển thị sơ đồ 3D tương tác với Three.js

### 2. Nhập Tọa Độ 3D cho Lot/Serial
- Gán tọa độ (X, Y, Z) cho từng lot/serial number
- Kiểm tra tự động vị trí trống/bị chặn
- Cảnh báo khi vị trí đã có hàng
- Hiển thị/ẩn lot trên sơ đồ

### 3. Hiển Thị 3D
- Render 3D với Three.js
- Màu sắc theo mức độ sẵn có:
  - **Xanh lá**: > 70% khả dụng
  - **Vàng**: 30-70% khả dụng
  - **Đỏ**: < 30% khả dụng
  - **Xám**: Ô bị chặn
  - **Lưới**: Ô trống
- Điều khiển camera (xoay, zoom, pan)
- Chọn ô để xem chi tiết
- Lọc theo tầng hoặc hiển thị tất cả

## Cách sử dụng

### Tạo Sơ đồ Kho 3D

1. Vào menu **Kho hàng > Sơ đồ kho > Sơ đồ kho 3D**
2. Nhấn **Tạo mới**
3. Điền thông tin:
   - **Tên sơ đồ**: Đặt tên cho sơ đồ
   - **Kho**: Chọn kho cần tạo sơ đồ
   - **Vị trí kho chính**: Location gốc của kho
   
4. Cấu hình kích thước:
   - **Số cột (X)**: Chiều rộng kho
   - **Số hàng (Y)**: Chiều dài kho
   - **Số tầng (Z)**: Chiều cao/số tầng kệ
   
5. Kích thước thực tế:
   - **Rộng mỗi ô (m)**: Độ rộng của 1 ô tính bằng mét
   - **Sâu mỗi ô (m)**: Độ sâu của 1 ô
   - **Cao mỗi tầng (m)**: Chiều cao mỗi tầng

6. Phân vùng (tùy chọn):
   - Cấu hình khoảng cách sau mỗi X cột/hàng/tầng
   - VD: 5 = có khoảng trống sau mỗi 5 đơn vị

7. Cài đặt hiển thị:
   - Hiển thị lưới
   - Hiển thị trục tọa độ
   - Hiển thị nhãn

8. Nhấn **Lưu**

### Gán Tọa Độ cho Lot/Serial

#### Cách 1: Từ Quant
1. Vào **Kho hàng > Sản phẩm > Lot/Serial Numbers**
2. Chọn lot cần gán tọa độ
3. Vào tab **Stock** để xem các quant
4. Chọn quant và nhấn nút **Gán tọa độ 3D**

#### Cách 2: Từ Wizard
1. Vào menu **Kho hàng > Sơ đồ kho > Gán tọa độ 3D**
2. Chọn:
   - **Sơ đồ 3D**: Sơ đồ cần gán
   - **Sản phẩm**: Sản phẩm cần gán
   - **Lot/Serial**: Lot hoặc Serial number
   - **Vị trí**: Location chứa hàng
   
3. Nhập tọa độ:
   - **Vị trí X (Cột)**: 0 đến n-1
   - **Vị trí Y (Hàng)**: 0 đến n-1
   - **Vị trí Z (Tầng)**: 0 đến n-1
   
4. Chọn **Hiển thị trên sơ đồ**: Bật/tắt hiển thị
5. Nhấn **Gán tọa độ**

### Xem Sơ đồ 3D

1. Từ danh sách sơ đồ kho 3D
2. Nhấn nút **Xem sơ đồ 3D** trên card
3. Sơ đồ 3D sẽ mở ra với:
   - **Điều khiển bên phải**: Làm mới, chọn tầng
   - **Chú thích bên trái**: Giải thích màu sắc
   - **Thông tin ô dưới cùng**: Hiển thị khi chọn ô

### Điều khiển Camera

- **Xoay**: Kéo chuột trái
- **Zoom**: Cuộn chuột
- **Pan**: Kéo chuột phải hoặc Shift + kéo chuột trái
- **Chọn ô**: Click chuột trái vào ô

### Chặn/Bỏ chặn Ô

1. Từ form sơ đồ 3D
2. Nhấn nút **Quản lý ô bị chặn 3D**
3. Danh sách các ô bị chặn sẽ hiển thị
4. Để chặn ô mới:
   - Nhấn **Tạo mới**
   - Chọn sơ đồ và nhập tọa độ (X, Y, Z)
   - Nhập lý do chặn (tùy chọn)
   - Nhấn **Lưu**
5. Để bỏ chặn: Xóa record tương ứng

## Lưu ý

### Tọa độ
- Tọa độ bắt đầu từ **0**
- **X**: Chiều ngang (cột, chiều rộng)
- **Y**: Chiều dọc (hàng, chiều dài)
- **Z**: Chiều cao (tầng)
- Mỗi vị trí (X, Y, Z) chỉ chứa 1 lot/serial

### Hiệu suất
- Với kho lớn (>1000 ô), nên:
  - Sử dụng chế độ xem theo tầng
  - Tắt hiển thị nhãn
  - Giảm số lượng ô hiển thị cùng lúc

### Tracking
- Chỉ hiển thị sản phẩm có **tracking** (lot/serial)
- Sản phẩm không tracking sẽ không xuất hiện trên sơ đồ

### Three.js
- Module sử dụng Three.js cho rendering 3D
- Cần trình duyệt hỗ trợ WebGL
- Khuyến nghị: Chrome, Firefox, Edge phiên bản mới

## Workflow tích hợp 2D & 3D

1. **Nhập hàng**:
   - Tạo phiếu nhập kho
   - Xác nhận nhận hàng
   - Gán tọa độ 3D cho lot/serial qua wizard
   - Kiểm tra vị trí trên sơ đồ 3D

2. **Xuất hàng**:
   - Tìm lot trên sơ đồ 3D
   - Xem thông tin số lượng khả dụng
   - Tạo phiếu xuất với lot đã chọn
   - Hệ thống tự động cập nhật sơ đồ

3. **Kiểm kê**:
   - Sử dụng sơ đồ 3D để định vị hàng hóa
   - Lọc theo tầng để kiểm tra từng tầng
   - Đối chiếu thực tế với hệ thống

## Troubleshooting

### Sơ đồ không hiển thị
- Kiểm tra console browser (F12)
- Đảm bảo đã import Three.js đúng
- Xóa cache trình duyệt

### Tọa độ không gán được
- Kiểm tra ô có bị chặn không
- Kiểm tra quant có tồn tại không
- Kiểm tra tọa độ có vượt quá giới hạn không

### Hiệu suất chậm
- Giảm số tầng hiển thị cùng lúc
- Tắt labels
- Tắt grid/axes nếu không cần
- Giảm kích thước sơ đồ

## Hỗ trợ

- Email: quochuy.software@gmail.com
- Module được phát triển với sự hỗ trợ của Claude.ai
