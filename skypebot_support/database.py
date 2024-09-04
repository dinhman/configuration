import pymssql
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Database connection information
db_server = os.getenv('DB_SERVER')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_name = os.getenv('DB_NAME')
if not all([db_server, db_user, db_password, db_name]):
    raise ValueError("One or more database connection environment variables are not set.")


# Kết nối đến SQL Server
def connect_to_db():
    conn = pymssql.connect(server=db_server, user=db_user, password=db_password, database=db_name)
    return pymssql.connect(conn)



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


