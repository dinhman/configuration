import os
import pandas as pd
from zipfile import ZipFile
import shutil
from pathlib import Path
import re
import pyodbc
import paramiko
import stat
import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw


# -------------------------------------------------------------------

# Load environment variables from .env file
load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise ValueError("The TELEGRAM_BOT_TOKEN environment variable is not set.")

# Database connection information
myLocalDBConn = os.getenv('LOCAL_DB_CONN')
if not myLocalDBConn:
    raise ValueError("The LOCAL_DB_CONN environment variable is not set.")

# SFTP connection information
sftpHost = os.getenv('SFTP_HOST')
sftpPort = int(os.getenv('SFTP_PORT', 22))
sftpUser = os.getenv('SFTP_USER')
sftpPassword = os.getenv('SFTP_PASSWORD')
if not all([sftpHost, sftpPort, sftpUser, sftpPassword]):
    raise ValueError("One or more SFTP connection environment variables are not set.")
#----
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# -------------------------------------------------------------------
# Font
SMS_font = ImageFont.truetype("tahoma.ttf", 14)
SMS_Wartermark_font = ImageFont.truetype("tahoma.ttf", 34)

# Định nghĩa các mẫu
LOANEID_PATTERN = re.compile(r'((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+')
GETINFO_PATTERN = re.compile(r'^getinfo\s+((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+\s*$', re.IGNORECASE)
GETSMS_PATTERN = re.compile(r'^getsms[123]\s+((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+\s*$')
SMSTEMPLATE_PATTERN = re.compile('^getsms[123]')
# Combined regular expression patterns
# GETINFO_SMSTEMPLATE_PATTERN = re.compile(r'^(getinfo\s+((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+\s*)$|^(getsms[123]\s+\w+\d+\s*)$', re.IGNORECASE)

# Initialize bot
bot = Bot(token=TOKEN)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.info("Attempting to send photo...")

# client = httpx.AsyncClient(timeout=120.0)  # Adjust the timeout

# SSH client setup
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I'm your Telegram bot.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for incoming text messages"""
    message = update.message.text.strip()
    logging.info(f'Received message: {message}')

    if GETINFO_PATTERN.match(message.lower()):
        logging.info('Pattern matched. Processing getinfo command.')
        await process_getinfo(update, context, message)

    elif  GETSMS_PATTERN.match(message.lower()):
        logging.info('Pattern matched. Processing getinfo command.')
        await process_getsms(update, context, message)
    else:
        logging.info('Pattern did not match.')
        await update.message.reply_text("Sorry, I didn't understand that command. Send /help for available commands.")

async def process_getinfo(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str):
    """Process '/getinfo' command"""
    user_id = update.message.from_user.username
    search_value = LOANEID_PATTERN.search(message.lower()).group()

    if search_value:
        logging.info(f'Search value: {search_value}')
        my_db_conn = pyodbc.connect(myLocalDBConn)
        await update.message.reply_text(f'@{user_id}: Your request is being processed')

        result = pd.read_sql_query(f"""
            EXEC [localDB].[dbo].[SkypeGetInfo]
            @userName = '{user_id}',
            @Domain = 'Inhouse',
            @SearchKey = 1,
            @SearchValue = '{search_value}'
        """, my_db_conn)

        my_db_conn.close()

        if result.empty:
            logging.info('No contract found.')
            await update.message.reply_text(f'@{user_id}: Contract "{search_value}" not found')
        else:
            logging.info('Contract found. Preparing to send files.')
            destination_path = os.path.join('Output', search_value)

            if os.path.exists(destination_path):
                shutil.rmtree(destination_path)

            Path(destination_path).mkdir(parents=True)

            ssh.connect(sftpHost, sftpPort, sftpUser, sftpPassword)
            sftp = ssh.open_sftp()

            for path in result["Path"]:
                temp = sftp.lstat(path)
                if stat.S_ISDIR(temp.st_mode):
                    for file in sftp.listdir(path):
                        full_source_path = path + '/' + file
                        full_dest_path = destination_path + '\\' + file
                        sftp.get(full_source_path, full_dest_path)
                else:
                    full_source_path = path
                    full_dest_path = destination_path + '\\' + os.path.basename(path)
                    sftp.get(full_source_path, full_dest_path)

            ssh.close()

            with ZipFile(os.path.join('Output', search_value + '.zip'), 'w') as zip_obj:
                for folder_name, subfolders, filenames in os.walk(destination_path):
                    for filename in filenames:
                        file_path = os.path.join(folder_name, filename)
                        zip_obj.write(file_path, os.path.basename(file_path))

            full_path = os.path.join('Output', search_value + '.zip')
            try:
                await context.bot.send_document(chat_id=update.message.chat_id, document=open(full_path, 'rb'))
                await update.message.reply_text(f'@{user_id}: Contract "{search_value}" has been sent to you')
            except ValueError:
                logging.error("Oops! Check your contacts & try again...")

async def process_getsms(update: Update, context, message):
    """Process '/getsms' command."""
    user_id = update.message.from_user.username
    search_value = LOANEID_PATTERN.search(message.lower()).group()
    template = int(SMSTEMPLATE_PATTERN.search(message.lower()).group()[-1])

    if search_value:
        logging.info(f'Search value: {search_value}')
        my_db_conn = pyodbc.connect(myLocalDBConn)
        update.message.reply_text(f'@{user_id}: Your request is being processed')

        try:
            result = pd.read_sql_query(f"""
                EXEC [localDB].[dbo].[SkypeGetSMS]
                @SkypeId = '{user_id}',
                @SkypeGroup = '{update.message.chat_id}',
                @SearchValue = '{search_value}',
                @Template = {template}
            """, my_db_conn)

            if result.empty:
                logging.info('No SMS found.')
                update.message.reply_text(f'@{user_id}: SMS for "{search_value}" not found')
            else:
                logging.info('SMS found. Generating and sending image.')
                SMS_img = Image.new('RGB', (500, 450))  # Default size
                if template == 2:
                    SMS_img = Image.new('RGB', (500, 265))
                elif template == 3:
                    SMS_img = Image.new('RGB', (500, 440))
                elif template == 4:
                    SMS_img = Image.new('RGB', (500, 800))

                SMS_draw = ImageDraw.Draw(SMS_img)

                SMS_wartermark = result['CrmUser'][0]
                SMS_draw.text((20, 50), SMS_wartermark, font=SMS_Wartermark_font, fill=(0, 65, 0, 30))
                SMS_draw.text((20, 160), SMS_wartermark, font=SMS_Wartermark_font, fill=(0, 65, 0, 30))
                SMS_draw.text((20, 350), SMS_wartermark, font=SMS_Wartermark_font, fill=(65, 0, 0, 30))

                SMS_text = result['SMS'][0].replace('\r\n', '\n')
                SMS_draw.text((10, 20), SMS_text, font=SMS_font)

                fullPath = os.path.join('Output', f'{search_value}_SMS{template}.jpg')
                SMS_img.save(fullPath)

                caption = f'Here is your image: {os.path.basename(fullPath)}'
                with open(fullPath, 'rb') as photo:
                    await context.bot.send_photo(chat_id=update.message.chat_id, photo=photo, caption=caption)
                    await update.message.reply_text(f'@{user_id}: SMS image for "{search_value}" has been sent to you')

        except Exception as e:
            logging.error(f"Error processing getsms command: {str(e)}")
            update.message.reply_text("Oops! Something went wrong while processing your request.")

        finally:
            my_db_conn.close()

# Khởi tạo Application
application = Application.builder().token(TOKEN).build()

# Đăng ký các handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Chạy bot
application.run_polling()
