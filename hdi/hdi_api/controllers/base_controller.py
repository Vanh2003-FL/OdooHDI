"""
Base Controller for HDI API
Cung cấp các hàm tiện ích chung cho tất cả controllers
"""
from contextlib import contextmanager
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class BaseController(http.Controller):
    """Base class cho tất cả HDI API controllers"""

    @contextmanager
    def _get_env_context(self):
        """
        Context manager để lấy environment từ database.
        
        Đảm bảo cleanup cursor sau khi sử dụng.
        
        Ví dụ:
            with self._get_env_context() as env:
                env['hr.employee'].search([...])
        
        Raises:
            ValueError: Nếu không có db_name trong JWT payload
        """
        db_name = request.jwt_payload.get('db')
        
        if not db_name:
            raise ValueError('Database name not found in JWT payload')
        
        cr = None
        try:
            import odoo
            from odoo.modules.registry import Registry
            
            registry = Registry(db_name)
            cr = registry.cursor()
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            yield env
            
        except Exception as e:
            _logger.error(f'Error getting environment: {str(e)}')
            if cr:
                try:
                    cr.rollback()
                except Exception as rollback_error:
                    _logger.error(f'Error rolling back: {str(rollback_error)}')
            raise
        finally:
            if cr:
                try:
                    cr.close()
                except Exception as close_error:
                    _logger.error(f'Error closing cursor: {str(close_error)}')

    def _get_env(self):
        """
        Lấy environment và cursor trực tiếp (dùng khi cần xử lý manual).
        
        ⚠️ CẢNH BÁO: Hãy dùng `_get_env_context()` để tránh rò rỉ kết nối.
        Nếu dùng hàm này, phải đóng cursor thủ công.
        
        Returns:
            tuple: (env, cr) - Environment và database cursor
            
        Raises:
            ValueError: Nếu không có db_name trong JWT payload
        """
        db_name = request.jwt_payload.get('db')
        
        if not db_name:
            raise ValueError('Database name not found in JWT payload')
        
        import odoo
        from odoo.modules.registry import Registry
        
        registry = Registry(db_name)
        cr = registry.cursor()
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        
        return env, cr

    def _ensure_db_name(self):
        """
        Kiểm tra và lấy database name từ JWT.
        
        Returns:
            str: Database name
            
        Raises:
            ValueError: Nếu không có db_name
        """
        db_name = request.jwt_payload.get('db')
        if not db_name:
            raise ValueError('Database name not found in JWT payload')
        return db_name
