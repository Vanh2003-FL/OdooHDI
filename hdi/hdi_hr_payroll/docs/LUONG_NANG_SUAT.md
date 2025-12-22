# 📊 HƯỚNG DẪN: LƯƠNG NĂNG SUẤT THEO CÔNG THỰC TẾ

## 🎯 Thay đổi chính

**TRƯỚC ĐÂY:**
- Lương năng suất được cố định trong hợp đồng
- Tính theo công thực tế + công phép

**BÂY GIỜ:**
- Lương năng suất được nhập hàng tháng vào phiếu lương
- **CHỈ** tính theo công thực tế (không tính nghỉ phép)
- Hợp đồng chỉ chứa: Lương cơ bản + Phụ cấp

---

## 📝 CÁCH SỬ DỤNG

### Bước 1: Thiết lập hợp đồng

**Menu:** Employees → Hợp đồng → Tab "Thông tin lương"

```
✅ Lương cơ bản/tháng: 15,000,000
✅ Phụ cấp ăn trưa: 730,000
✅ Phụ cấp xăng xe: 1,000,000
❌ Lương năng suất: (Đã bỏ - không còn trong hợp đồng)
```

### Bước 2: Tạo phiếu lương

**Menu:** Payroll → Phiếu lương → Create

1. **Chọn nhân viên** → Tự động điền hợp đồng
2. **Chọn kỳ lương** (Từ ngày - Đến ngày)
3. **Nhập công chuẩn** (VD: 22.5)

### Bước 3: Nhập Lương Năng Suất

**Tab "Các khoản khác":**

| Tên | Mã | Số tiền |
|-----|-----|---------|
| Lương năng suất | PERFORMANCE | 5,000,000 |

> ⚠️ **Lưu ý:** Nhập số tiền lương năng suất TỔNG trong tháng (chưa tính công). Hệ thống sẽ tự động tính theo công thực tế.

### Bước 4: Nhập ngày công

**Tab "Ngày công":**

| Mô tả | Mã | Số ngày |
|-------|-----|---------|
| Ngày công thực tế | WORK100 | 20 |
| Nghỉ phép hưởng lương | LEAVE | 2 |

### Bước 5: Tính lương

Click **"Tính lương"** → Hệ thống sẽ tự động tính:

**Công thức:**
```python
# Lương cơ bản
Lương CB = (15,000,000 / 22.5) × (20 + 2) = 14,666,667 VNĐ

# Lương năng suất  
Lương NS = (5,000,000 / 22.5) × 20 = 4,444,444 VNĐ
           ↑ Chỉ tính 20 công thực tế (KHÔNG tính 2 công phép)
```

---

## 💡 CÁC TRƯỜNG HỢP THỰC TẾ

### Case 1: Nhân viên đi làm đủ công

```
Công chuẩn: 22.5
Công thực tế: 22
Nghỉ phép: 0.5
Lương NS input: 6,000,000

→ Lương NS nhận được = (6,000,000 / 22.5) × 22 = 5,866,667 VNĐ
```

### Case 2: Nhân viên nghỉ nhiều

```
Công chuẩn: 22.5
Công thực tế: 15
Nghỉ phép: 3
Nghỉ không lương: 4.5
Lương NS input: 5,000,000

→ Lương NS nhận được = (5,000,000 / 22.5) × 15 = 3,333,333 VNĐ
   (Chỉ tính 15 công thực tế)
```

### Case 3: Không nhập lương năng suất

```
→ Khoản "Lương năng suất" sẽ KHÔNG hiển thị trên phiếu lương
```

---

## 🔧 CHI TIẾT KỸ THUẬT

### File đã thay đổi

1. **models/hr_contract.py**
   - ❌ Xóa field `performance_wage`
   - ✅ Chỉ giữ lại `wage` + các phụ cấp

2. **data/hr_salary_rule_data.xml**
   - Rule `PERFORMANCE` đã được sửa:
     ```python
     # Điều kiện: Có nhập input PERFORMANCE
     result = inputs.PERFORMANCE and inputs.PERFORMANCE.amount > 0
     
     # Tính toán: CHỈ theo công thực tế
     result = (inputs.PERFORMANCE.amount / standard_days) × work_days
     ```

3. **views/hr_payslip_views.xml**
   - ✅ Thêm tab "Các khoản khác" để nhập lương năng suất
   - ✅ Hiển thị hướng dẫn rõ ràng

### Cấu trúc dữ liệu

```python
# Model: hr.payslip.input
{
    'name': 'Lương năng suất',
    'code': 'PERFORMANCE',  # ← Quan trọng! Phải đúng mã này
    'amount': 5000000,      # Tổng lương NS trong tháng
}
```

---

## ❓ CÂU HỎI THƯỜNG GẶP

### Q1: Tại sao không để lương năng suất trong hợp đồng?
**A:** Lương năng suất thay đổi hàng tháng dựa trên KPI/hiệu suất, nên không phù hợp để cố định trong hợp đồng. Hợp đồng chỉ nên chứa các khoản cố định.

### Q2: Nếu quên nhập PERFORMANCE thì sao?
**A:** Khoản "Lương năng suất" sẽ không xuất hiện trên phiếu lương. Nhân viên chỉ nhận lương cơ bản + phụ cấp.

### Q3: Có thể nhập nhiều khoản khác không?
**A:** Có! Tab "Các khoản khác" cho phép nhập:
- `BONUS` - Thưởng
- `DEDUCTION` - Phạt  
- `ADVANCE` - Tạm ứng
- `COMMISSION` - Hoa hồng

### Q4: Lương năng suất có tính BHXH không?
**A:** Tùy vào cấu hình của bạn. Mặc định:
- Lương CB + PC ăn → Tính BHXH
- Lương năng suất → KHÔNG tính BHXH (vì thuộc category BASIC, không phải INSURANCE)

### Q5: Công thức tính có thay đổi không?
**A:** Có! Thay đổi chính:
- **Trước:** Lương NS = (Amount / Công chuẩn) × (Công thực tế + Công phép)
- **Sau:** Lương NS = (Amount / Công chuẩn) × Công thực tế

---

## 🎯 CHECKLIST TRIỂN KHAI

- [ ] Xóa lương năng suất khỏi tất cả hợp đồng hiện có
- [ ] Hướng dẫn HR/Kế toán cách nhập lương năng suất mới
- [ ] Test với 1-2 phiếu lương mẫu
- [ ] Kiểm tra báo cáo lương có đúng không
- [ ] Cập nhật quy trình làm việc nội bộ

---

## 📞 HỖ TRỢ

Nếu có vấn đề, vui lòng liên hệ:
- **Developer:** HDI Development Team
- **Ngày cập nhật:** 22/12/2025
