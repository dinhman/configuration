import json

def load_ports(file_path):
    """Đọc nội dung file JSON và trả về dữ liệu."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def find_port_info(data, input_port):
    """Tìm kiếm thông tin port trong dữ liệu."""
    for key, items in data.items():
        for item in items:
            if item["port"] == input_port:
                return item
    return None
