import json
from odoo.http import request


def get_json_data():
    try:
        if hasattr(request, 'get_json_data'):
            return request.get_json_data()
        elif hasattr(request, 'jsonrequest'):
            return request.jsonrequest
        else:
            return json.loads(request.httprequest.data.decode('utf-8'))
    except Exception:
        return {}


def get_request_data():
    """
    Lấy dữ liệu từ request (JSON body hoặc form data)
    """
    try:
        body = request.httprequest.get_data(as_text=True)
        if body:
            data = json.loads(body)
            return data
    except Exception:
        pass

    form_data = request.httprequest.form.to_dict()
    return form_data

