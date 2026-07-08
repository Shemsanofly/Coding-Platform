from rest_framework.exceptions import ErrorDetail
from rest_framework.views import exception_handler


def _stringify_detail(value):
    if isinstance(value, ErrorDetail):
        return str(value)
    if isinstance(value, list):
        return [_stringify_detail(item) for item in value]
    if isinstance(value, dict):
        return {key: _stringify_detail(item) for key, item in value.items()}
    return value


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    data = response.data
    if isinstance(data, list):
        detail = _stringify_detail(data[0]) if data else "Request failed."
        response.data = {"detail": detail}
        return response

    if not isinstance(data, dict):
        response.data = {"detail": str(data)}
        return response

    if "detail" in data:
        response.data = {"detail": _stringify_detail(data["detail"])}
        return response

    response.data = {
        "detail": "Validation failed.",
        "errors": _stringify_detail(data),
    }
    return response
