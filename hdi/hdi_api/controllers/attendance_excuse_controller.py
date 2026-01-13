from odoo import http
from odoo.http import request

from .auth_controller import _verify_token_http, _get_json_data
from ..utils.response_formatter import ResponseFormatter


class MobileAppAttendanceExcuseAPI(http.Controller):

    def _call_model_method(self, method_name, *args, **kwargs):
        jwt_payload = getattr(request, 'jwt_payload', {})
        db_name = jwt_payload.get('db')

        import odoo
        from odoo.modules.registry import Registry

        registry = Registry(db_name)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

            try:
                excuse_model = env['attendance.excuse'].sudo()
                method = getattr(excuse_model, method_name)
                result = method(*args, **kwargs)
                cr.commit()
                return result
            except Exception as e:
                cr.rollback()
                raise

    @http.route('/api/v1/attendance-excuse/create', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def create_excuse(self):
        try:
            data = _get_json_data()
            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')

            result = self._call_model_method('api_create_excuse', data, user_id)
            return ResponseFormatter.success_response('Tạo giải trình thành công', result)

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/attendance-excuse/detail', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_excuse(self):
        try:
            data = _get_json_data()
            excuse_id = data.get('excuse_id')
            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')

            db_name = jwt_payload.get('db')
            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

                try:
                    excuse = env['attendance.excuse'].sudo().browse(excuse_id)
                    result = excuse.api_get_excuse_detail(user_id)
                    cr.commit()

                    return ResponseFormatter.success_response('Lấy chi tiết giải trình thành công', result)

                except Exception as e:
                    cr.rollback()
                    raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/attendance-excuse/list', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_excuse_list(self):
        try:
            data = _get_json_data()
            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')

            limit = data.get('limit', 10)
            offset = data.get('offset', 0)
            state = data.get('state')

            result = self._call_model_method('api_get_my_excuse_list', user_id,
                                             limit=limit, offset=offset, state=state)
            return ResponseFormatter.success_response('Lấy danh sách giải trình thành công', result)

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/attendance-excuse/submit', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def submit_excuse(self):
        try:
            data = _get_json_data()
            excuse_id = data.get('excuse_id')
            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')

            db_name = jwt_payload.get('db')
            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

                try:
                    excuse = env['attendance.excuse'].sudo().browse(excuse_id)
                    result = excuse.api_submit_excuse(user_id)
                    cr.commit()

                    return ResponseFormatter.success_response('Submit giải trình thành công', result)

                except Exception as e:
                    cr.rollback()
                    raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/attendance-excuse/update', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def update_excuse(self):
        try:
            data = _get_json_data()
            excuse_id = data.get('excuse_id')
            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')

            db_name = jwt_payload.get('db')
            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

                try:
                    excuse = env['attendance.excuse'].sudo().browse(excuse_id)

                    update_data = {}
                    if 'reason' in data:
                        update_data['reason'] = data['reason']
                    if 'requested_checkin' in data:
                        update_data['requested_checkin'] = data['requested_checkin']
                    if 'requested_checkout' in data:
                        update_data['requested_checkout'] = data['requested_checkout']

                    if update_data:
                        excuse.write(update_data)

                    result = excuse.api_get_excuse_detail(user_id)
                    cr.commit()

                    return ResponseFormatter.success_response('Cập nhật giải trình thành công', result)

                except Exception as e:
                    cr.rollback()
                    raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

    @http.route('/api/v1/attendance-excuse/delete', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def delete_excuse(self):
        try:
            data = _get_json_data()
            excuse_id = data.get('excuse_id')

            db_name = getattr(request, 'jwt_payload', {}).get('db')
            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

                try:
                    excuse = env['attendance.excuse'].sudo().browse(excuse_id)
                    excuse.unlink()
                    cr.commit()

                    return ResponseFormatter.success_response('Xóa giải trình thành công', {'deleted': True})

                except Exception as e:
                    cr.rollback()
                    raise

        except Exception as e:
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR,
                                                    http_status_code=ResponseFormatter.HTTP_OK)

