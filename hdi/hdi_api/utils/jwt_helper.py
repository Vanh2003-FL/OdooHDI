import hashlib
import odoo
from odoo.http import request
from odoo.modules.registry import Registry

DEFAULT_JWT_SECRET_KEY = 'your-secret-key-change-in-production'


def get_jwt_secret_key():
    try:
        return request.env['ir.config_parameter'].sudo().get_param(
            'hdi_api.jwt_secret_key',
            DEFAULT_JWT_SECRET_KEY
        )
    except Exception:
        return DEFAULT_JWT_SECRET_KEY


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def is_token_blacklisted(token, db_name):
    try:
        registry = Registry(db_name)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            blacklist = env['jwt.token.blacklist'].sudo().search([
                ('token_hash', '=', hash_token(token))
            ], limit=1)
            return bool(blacklist)
    except Exception:
        return False


def add_token_to_blacklist(token, user_id, db_name, exp_time):
    try:
        registry = Registry(db_name)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            env['jwt.token.blacklist'].sudo().create({
                'token_hash': hash_token(token),
                'user_id': user_id,
                'exp_time': exp_time,
            })
            cr.commit()
    except Exception as e:
        pass
