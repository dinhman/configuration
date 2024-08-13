import logging as l
from telegram import Update as U
from telegram.ext import ContextTypes as C
from config import TOKEN as T
from database import execute_query as eq
from sftp import download_files as df
from image_processing import create_sms_image as cs
import re as r
import os as o
import shutil as s

# Regex patterns
L_PATTERN = r.compile(r'((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+')
GINFO_PATTERN = r.compile(r'^getinfo\s+((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+\s*$', r.IGNORECASE)
GSMS_PATTERN = r.compile(r'^getsms[123]\s+((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+\s*$')
SMST_PATTERN = r.compile('^getsms[123]')

async def start(u: U, c: C):
    await u.message.reply_text("Hi! I'm VID BOT.")

async def handle(u: U, c: C):
    """Msg handler"""
    m = u.message.text.strip()
    l.info(f'Msg: {m}')

    if GINFO_PATTERN.match(m.lower()):
        l.info('Matched getinfo.')
        await _ginfo(u, c, m)

    elif GSMS_PATTERN.match(m.lower()):
        l.info('Matched getsms.')
        await _gsms(u, c, m)
    else:
        l.info('No match.')
        await u.message.reply_text("Unknown command. Use /help for help.")

async def _ginfo(u: U, c: C, m: str):
    """Handle getinfo"""
    uid = u.message.from_user.username
    sv = L_PATTERN.search(m.lower()).group()

    if sv:
        l.info(f'Searching: {sv}')
        q = f"""
            EXEC [localDB].[dbo].[SkypeGetInfo]
            @userName = '{uid}',
            @Domain = 'Inhouse',
            @SearchKey = 1,
            @SearchValue = '{sv}'
        """

        r = eq(q)
        await u.message.reply_text(f'@{uid}: Processing request.')
        if r.empty:
            l.info('No contract.')
            await u.message.reply_text(f'@{uid}: Contract "{sv}" not found.')
        else:
            l.info('Found contract. Sending files.')
            dp = o.path.join('Output', sv)

            if o.path.exists(dp):
                s.rmtree(dp)

            df(r, dp)
            
            fp = o.path.join('Output', f'{sv}.zip')
            try:
                with open(fp, 'rb') as d:
                    await c.bot.send_document(chat_id=u.message.chat_id, document=d)
                await u.message.reply_text(f'@{uid}: Contract "{sv}" sent.')
            except ValueError:
                l.error("Error sending document.")

async def _gsms(u: U, c: C, m: str):
    """Handle getsms"""
    uid = u.message.from_user.username
    sv = L_PATTERN.search(m.lower()).group()
    tmpl = int(SMST_PATTERN.search(m.lower()).group()[-1])

    if sv:
        l.info(f'SMS Search: {sv}')
        q = f"""
            EXEC [localDB].[dbo].[SkypeGetSMS]
            @SkypeId = '{uid}',
            @SkypeGroup = '{u.message.chat_id}',
            @SearchValue = '{sv}',
            @Template = {tmpl}
        """

        r = eq(q)

        if r.empty:
            l.info('No SMS.')
            await u.message.reply_text(f'@{uid}: SMS for "{sv}" not found.')
        else:
            l.info('SMS found. Creating image.')
            fp = cs(r, sv, tmpl)
            cap = f'Image: {o.path.basename(fp)}'
            try:
                with open(fp, 'rb') as p:
                    await c.bot.send_photo(chat_id=u.message.chat_id, photo=p, caption=cap)
                await u.message.reply_text(f'@{uid}: SMS image "{sv}" sent.')
            except Exception as e:
                l.error(f"Image error: {e}")
                await u.message.reply_text("Error processing request.")
