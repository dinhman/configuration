import json

# Đường dẫn đến file JSON
file_path = 'ports.lists.json'  # Đảm bảo đường dẫn chính xác

# Mở file JSON và đọc nội dung
with open(file_path, 'r', encoding='utf-8') as file:
    data = json.load(file)

# Nhập giá trị port từ người dùng
input_port = input("Nhập giá trị port: ")

# Tìm kiếm thông tin dựa trên giá trị port
found = False
for key, items in data.items():  # Duyệt qua từng key và danh sách các đối tượng
    for item in items:
        if item["port"] == input_port:
            found = True
            description = item["description"]
            udp = item["udp"]
            status = item["status"]
            tcp = item["tcp"]

            # In ra các giá trị
            print(f"Port: {input_port}")
            print(f"Mô tả: {description}")
            print(f"UDP: {udp}")
            print(f"Trạng thái: {status}")
            print(f"TCP: {tcp}")
            break  # Dừng vòng lặp nếu đã tìm thấy

if not found:
    print(f"Không tìm thấy thông tin cho port: {input_port}")
