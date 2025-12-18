# HDI Payroll - Hệ thống tính lương Việt Nam

## 📌 Tổng quan

Module **hdi_payroll** là giải pháp tính lương hoàn chỉnh cho Việt Nam, tích hợp sẵn tất cả nghiệp vụ:

- ✅ Tính lương cơ bản theo công thực tế
- ✅ Quản lý phụ cấp (ăn trưa, xăng xe, điện thoại, nhà ở, chức vụ...)
- ✅ Tính BHXH, BHYT, BHTN theo quy định VN (17.5% + 3% + 1% / 8% + 1.5% + 1%)
- ✅ Tính thuế TNCN lũy tiến 7 bậc (5% - 35%)
- ✅ Quản lý người phụ thuộc giảm trừ thuế (11tr + 4.4tr/người)
- ✅ Quản lý tạm ứng lương & khoản vay
- ✅ Quản lý khen thưởng & kỷ luật
- ✅ In phiếu lương, xuất báo cáo

## 📦 Cấu trúc Module

```
hdi_payroll/
├── models/               # 10 models chính
│   ├── hr_employee.py           # Mở rộng: thuế, người PT, vay...
│   ├── hr_contract.py           # Mở rộng: phụ cấp, BH, KPI...
│   ├── hr_payroll_structure.py  # Cấu trúc lương & categories
│   ├── hr_salary_rule.py        # Quy tắc tính (Python code)
│   ├── hr_payslip.py           # Phiếu lương (CORE)
│   ├── hr_payslip_run.py       # Batch tính lương
│   ├── hr_allowance.py         # Loại PC & gán PC
│   ├── hr_loan.py              # Vay/tạm ứng
│   ├── hr_discipline.py        # Kỷ luật & thưởng
│   └── hr_tax.py               # Thuế TNCN & người PT
│
├── data/                 # Dữ liệu mẫu quan trọng
│   ├── hr_salary_rule_category_data.xml
│   ├── hr_salary_structure_data.xml
│   ├── hr_tax_bracket_data.xml          # 7 bậc thuế VN
│   ├── hr_allowance_type_data.xml       # Các loại PC
│   └── hr_salary_rule_data.xml          # ⭐ CÔNG THỨC TÍNH LƯƠNG
│
├── views/                # Views (placeholder)
├── wizard/               # Wizard tạo hàng loạt payslips
├── report/               # Template in phiếu lương
└── security/             # Phân quyền
