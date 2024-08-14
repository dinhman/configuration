import pyodbc

# Kết nối đến SQL Server
def connect_to_db():
    conn_str = "Driver={SQL Server};Server=172.16.1.10;Database=localDB;UID=man.dinh;PWD=QTcC82HDzvJh;Trusted_Connection=no;"
    return pyodbc.connect(conn_str)

# Hàm để chèn dữ liệu người dùng
def insert_user(crm_user, skype_user, get_sms, dca):
    conn = connect_to_db()
    cursor = conn.cursor()
    try:
        # Convert get_sms to string if necessary
        get_sms = str(get_sms)  # Ensure it's a string if required
        # Perform the INSERT query
        query = "INSERT INTO Users (CrmUser, SkypeUser, GetSMS, DCA) VALUES (?, ?, ?, ?)"
        cursor.execute(query, (crm_user, skype_user, get_sms, dca))
        conn.commit()
        return "Người dùng đã được thêm thành công."
    except Exception as e:
        return f"Đã xảy ra lỗi khi thêm người dùng: {e}"
    finally:
        cursor.close()
        conn.close()



def delete_user(crm_user):
    conn = connect_to_db()
    cursor = conn.cursor()
    try:
        # Thực hiện truy vấn DELETE
        query = "DELETE FROM Users WHERE CrmUser = ?"
        cursor.execute(query, (crm_user,))
        conn.commit()

        # Kiểm tra số lượng bản ghi bị xóa
        if cursor.rowcount > 0:
            return "Người dùng đã được xóa thành công."
        else:
            return "Không tìm thấy người dùng để xóa."
    except Exception as e:
        return f"Đã xảy ra lỗi khi xóa người dùng: {e}"
    finally:
        cursor.close()
        conn.close()


