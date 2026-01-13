import odoo
from odoo.http import request
from odoo.modules.registry import Registry


def get_env():
    db_name = request.jwt_payload.get('db')
    registry = Registry(db_name)
    cr = registry.cursor()
    return odoo.api.Environment(cr, odoo.SUPERUSER_ID, {}), cr
