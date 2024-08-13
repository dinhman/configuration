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
# import httpx

# -------------------------------------------------------------------

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# -------------------------------------------------------------------

# Định nghĩa các mẫu
LOANEID_PATTERN = re.compile(r'((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+')
GETINFO_PATTERN = re.compile(r'^getinfo\s+((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+\s*$', re.IGNORECASE)

# Token của Telegram Bot
TOKEN = '7256330987:AAEGw3ldYU9uXR9VHNedf910UbsPhQWM4rE'

# Thông tin kết nối
myLocalDBConn = """
    Driver={SQL Server};
    Server=172.16.1.10;
    Database=localDB;
    UID=man.dinh;
    PWD=QTcC82HDzvJh;
    Trusted_Connection=no;
"""

sftpHost = '119.82.135.233'
sftpPort = 2022
sftpUser = 'man.dinh'
sftpPassword = 'ucLMYXTr433nungv'

# Khởi tạo bot và cài đặt logging
bot = Bot(token=TOKEN)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
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

# Khởi tạo Application
application = Application.builder().token(TOKEN).build()

# Đăng ký các handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Chạy bot
application.run_polling()
