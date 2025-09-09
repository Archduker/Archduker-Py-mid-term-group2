import os
import re
import json
import csv
import base64
from io import BytesIO
from datetime import datetime, date

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk, ImageOps
import mysql.connector

MAX_IMAGE_BYTES = 3 * 1024 * 1024   # 3MB
THUMB_SIZE = (240, 240)             # preview
SAVE_JPEG_QUALITY = 85              # chất lượng nén khi re-encode

#database
def get_connection():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="BaeTyn0606@",
            database="product_db"
        )
    except mysql.connector.Error as e:
        messagebox.showerror("Lỗi DB", f"Không thể kết nối database: {e}")
        return None

def open_image_safely(file_path: str) -> Image.Image:
    """
    Mở ảnh và auto-rotate theo EXIF (nếu có), trả về PIL.Image.
    """
    img = Image.open(file_path)
    img = ImageOps.exif_transpose(img)
    return img
def image_to_base64(image_path: str) -> str | None:
    """
    Đọc ảnh → nếu > MAX_IMAGE_BYTES thì nén/resize → Base64 (UTF-8 string).
    """
    try:
        if not os.path.exists(image_path):
            messagebox.showerror("Lỗi ảnh", "File ảnh không tồn tại.")
            return None

        img = open_image_safely(image_path)

        def encode_img_to_b64(pil_img: Image.Image) -> str:
            buf = BytesIO()
            # Chọn định dạng xuất: PNG cho ảnh có alpha, còn lại JPEG
            fmt = "PNG" if pil_img.mode in ("RGBA", "LA") else "JPEG"
            save_kwargs = {}
            if fmt == "JPEG":
                if pil_img.mode in ("RGBA", "LA"):
                    pil_img = pil_img.convert("RGB")
                save_kwargs.update({"quality": SAVE_JPEG_QUALITY, "optimize": True})
            pil_img.save(buf, format=fmt, **save_kwargs)
            data = buf.getvalue()
            return base64.b64encode(data).decode("utf-8")

        try:
            file_size = os.path.getsize(image_path)
        except OSError:
            file_size = MAX_IMAGE_BYTES + 1  # nếu không đọc được size, cưỡng bức nén

        if file_size <= MAX_IMAGE_BYTES:
            return encode_img_to_b64(img)

        # File lớn → giảm chiều lớn về tối đa 1600px và re-encode
        max_side = max(img.size)
        if max_side > 1600:
            ratio = 1600 / float(max_side)
            new_size = (int(img.size[0]*ratio), int(img.size[1]*ratio))
            img = img.resize(new_size, Image.LANCZOS)

        return encode_img_to_b64(img)

    except Exception as e:
        messagebox.showerror("Lỗi ảnh", f"Không thể đọc/xử lý ảnh: {e}")
        return None

def none_if_empty(value: str):
    v = (value or "").strip()
    return v if v else None

def is_valid_date(date_text: str):
    if not (date_text or "").strip():
        return True
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def is_date_order(manu: str, exp: str):
    manu = (manu or "").strip()
    exp  = (exp  or "").strip()
    if not manu or not exp:
        return True
    m = datetime.strptime(manu, "%Y-%m-%d").date()
    e = datetime.strptime(exp,  "%Y-%m-%d").date()
    return m <= e

PHONE_RE = re.compile(r'^(?:\+84|0)\d{9,12}$')
def is_valid_phone(phone: str):
    p = (phone or "").strip()
    if not p:
        return True
    return bool(PHONE_RE.fullmatch(p))
def save_product():
    try:
        # Validations
        if not image_path_var.get():
            messagebox.showerror("Lỗi", "Vui lòng chọn hình ảnh sản phẩm!")
            return
        if type_var.get() not in {"Bánh", "Kẹo"}:
            messagebox.showerror("Lỗi", "Vui lòng chọn loại sản phẩm (Bánh/Kẹo)!")
            return
        if not is_valid_date(manu_date_var.get()):
            messagebox.showerror("Lỗi", "Ngày sản xuất không đúng định dạng YYYY-MM-DD!")
            return
        if not is_valid_date(expiry_date_var.get()):
            messagebox.showerror("Lỗi", "Ngày hết hạn không đúng định dạng YYYY-MM-DD!")
            return
        if not is_date_order(manu_date_var.get(), expiry_date_var.get()):
            messagebox.showerror("Lỗi", "NSX phải nhỏ hơn hoặc bằng HSD.")
            return
        if not is_valid_phone(manu_phone_var.get()):
            messagebox.showerror("Lỗi", "SĐT NSX không hợp lệ!")
            return
        if not is_valid_phone(importer_phone_var.get()):
            messagebox.showerror("Lỗi", "SĐT NK không hợp lệ!")
            return

        confirm = messagebox.askyesno(
            "Xác nhận",
            f"Bạn có chắc muốn lưu sản phẩm:\n\nTên: {product_name_var.get()}\nLoại: {type_var.get()}"
        )
        if not confirm:
            return

        # Chuẩn hoá & chuyển ảnh
        img_path  = image_path_var.get()
        img_b64   = image_to_base64(img_path)
        if not img_b64:
            return

        product_tuple = (
            os.path.basename(img_path),              # image_name
            img_path,                                # image_path (lưu ý: đường dẫn cục bộ)
            img_b64,                                 # image_base64
            none_if_empty(product_name_var.get()),   # product_name
            none_if_empty(manu_name_var.get()),      # manufacturer_name
            none_if_empty(manu_addr_var.get()),      # manufacturer_addr
            none_if_empty(manu_phone_var.get()),     # manufacturer_phone
            none_if_empty(importer_name_var.get()),  # importer_name
            none_if_empty(importer_addr_var.get()),  # importer_addr
            none_if_empty(importer_phone_var.get()), # importer_phone
            none_if_empty(manu_date_var.get()),      # manufacturing_date
            none_if_empty(expiry_date_var.get()),    # expiry_date
            type_var.get()                           # type
        )

        conn = get_connection()
        if not conn:
            return

        cursor = None
        try:
            cursor = conn.cursor()
            insert_sql = """
                INSERT INTO products 
                (image_name, image_path, image_base64, product_name,
                 manufacturer_name, manufacturer_addr, manufacturer_phone,
                 importer_name, importer_addr, importer_phone,
                 manufacturing_date, expiry_date, type)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """
            cursor.execute(insert_sql, product_tuple)
            conn.commit()
        except mysql.connector.Error as e:
            try: conn.rollback()
            except: pass
            messagebox.showerror("Lỗi DB", f"Không thể lưu: {e}")
            return
        finally:
            if cursor is not None:
                try: cursor.close()
                except: pass
            try: conn.close()
            except: pass

        messagebox.showinfo("Thành công", f"Đã lưu sản phẩm: {product_name_var.get()}")

    except Exception as e:
        messagebox.showerror("Lỗi", f"Không thể lưu: {e}")

def load_image():
    file_path = filedialog.askopenfilename(
        filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp")]
    )
    if not file_path:
        return

    ext_ok = file_path.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    if not ext_ok:
        messagebox.showerror("Lỗi", "Chỉ nhận JPG, JPEG, PNG, WEBP.")
        return

    try:
        img = open_image_safely(file_path)
    except Exception as e:
        messagebox.showerror("Lỗi ảnh", f"Không thể mở ảnh: {e}")
        return

    image_path_var.set(file_path)

    img = img.copy()
    img.thumbnail(THUMB_SIZE)
    img_tk = ImageTk.PhotoImage(img)
    image_label.config(image=img_tk)
    image_label.image = img_tk
def view_products():
    conn = get_connection()
    if not conn:
        return

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT product_name, type, manufacturing_date, expiry_date FROM products")
        rows = cursor.fetchall()
    except mysql.connector.Error as e:
        messagebox.showerror("Lỗi DB", f"Không thể đọc dữ liệu: {e}")
        return
    finally:
        if cursor is not None:
            try: cursor.close()
            except: pass
        try: conn.close()
        except: pass

    win = tk.Toplevel(root)
    win.title("Danh sách sản phẩm")
    win.geometry("600x400")

    cols = ("Tên", "Loại", "NSX", "HSD")
    tree = ttk.Treeview(win, columns=cols, show="headings")
    for c, w in zip(cols, (250, 80, 120, 120)):
        tree.heading(c, text=c)
        tree.column(c, width=w, anchor="w")
    tree.pack(fill="both", expand=True)

    for row in rows:
        tree.insert("", tk.END, values=row)


def convert_dates_to_string(records):
    """date -> chuỗi 'YYYY-MM-DD' (in-place)"""
    for record in records:
        for key, value in record.items():
            if isinstance(value, date):
                record[key] = value.strftime("%Y-%m-%d")
    return records

def export_json():
    try:
        conn = get_connection()
        if not conn:
            return
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        cursor.close()
        conn.close()

        if not products:
            messagebox.showwarning("Cảnh báo", "Không có dữ liệu!")
            return

        products = convert_dates_to_string(products)

        save_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="products.json",
            title="Chọn nơi lưu JSON"
        )
        if not save_path:
            return

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=4)
        messagebox.showinfo("Xuất JSON", f"Đã xuất file: {save_path}")

    except Exception as e:
        messagebox.showerror("Lỗi", f"Không thể xuất JSON: {e}")

def export_csv():
    try:
        conn = get_connection()
        if not conn:
            return
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        cursor.close()
        conn.close()

        if not products:
            messagebox.showwarning("Cảnh báo", "Không có dữ liệu!")
            return

        products = convert_dates_to_string(products)

        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="products.csv",
            title="Chọn nơi lưu CSV"
        )
        if not save_path:
            return

        with open(save_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=products[0].keys())
            writer.writeheader()
            writer.writerows(products)
        messagebox.showinfo("Xuất CSV", f"Đã xuất file: {save_path}")

    except Exception as e:
        messagebox.showerror("Lỗi", f"Không thể xuất CSV: {e}")
root = tk.Tk()
root.title("Quản lý sản phẩm Bánh/Kẹo")
root.geometry("620x900")

# Tk variables
image_path_var   = tk.StringVar()
product_name_var = tk.StringVar()
manu_name_var    = tk.StringVar()
manu_addr_var    = tk.StringVar()
manu_phone_var   = tk.StringVar()
importer_name_var= tk.StringVar()
importer_addr_var= tk.StringVar()
importer_phone_var= tk.StringVar()
manu_date_var    = tk.StringVar()
expiry_date_var  = tk.StringVar()
type_var         = tk.StringVar()

padx = 10
pady = 6

frm = ttk.Frame(root, padding=10)
frm.pack(fill="both", expand=True)

ttk.Button(frm, text="Chọn ảnh", command=load_image).pack(pady=(0,8))
image_label = ttk.Label(frm)
image_label.pack(pady=(0,10))

def add_labeled_entry(parent, label, var):
    ttk.Label(parent, text=label).pack(anchor="w", padx=padx)
    ttk.Entry(parent, textvariable=var).pack(fill="x", padx=padx, pady=(0,pady))

add_labeled_entry(frm, "Tên sản phẩm", product_name_var)

add_labeled_entry(frm, "Nhà sản xuất", manu_name_var)
add_labeled_entry(frm, "Địa chỉ NSX", manu_addr_var)
add_labeled_entry(frm, "SĐT NSX", manu_phone_var)

add_labeled_entry(frm, "Nhà nhập khẩu", importer_name_var)
add_labeled_entry(frm, "Địa chỉ NK", importer_addr_var)
add_labeled_entry(frm, "SĐT NK", importer_phone_var)

add_labeled_entry(frm, "Ngày sản xuất (YYYY-MM-DD)", manu_date_var)
add_labeled_entry(frm, "Ngày hết hạn (YYYY-MM-DD)", expiry_date_var)

ttk.Label(frm, text="Loại sản phẩm").pack(anchor="w", padx=padx)
ttk.Combobox(frm, textvariable=type_var, values=["Bánh", "Kẹo"], state="readonly").pack(fill="x", padx=padx, pady=(0,pady))

ttk.Separator(frm).pack(fill="x", pady=8)

btns = ttk.Frame(frm)
btns.pack(fill="x")
ttk.Button(btns, text="Lưu sản phẩm", command=save_product).pack(side="left", padx=5, pady=5)
ttk.Button(btns, text="Xem sản phẩm", command=view_products).pack(side="left", padx=5, pady=5)
ttk.Button(btns, text="Xuất JSON", command=export_json).pack(side="left", padx=5, pady=5)
ttk.Button(btns, text="Xuất CSV", command=export_csv).pack(side="left", padx=5, pady=5)

root.mainloop()