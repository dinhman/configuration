from telegram.ext import Application as App, CommandHandler as CH, MessageHandler as MH, filters as fl
from handlers import start as s, handle as h
from config import TOKEN as T
import httpx as hx

def init_client():
    """Initialize the HTTP client with a specific timeout."""
    return hx.AsyncClient(timeout=10.0)

def setup_application(token: str):
    """Setup and configure the application with handlers."""
    app = App.builder().token(token).build()
    app.request = init_client()
    app.add_handler(CH("start", s))
    app.add_handler(MH(fl.TEXT & ~fl.COMMAND, h))
    return app

def run_bot():
    """Run the bot with polling."""
    app = setup_application(T)
    app.run_polling()

if __name__ == '__main__':
    run_bot()
