# Hướng dẫn tính lương theo chấm công

## 📊 **Cách tính ngày công**

### 1. **Nguồn dữ liệu**

Module tự động lấy ngày công từ 2 nguồn (theo thứ tự ưu tiên):

#### **Ưu tiên 1: Work Entries** (`hr.work.entry`)
- Nếu có work entries được validated → Lấy từ work entries
- Phân loại theo `work_entry_type_id`
- Tính giờ → Quy đổi ra ngày (8 giờ = 1 ngày)

#### **Ưu tiên 2: Attendance** (`hr.attendance`) 
- Nếu không có work entries → Lấy từ chấm công attendance
- Đếm số ngày có check-in/check-out
- Tính tổng giờ làm việc

#### **Kết hợp với Leave** (`hr.leave`)
- **Nghỉ phép hưởng lương**: `holiday_status_id.unpaid = False`
- **Nghỉ không lương**: `holiday_status_id.unpaid = True`

---

## 🔢 **Các loại ngày công**

| Mã Code | Tên | Nguồn dữ liệu | Dùng để tính lương |
|---------|-----|----------------|-------------------|
| `WORK100` | Ngày công thực tế | `hr.attendance` hoặc `hr.work.entry` | ✅ Có |
| `LEAVE` | Nghỉ phép hưởng lương | `hr.leave` (unpaid=False) | ✅ Có |
| `UNPAID` | Nghỉ không lương | `hr.leave` (unpaid=True) | ❌ Trừ lương |

---

## 💰 **Công thức tính lương**

### **A. Lương cơ bản (BASIC)**

```python
# Công thức:
Lương theo ngày = Lương cơ bản / Công chuẩn
Lương thực tế = Lương theo ngày × (Công thực tế + Phép hưởng lương)
```

**Ví dụ:**
- Lương CB: 10,000,000 VNĐ
- Công chuẩn: 22 ngày
- Công thực tế (WORK100): 20 ngày
- Nghỉ phép (LEAVE): 2 ngày

```
Lương theo ngày = 10,000,000 / 22 = 454,545 VNĐ/ngày
Lương BASIC = 454,545 × (20 + 2) = 10,000,000 VNĐ
```

---

### **B. Phụ cấp ăn trưa (ALW_MEAL)**

```python
# Chỉ tính theo ngày làm việc thực tế (không tính phép)
Phụ cấp ăn = (PC ăn / Công chuẩn) × Công thực tế
```

**Ví dụ:**
- PC ăn tháng: 1,000,000 VNĐ
- Công chuẩn: 22 ngày
- Công thực tế: 20 ngày

```
Phụ cấp ăn = (1,000,000 / 22) × 20 = 909,091 VNĐ
```

---

### **C. Trừ nghỉ không lương (UNPAID_DED)**

```python
# Trừ lương theo ngày nghỉ không lương
Trừ lương = -1 × (Lương CB / Công chuẩn) × Nghỉ không lương
```

**Ví dụ:**
- Lương CB: 10,000,000 VNĐ
- Công chuẩn: 22 ngày  
- Nghỉ không lương: 3 ngày

```
Trừ lương = -1 × (10,000,000 / 22) × 3 = -1,363,636 VNĐ
```

---

## 🔧 **Cấu hình**

### **1. Work Entry Types**

Đảm bảo có các loại work entry với mã code chuẩn:
- `WORK100` - Làm việc bình thường
- `LEAVE` - Nghỉ phép (nếu dùng work entries)

### **2. Leave Types** (`hr.leave.type`)

Cấu hình field `unpaid`:
- ✅ `unpaid = False`: Nghỉ phép hưởng lương (VD: Phép năm, ốm có lương)
- ❌ `unpaid = True`: Nghỉ không lương (VD: Phép không lương, thai sản không lương)

### **3. Công chuẩn tháng**

Cài đặt trong phiếu lương: `payslip.standard_days`
- Mặc định: **22 ngày** (theo Bộ luật Lao động VN)
- Có thể điều chỉnh theo từng tháng (22, 23, 24...)

---

## 📝 **Quy trình tính lương**

```
1. Tạo phiếu lương (hr.payslip)
   ↓
2. Nhấn "Tính lương" (compute_sheet)
   ↓
3. Hệ thống tự động:
   a. Lấy worked_days_line_ids:
      - Từ Work Entries (nếu có)
      - Hoặc Attendance + Leave
   b. Áp dụng salary rules theo sequence
   c. Tính toán từng rule với Python code
   ↓
4. Hiển thị kết quả trong payslip_line_ids
```

---

## ⚠️ **Lưu ý quan trọng**

### **1. Thiếu chấm công**
Nếu không có dữ liệu attendance/work entry:
- Hệ thống tạo WORK100 với số công = Công chuẩn
- Nhân viên vẫn nhận đủ lương

### **2. Nghỉ phép**
- **Phép hưởng lương**: Cộng vào ngày công → Nhận đủ lương
- **Phép không lương**: Bị trừ theo công thức

### **3. Đi muộn/về sớm**
- Cần tích hợp module `hdi_attendance_excuse`
- Hoặc tạo rule riêng để xử lý penalty

---

## 🧪 **Test Cases**

### **Case 1: Full công**
```
WORK100 = 22 ngày
LEAVE = 0 ngày
→ Lương = 100% lương CB
```

### **Case 2: Có nghỉ phép hưởng lương**
```
WORK100 = 20 ngày
LEAVE = 2 ngày
→ Lương = 100% lương CB (20+2=22)
```

### **Case 3: Nghỉ không lương**
```
WORK100 = 19 ngày
UNPAID = 3 ngày
→ Lương = 86.4% lương CB (19/22)
→ Có rule UNPAID_DED trừ thêm
```

### **Case 4: Không chấm công**
```
Không có dữ liệu attendance
→ Tạo WORK100 = 22 ngày (mặc định)
→ Lương = 100% lương CB
```

---

## 🔗 **Files liên quan**

- Model: `/models/hr_payslip.py` → Method `_get_worked_days_lines()`
- Rules: `/data/hr_salary_rule_data.xml`
  - `rule_basic_salary` (BASIC)
  - `rule_meal_allowance` (ALW_MEAL)
  - `rule_unpaid_leave_deduction` (UNPAID_DED)

---

## 📞 **Support**

Nếu có vấn đề về tính lương theo công:
1. Kiểm tra `worked_days_line_ids` trong phiếu lương
2. Xem log Python trong salary rule
3. Kiểm tra dữ liệu attendance/leave trong kỳ tính lương
