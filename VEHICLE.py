import logging
import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command

# ================= CONFIG =================
BOT_TOKEN = "9107155120:AAHZOav_is5OnqIjGmcw7JpBAGRA-75oDgM"
ADMIN_ID = 9282611275

# TERI ASLI APK FILE ID
APK_FILE_ID = "BQACAgUAAxkBAAMGaueam4-io200DJv_Lf8Fw-EvN6cAAtkkAALE7jlXgdFBorWUEJw9BA"

# Tera Message
WELCOME_MSG = """Download app and enjoy video call service.
come fast bby 🥵💦"""

# ================= BOT SETUP =================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Start Command Handler
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "No Username"
    first_name = message.from_user.first_name or "User"

    # 1. User ko message aur APK bhejo
    try:
        await message.answer(WELCOME_MSG)
        
        # APK bhejo
        await message.answer_document(
            document=APK_FILE_ID,
            caption="📥 Here is your App. Download and install."
        )
            
    except Exception as e:
        logging.error(f"Error sending to user: {e}")
        await message.answer("⚠️ File send error. Admin is fixing it.")

    # 2. Admin ko notification bhejo
    try:
        admin_msg = (
            f"🔔 **New User Started Bot!**\n\n"
            f"👤 Name: {first_name}\n"
            f"🆔 User ID: `{user_id}`\n"
            f"📱 Username: @{username}"
        )
        await bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error sending to admin: {e}")

# ================= RENDER WEB SERVER =================
async def handle(request):
    return web.Response(text="Bot is alive and running!")

async def web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Web server started on port {port}")

# ================= MAIN =================
async def main():
    asyncio.create_task(web_server())
    logging.info("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")