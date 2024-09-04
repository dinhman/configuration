import json

def load_http_codes(file_path):
    """Nạp dữ liệu từ file JSON chứa mã HTTP."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def get_http_code_info(http_data, code_key):
    """Trích xuất thông tin về mã HTTP từ dữ liệu đã nạp."""
    code_info = http_data.get(code_key)
    if code_info:
        message = code_info.get('message', 'Không có thông tin')
        description = code_info.get('description', 'Không có mô tả')
        return message, description
    return None, None
