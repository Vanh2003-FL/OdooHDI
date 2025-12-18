# -*- coding: utf-8 -*-
{
    'name': 'HDI HR Payroll Management',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Quản lý tính lương theo chuẩn Việt Nam - HDI',
    'description': """
HDI Payroll Management System
==============================

Module tính lương tích hợp đầy đủ cho Việt Nam:

Tính năng chính:
----------------
* Quản lý cấu trúc lương và quy tắc tính lương
* Tính lương cơ bản theo công thực tế
* Quản lý phụ cấp (ăn trưa, xăng xe, điện thoại...)
* Tính BHXH, BHYT, BHTN theo quy định VN
* Tính thuế TNCN lũy tiến (7 bậc thuế)
* Quản lý người phụ thuộc giảm trừ thuế
* Quản lý tạm ứng lương và khoản vay
* Quản lý khen thưởng và kỷ luật
* In phiếu lương cá nhân
* Báo cáo tổng hợp lương theo phòng ban
* Xuất Excel bảng lương

Nghiệp vụ:
----------
* Chấm công → Work Entry → Tính lương → Duyệt → Xuất báo cáo
* Hỗ trợ lương thử việc, lương chính thức
* Tự động tính khấu trừ và thuế
* Tích hợp với kế toán (tùy chọn)
    """,
    'author': 'HDI Development Team',
    'website': 'https://hdi.com.vn',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'hr_contract',
        'hr_attendance',
        'hr_work_entry',
        'hr_work_entry_contract',
        'hr_holidays',
    ],
    'data': [
        # Security
        'security/payroll_security.xml',
        'security/ir.model.access.csv',
        
        # Data - Load theo thứ tự QUAN TRỌNG
        'data/hr_salary_rule_category_data.xml',
        'data/hr_payroll_structure_type_data.xml',
        'data/hr_salary_structure_data.xml',
        'data/hr_tax_bracket_data.xml',
        'data/hr_allowance_type_data.xml',
        'data/hr_salary_rule_data.xml',
        
        # Views - Placeholder
        'views/hr_employee_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_payslip_run_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_allowance_views.xml',
        'views/hr_loan_views.xml',
        'views/hr_discipline_views.xml',
        'views/hr_tax_views.xml',
        
        # Wizard
        'wizard/payslip_batch_create_views.xml',
        
        # Menu
        'views/menu.xml',
        
        # Report
        'report/payroll_reports.xml',
        'report/payslip_report_template.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
