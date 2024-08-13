import os
import pandas as pd
from zipfile import ZipFile
import shutil
from pathlib import Path
import re
from sqlalchemy import create_engine, text
import paramiko
import stat
import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from PIL import Image, ImageFont, ImageDraw
import asyncio

# Load environment variables from .env file
load_dotenv()

# Retrieve environment variables
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
myLocalDBConn = os.getenv('LOCAL_DB_CONN', 'mssql+pymssql://man.dinh:QTcC82HDzvJh@172.16.1.10/localDB')
sftpHost = os.getenv('SFTP_HOST', '119.82.135.233')
sftpPort = int(os.getenv('SFTP_PORT', 2022))
sftpUser = os.getenv('SFTP_USER', 'man.dinh')
sftpPassword = os.getenv('SFTP_PASSWORD', 'ucLMYXTr433nungv')

# Check required environment variables
if not all([TOKEN, myLocalDBConn, sftpHost, sftpUser, sftpPassword]):
    raise ValueError("One or more required environment variables are not set.")

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot
bot = Bot(token=TOKEN)

# Font settings
SMS_font = ImageFont.truetype("tahoma.ttf", 14)
SMS_Wartermark_font = ImageFont.truetype("tahoma.ttf", 34)

# Regex patterns
LOANEID_PATTERN = re.compile(r'((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+')
GETINFO_PATTERN = re.compile(r'^getinfo\s+((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+\s*$', re.IGNORECASE)
GETSMS_PATTERN = re.compile(r'^getsms[123]\s+((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+\s*$')
SMSTEMPLATE_PATTERN = re.compile(r'^getsms[123]')

# SQLAlchemy engine setup
engine = create_engine(myLocalDBConn)

# SSH client setup
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I'm your Telegram bot.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for incoming text messages"""
    message = update.message.text.strip()
    logger.info(f'Received message: {message}')

    if GETINFO_PATTERN.match(message.lower()):
        logger.info('Pattern matched. Processing getinfo command.')
        await process_getinfo(update, context, message)
    elif GETSMS_PATTERN.match(message.lower()):
        logger.info('Pattern matched. Processing getsms command.')
        await process_getsms(update, context, message)
    else:
        logger.info('Pattern did not match.')
        await update.message.reply_text("Sorry, I didn't understand that command. Send /help for available commands.")

async def process_getinfo(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str):
    """Process '/getinfo' command"""
    user_id = update.message.from_user.username
    search_value = LOANEID_PATTERN.search(message.lower()).group()

    if search_value:
        logger.info(f'Search value: {search_value}')

        with engine.connect() as connection:
            await update.message.reply_text(f'@{user_id}: Your request is being processed')

            result = pd.read_sql_query(text(f"""
                EXEC [localDB].[dbo].[SkypeGetInfo]
                @userName = :userName,
                @Domain = 'Inhouse',
                @SearchKey = 1,
                @SearchValue = :searchValue
            """), connection, params={"userName": user_id, "searchValue": search_value})

            if result.empty:
                logger.info('No contract found.')
                await update.message.reply_text(f'@{user_id}: Contract "{search_value}" not found')
            else:
                logger.info('Contract found. Preparing to send files.')
                destination_path = os.path.join('Output', search_value)

                if os.path.exists(destination_path):
                    shutil.rmtree(destination_path)

                Path(destination_path).mkdir(parents=True)

                try:
                    ssh.connect(sftpHost, sftpPort, sftpUser, sftpPassword, timeout=60.0)
                    sftp = ssh.open_sftp()

                    for path in result["Path"]:
                        temp = sftp.lstat(path)
                        if stat.S_ISDIR(temp.st_mode):
                            for file in sftp.listdir(path):
                                full_source_path = path + '/.' + file
                                full_dest_path = os.path.join(destination_path, file)
                                sftp.get(full_source_path, full_dest_path)
                        else:
                            full_source_path = path
                            full_dest_path = os.path.join(destination_path, os.path.basename(path))
                            sftp.get(full_source_path, full_dest_path)
                finally:
                    ssh.close()

                with ZipFile(os.path.join('Output', f'{search_value}.zip'), 'w') as zip_obj:
                    for folder_name, subfolders, filenames in os.walk(destination_path):
                        for filename in filenames:
                            file_path = os.path.join(folder_name, filename)
                            zip_obj.write(file_path, os.path.relpath(file_path, destination_path))

                full_path = os.path.join('Output', f'{search_value}.zip')
                try:
                    await context.bot.send_document(chat_id=update.message.chat_id, document=open(full_path, 'rb'))
                    await update.message.reply_text(f'@{user_id}: Contract "{search_value}" has been sent to you')
                except Exception as e:
                    logger.error(f"Error sending document: {e}")
                    await update.message.reply_text("Oops! There was an error sending the document.")

async def process_getsms(update: Update, context, message):
    """Process '/getsms' command."""
    user_id = update.message.from_user.username
    search_value = LOANEID_PATTERN.search(message.lower()).group()
    template = int(SMSTEMPLATE_PATTERN.search(message.lower()).group()[-1])

    if search_value:
        logger.info(f'Search value: {search_value}')

        with engine.connect() as connection:
            await update.message.reply_text(f'@{user_id}: Your request is being processed')

            try:
                result = pd.read_sql_query(text(f"""
                    EXEC [localDB].[dbo].[SkypeGetSMS]
                    @SkypeId = :userId,
                    @SkypeGroup = :chatId,
                    @SearchValue = :searchValue,
                    @Template = :template
                """), connection, params={"userId": user_id, "chatId": update.message.chat_id, "searchValue": search_value, "template": template})

                if result.empty:
                    logger.info('No SMS found.')
                    await update.message.reply_text(f'@{user_id}: SMS for "{search_value}" not found')
                else:
                    logger.info('SMS found. Generating and sending image.')
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
                logger.error(f"Error processing getsms command: {e}")
                await update.message.reply_text("Oops! Something went wrong while processing your request.")

# Initialize Application
application = Application.builder().token(TOKEN).build()

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Run bot
if __name__ == '__main__':
    try:
        application.run_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
