import os
from PIL import ImageFont
# from dotenv import load_dotenv as env
# env()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    raise ValueError("The TELEGRAM_BOT_TOKEN environment variable is not set.")

db_server = os.getenv('DB_SERVER')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_name = os.getenv('DB_NAME')
if not all([db_server, db_user, db_password, db_name]):
    raise ValueError("One or more database connection environment variables are not set.")
sftp_host = os.getenv('SFTP_HOST')
sftp_port = int(os.getenv('SFTP_PORT', 22))
sftp_user = os.getenv('SFTP_USER')
sftp_password = os.getenv('SFTP_PASSWORD')
if not all([sftp_host, sftp_port, sftp_user, sftp_password]):
    raise ValueError("One or more SFTP connection environment variables are not set.")
SMS_font = ImageFont.truetype("tahoma.ttf", 14)
SMS_Wartermark_font = ImageFont.truetype("tahoma.ttf", 34)
