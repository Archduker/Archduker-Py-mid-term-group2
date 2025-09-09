import json

# Hàm xử lý: nếu chuỗi rỗng thì trả về None
def normalize(value):
    if value is None:  # đã null sẵn
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value

# Hàm chuyển đổi 1 item
def transform(item):
    return {
        "id": item.get("id"),
        "image_name": normalize(item.get("image_name")),
        "image_path": normalize(item.get("image_path")),
        "image_base64": normalize(item.get("image_base64")),
        "product_name": normalize(item.get("product_name")),
        "manufacturer": {
            "company_name": normalize(item.get("manufacturer_name")),
            "address": normalize(item.get("manufacturer_addr")),
            "phone": normalize(item.get("manufacturer_phone"))
        },
        "importer": {
            "company_name": normalize(item.get("importer_name")),
            "address": normalize(item.get("importer_addr")),
            "phone": normalize(item.get("importer_phone"))
        },
        "manufacturing_date": normalize(item.get("manufacturing_date")),
        "expiry_date": normalize(item.get("expiry_date")),
        "type": normalize(item.get("type"))
    }

# Đọc file input.json
with open("products.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

# Áp dụng chuyển đổi cho toàn bộ list
result = [transform(item) for item in raw_data]

# Ghi ra file output.json
with open("output.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("✅ Xuất file output.json thành công!")
