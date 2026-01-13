from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date, datetime


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    start_work_date = fields.Date(
        string='Ngày bắt đầu làm việc',
        tracking=True
    )

    seniority_text = fields.Char(
        string='Thâm niên',
        compute='_compute_seniority',
        store=True
    )

    @api.depends('start_work_date')
    def _compute_seniority(self):
        """Tính thâm niên hiển thị theo dạng: X năm Y tháng"""
        for rec in self:
            if rec.start_work_date:
                today = date.today()
                start = rec.start_work_date

                years = today.year - start.year
                months = today.month - start.month

                # Nếu chưa tới ngày làm trong tháng ⇒ trừ 1 tháng
                if today.day < start.day:
                    months -= 1

                # Nếu tháng âm ⇒ giảm 1 năm và cộng 12 tháng
                if months < 0:
                    years -= 1
                    months += 12

                # Xuất dạng "X năm Y tháng"
                rec.seniority_text = f"{years} năm {months} tháng"
            else:
                rec.seniority_text = ""

    @api.model
    def api_get_employee_detail(self, employee_id, current_user_id):
        """
        API method để lấy thông tin chi tiết nhân viên
        Kiểm tra quyền truy cập và trả về data
        """
        # Tìm current user và employee
        current_user = self.env['res.users'].browse(current_user_id)
        if not current_user.exists():
            raise UserError('User không tồn tại')

        current_employee = current_user.employee_id
        if not current_employee:
            raise UserError('User hiện tại không phải là nhân viên')

        # Tìm target employee
        target_employee = self.browse(employee_id)
        if not target_employee.exists():
            raise UserError('Không tìm thấy nhân viên')

        # Kiểm tra quyền truy cập
        if not self._check_department_access(current_user, current_employee, target_employee):
            raise UserError('Không có quyền truy cập thông tin nhân viên này')

        # Trả về thông tin chi tiết
        return self._get_employee_detail_data(target_employee)

    def _check_department_access(self, current_user, current_employee, target_employee):
        """Kiểm tra quyền truy cập phòng ban"""
        # Rule 1: Admin có thể xem tất cả
        if current_user.has_group('base.group_system'):
            return True

        # Rule 4: HR có thể xem tất cả
        if current_user.has_group('hr.group_hr_manager') or current_user.has_group('hr.group_hr_user'):
            return True

        # Rule 3: Nhân viên có thể xem thông tin của chính mình
        if current_employee and current_employee.id == target_employee.id:
            return True

        # Rule 2: Trưởng phòng có thể xem nhân viên trong phòng ban và các phòng ban con
        if current_employee and current_employee.department_id:
            # Kiểm tra xem current_employee có phải là trưởng phòng không
            is_department_head = self.env['hr.department'].search([
                ('head_id', '=', current_employee.id)
            ])

            if is_department_head:
                # Lấy tất cả phòng ban con (đệ quy) của từng phòng ban mà trưởng phòng quản lý
                managed_department_ids = []
                for dept in is_department_head:
                    managed_department_ids.extend(self._get_child_departments_recursive(dept.id))

                # Kiểm tra target_employee có trong các phòng ban quản lý không (bao gồm con)
                if target_employee.department_id.id in managed_department_ids:
                    return True

        return False

    def _get_child_departments_recursive(self, parent_department_id, department_ids=None):
        """Lấy danh sách phòng ban con đệ quy"""
        if department_ids is None:
            department_ids = []

        # Thêm phòng ban cha vào list
        if parent_department_id not in department_ids:
            department_ids.append(parent_department_id)

        # Tìm tất cả phòng ban con trực tiếp
        child_departments = self.env['hr.department'].search([
            ('parent_id', '=', parent_department_id)
        ])

        # Đệ quy cho mỗi phòng ban con
        for child in child_departments:
            self._get_child_departments_recursive(child.id, department_ids)

        return department_ids

    def _get_employee_detail_data(self, employee):
        """Lấy thông tin chi tiết của nhân viên"""
        return {
            'id': employee.id,
            'name': employee.name,
            'employee_code': employee.barcode or '',
            'work_email': employee.work_email or '',
            'work_phone': employee.work_phone or '',
            'mobile_phone': employee.mobile_phone or '',
            'job_title': employee.job_title or '',
            'department': {
                'id': employee.department_id.id if employee.department_id else None,
                'name': employee.department_id.name if employee.department_id else '',
                'code': getattr(employee.department_id, 'department_code', '') if employee.department_id else ''
            },
            'manager': {
                'id': employee.parent_id.id if employee.parent_id else None,
                'name': employee.parent_id.name if employee.parent_id else ''
            },
            'work_location': employee.work_location_id.name if employee.work_location_id else '',
            'start_work_date': employee.start_work_date.isoformat() if employee.start_work_date else None,
            'seniority_text': employee.seniority_text or '',
            'birthday': employee.birthday.isoformat() if employee.birthday else None,
            'gender': employee.gender or '',
            'marital': employee.marital or '',
            'bank_account_id': employee.bank_account_id.acc_number if employee.bank_account_id else '',
            'identification_id': employee.identification_id or '',
            'passport_id': employee.passport_id or '',
            'visa_no': employee.visa_no or '',
            'visa_expire': employee.visa_expire.isoformat() if employee.visa_expire else None,
            'active': employee.active,
            'company': {
                'id': employee.company_id.id if employee.company_id else None,
                'name': employee.company_id.name if employee.company_id else ''
            }
        }

    @api.model
    def get_employee_list_api(self, current_user_id, search_text='', department_id=False, job_id=False,
                              active=True, limit=20, offset=0):
        """
        Lấy danh sách nhân viên cho API với phân trang và kiểm tra quyền
        
        Args:
            current_user_id: ID user hiện tại
            search_text: Tìm kiếm trong tên, email, điện thoại
            department_id: Lọc theo phòng ban
            job_id: Lọc theo vị trí
            active: Lọc theo trạng thái hoạt động
            limit: Số mục trên 1 trang
            offset: Offset cho phân trang
            
        Returns:
            dict: {
                'employees': danh sách nhân viên,
                'total_record': tổng số bản ghi,
                'next_page': số trang tiếp theo hoặc None
            }
        """
        # Kiểm tra quyền truy cập
        current_user = self.env['res.users'].browse(current_user_id)
        if not current_user.exists():
            raise UserError('User không tồn tại')
        
        current_employee = current_user.employee_id
        
        domain = []

        if active is not None:
            domain.append(('active', '=', active))

        if search_text:
            domain.append('|')
            domain.append('|')
            domain.append(('name', 'ilike', search_text))
            domain.append(('work_email', 'ilike', search_text))
            domain.append(('mobile_phone', 'ilike', search_text))

        if department_id:
            domain.append(('department_id', '=', department_id))

        if job_id:
            domain.append(('job_id', '=', job_id))

        # Nếu không phải admin/HR, chỉ xem được nhân viên trong phòng ban
        if not (current_user.has_group('base.group_system') or 
                current_user.has_group('hr.group_hr_manager') or 
                current_user.has_group('hr.group_hr_user')):
            # Lấy các phòng ban mà user quản lý hoặc chính user đó
            if current_employee and current_employee.department_id:
                managed_depts = self.env['hr.department'].search([
                    ('head_id', '=', current_employee.id)
                ])
                if managed_depts:
                    # User là trưởng phòng, chỉ xem nhân viên trong phòng ban quản lý
                    managed_dept_ids = []
                    for dept in managed_depts:
                        managed_dept_ids.extend(self._get_child_departments_recursive(dept.id))
                    domain.append(('department_id', 'in', managed_dept_ids))
                else:
                    # User không phải trưởng phòng, chỉ xem chính mình
                    domain.append(('id', '=', current_employee.id))
            else:
                # User không phải nhân viên, không xem được gì
                domain.append(('id', '=', -1))

        employees = self.sudo().search(
            domain,
            limit=limit,
            offset=offset,
            order='name asc'
        )

        total_record = self.sudo().search_count(domain)
        current_page = (offset // limit) + 1 if limit > 0 else 1
        next_page = current_page + 1 if (offset + limit) < total_record else None

        # Lấy base URL cho ảnh
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', 'http://localhost:8069'
        ).rstrip('/')

        employee_list = []
        for emp in employees:
            img_url = f"{base_url}/web/image/hr.employee/{emp.id}?timestamp={int(datetime.now().timestamp())}" \
                if emp.image_1920 else False

            employee_list.append({
                'id': emp.id,
                'code': emp.barcode or '',
                'name': emp.name,
                'mobile_phone': emp.mobile_phone or False,
                'work_phone': emp.work_phone or False,
                'work_email': emp.work_email or False,
                'img_url': img_url,
                'scale_area': {
                    'name': '',
                    'code': ''
                },
                'subsidiary': {
                    'name': '',
                    'code': ''
                },
                'department_id': {
                    'name': emp.department_id.name if emp.department_id else '',
                    'code': getattr(emp.department_id, 'code', '') if emp.department_id else ''
                },
                'job': {
                    'name': emp.job_id.name if emp.job_id else '',
                    'code': getattr(emp.job_id, 'code', '') if emp.job_id else ''
                },
                'position': emp.job_title or '',
                'tax_code': emp.identification_id or False,
                'insurance_code': emp.permit_no or False,
                'social_insurance_code': emp.ssnid or False,
            })

        return {
            'employees': employee_list,
            'total_record': total_record,
            'next_page': next_page,
            'current_page': current_page,
            'items_per_page': limit,
        }

    @api.model
    def get_employee_detail_api(self, current_user_id, employee_id):
        """
        Lấy thông tin chi tiết nhân viên cho API với kiểm tra quyền
        
        Args:
            current_user_id: ID user hiện tại
            employee_id: ID nhân viên
            
        Returns:
            dict: Dữ liệu chi tiết nhân viên hoặc None nếu không có quyền
        """
        # Kiểm tra user tồn tại
        current_user = self.env['res.users'].browse(current_user_id)
        if not current_user.exists():
            raise UserError('User không tồn tại')
        
        current_employee = current_user.employee_id
        
        # Tìm target employee
        employee = self.sudo().browse(employee_id)
        if not employee.exists():
            return None
        
        # Kiểm tra quyền truy cập
        if not self._check_department_access(current_user, current_employee, employee):
            raise UserError('Không có quyền truy cập thông tin nhân viên này')

        # Lấy base URL cho ảnh
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', 'http://localhost:8069'
        ).rstrip('/')
        img_url = f"{base_url}/web/image/hr.employee/{employee.id}" if employee.image_1920 else False

        # Helper để wrap giá trị field
        def field_wrap(value, invisible=False):
            return {'value': value, 'invisible': invisible}

        employee_data = {
            'id': field_wrap(employee.id),
            'code': field_wrap(employee.barcode or ''),
            'name': field_wrap(employee.name),
            'birthday': field_wrap(employee.birthday.strftime('%d/%m/%Y') if employee.birthday else None),
            'position': field_wrap(employee.job_title or ''),
            'mobile_phone': field_wrap(employee.mobile_phone or ''),
            'work_phone': field_wrap(employee.work_phone or ''),
            'work_email': field_wrap(employee.work_email or ''),
            'img_url': field_wrap(img_url),
            'tax_code': field_wrap(employee.identification_id or ''),
            'insurance_code': field_wrap(employee.permit_no or ''),
            'social_insurance_code': field_wrap(employee.ssnid or ''),
            'phone_other': field_wrap(employee.private_phone or ''),
            'current_address': field_wrap({
                'street': employee.private_street or '',
                'street2': employee.private_street2 or '',
                'city': employee.private_city or '',
                'zip': employee.private_zip or '',
                'country': employee.private_country_id.name if employee.private_country_id else '',
            }),
            'default_address': field_wrap(False),
            # Nested objects
            'subsidiary': field_wrap({
                'name': employee.company_id.name if employee.company_id else '',
                'code': getattr(employee.company_id, 'code', '') or ''
            }),
            'company': field_wrap({
                'name': employee.company_id.name if employee.company_id else ''
            }),
            'department': field_wrap({
                'name': employee.department_id.name if employee.department_id else '',
                'code': getattr(employee.department_id, 'code', '') or ''
            }),
            'department_parent': field_wrap({
                'name': employee.department_id.parent_id.name
                    if employee.department_id and employee.department_id.parent_id else '',
                'code': getattr(employee.department_id.parent_id, 'code', '') or ''
                    if employee.department_id and employee.department_id.parent_id else ''
            }),
            'job': field_wrap({
                'name': employee.job_id.name if employee.job_id else '',
                'code': getattr(employee.job_id, 'code', '') or ''
            }),
            'scale_area': field_wrap({
                'name': '',
                'code': ''
            }),
            'relation_family': field_wrap([]),
            'training': field_wrap([]),
            'salary': {'invisible': False},
            'allowance': {'invisible': False},
            'transfer': field_wrap([]),
            'transfer_outer': field_wrap([]),
        }

        return employee_data