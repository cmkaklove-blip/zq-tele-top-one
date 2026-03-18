#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ultra Fast Telegram Bot - Complete Single File
Welcome/Goodbye + Attack + Admin + Broadcast + Call
Version: V3 Ultra
"""
import urllib.parse
import os
import json
import html
import time
import asyncio
import logging
import re
import asyncio
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict
from telegram.constants import ChatAction
from telegram import (
    Update, ChatMember, ChatPermissions, ChatMemberUpdated,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ChatMemberHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from telegram.constants import ParseMode, ChatType
from telegram.error import (
    TelegramError, BadRequest, Forbidden, RetryAfter, TimedOut, NetworkError
)

# ════════════════════════════════════════════════
#  REPLIT WEB SERVER (ADDED FOR DEPLOYMENT)
# ════════════════════════════════════════════════
from flask import Flask
from threading import Thread

flask_app = Flask('')

@flask_app.route('/')
def home():
    return "Crucial X Bot is running continuously on Replit!"

def run_server():
    # Replit လိုချင်သော Port 8080 ကို ဖွင့်ပေးခြင်း
    flask_app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_server)
    t.start()

# ════════════════════════════════════════════════
#  CONFIGURATION - ဤနေရာတွင် Token ထည့်ပါ
# ════════════════════════════════════════════════

BOT_TOKEN   = "8415336726:AAGCQSPpUdXzIYK_BOabYA8CNbIXhlLs7Lc"          # Bot Token ထည့်ပါ

OWNER_IDS   = [5611725776]                    # Owner Telegram ID ထည့်ပါ (list)
OWNER_USERNAME = "NgaZen" 

SUPPORT_GROUP = "OfcOldButWonCommunity"
SUPPORT_CHANNEL = "ChannelByCrucial"

ATTACK_FILE = "auto_replies.txt"                 # Attack messages file

DATA_DIR              = "data"
GROUPS_FILE           = os.path.join(DATA_DIR, "groups.json")
PRIVATE_USERS_FILE    = os.path.join(DATA_DIR, "private_users.json")
ADMINS_FILE           = os.path.join(DATA_DIR, "admins.json")
MEMBERS_FILE          = os.path.join(DATA_DIR, "members.json")
WELCOME_FILE          = os.path.join(DATA_DIR, "welcome.json")
GOODBYE_FILE          = os.path.join(DATA_DIR, "goodbye.json")
STATS_FILE            = os.path.join(DATA_DIR, "stats.json")
LOCK_FILE             = os.path.join(DATA_DIR, "lock_config.json")
CALL_FILE             = os.path.join(DATA_DIR, "call_config.json")
SPEED_FILE            = os.path.join(DATA_DIR, "speed_config.json")

call_data = {}
call_tasks = {}
pending_admins = {} 

DEFAULT_WELCOME = "{name} သည် {group} သို့ ဝင်ရောက်လာခဲ့ပါသည်"
DEFAULT_GOODBYE = "{name} သည် {group} က ဆရာကြီးတွေကိုကြောက်၍ထွက်ပြေးတိန်းရှောင်းသွားပါပြီ "

DEFAULT_DELAY   = 0.1   # seconds between attack messages (ultra fast)
MIN_DELAY       = 0.5
MAX_DELAY       = 0.5

VERSION = "V3 Ultra"

# ════════════════════════════════════════════════
#  LOGGING
# ════════════════════════════════════════════════
os.makedirs(DATA_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.ERROR, 
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()], 
)
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════
#  ULTRA FAST DATA MANAGEMENT
# ════════════════════════════════════════════════
_file_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
_last_save:  Dict[str, float] = {}
_pending_save: Dict[str, Any] = {}
        
CACHED_ATTACK_LINES = []

def reload_attack_cache():
    global CACHED_ATTACK_LINES
    if os.path.exists(ATTACK_FILE):
        with open(ATTACK_FILE, "r", encoding="utf-8") as f:
            CACHED_ATTACK_LINES = [line.strip() for line in f if line.strip()]
    print(f"✅ Attack lines {len(CACHED_ATTACK_LINES)} ကြောင်းကို RAM ပေါ်သို့ တင်ပြီးပါပြီ။")

BOT_DATA_CACHE = {"groups": {}, "users": {}, "settings": {}}        

def load_json(path: str, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def save_json_sync(path: str, data: dict):
    try:
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
            
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
            
        os.replace(tmp, path)
    except Exception as e:
        logger.error(f"❌ Save failed {path}: {e}")
        
async def auto_save_task(context: ContextTypes.DEFAULT_TYPE):
    groups = load_json(GROUPS_FILE, {})
    private_users = load_json(PRIVATE_USERS_FILE, {})
    schedule_save(GROUPS_FILE, groups)
    schedule_save(PRIVATE_USERS_FILE, private_users)

async def background_save(path: str, data: dict):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, save_json_sync, path, data)

def schedule_save(path: str, data: dict):
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(background_save(path, data))
    except RuntimeError:
        save_json_sync(path, data)

# ════════════════════════════════════════════════
#  IN-MEMORY STATE
# ════════════════════════════════════════════════
welcome_data: Dict[str, Any] = load_json(WELCOME_FILE, {})
goodbye_data: Dict[str, Any] = load_json(GOODBYE_FILE, {})
admins_data:  Dict[str, Any] = load_json(ADMINS_FILE, {"ids": [], "usernames": []})
lock_data:    Dict[str, Any] = load_json(LOCK_FILE, {})
call_data:    Dict[str, Any] = load_json(CALL_FILE, {})
speed_data:   Dict[str, Any] = load_json(SPEED_FILE, {})
stats_data:   Dict[str, Any] = load_json(STATS_FILE, {})
pending_admins:  Dict[str, Any] = {} # /adm button logic အတွက်
call_data:       Dict[int, Any] = {} # call ခေါ်နေလား သိဖို့
call_tasks:      Dict[int, asyncio.Task] = {} # call ရပ်ဖို့ task သိမ်းရန်
ADMIN_IDS: Set[int] = set(int(x) for x in admins_data.get("ids", []) if str(x).lstrip("-").isdigit())
ADMIN_USERNAMES: Set[str] = set(u.lstrip("@").lower() for u in admins_data.get("usernames", []))

attack_tasks:             Dict[Any, asyncio.Task] = {}
attacking_single:         Dict[int, str] = {}
attacking_single_display: Dict[int, str] = {}
attacking_multiple:       Dict[int, List[str]] = {}
attacking_multiple_displays: Dict[int, List[str]] = {}
attack_delay:             Dict[int, float] = {}
call_tasks:               Dict[int, asyncio.Task] = {}
recent_actions:           Dict[str, float] = {}
member_cache:             Dict[str, Dict[str, Any]] = {}

# ════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════
def is_owner(user_id: int) -> bool: return user_id in OWNER_IDS
def is_admin(user) -> bool:
    if user is None: return False
    if user.id in OWNER_IDS or user.id in ADMIN_IDS: return True
    if user.username and user.username.lower() in ADMIN_USERNAMES: return True
    return False
def is_authorized(user) -> bool: return is_admin(user)
def escape_html(text: str) -> str: return html.escape(str(text))
def mention_html(user_id: int, name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{escape_html(name)}</a>'
def is_duplicate_action(chat_id: int, user_id: int, action: str) -> bool:
    key = f"{chat_id}_{user_id}_{action}"
    now = time.time()
    if key in recent_actions and (now - recent_actions[key]) < 10: return True
    recent_actions[key] = now
    return False
def get_attack_delay(chat_id: int) -> float:
    return attack_delay.get(chat_id, speed_data.get(str(chat_id), DEFAULT_DELAY))
def update_stats(key: str, chat_id: int = 0, user_id: int = 0):
    stats_data[key] = stats_data.get(key, 0) + 1
    schedule_save(STATS_FILE, stats_data)

# --- Permissions List & Keyboard Helper ---
# Telegram ရဲ့ Permission အခေါ်အဝေါ်တွေကို Button အတွက် Short-key နဲ့ တွဲထားတာပါ
ADM_PERMS_MAP = {
    "c_info": "can_change_info",
    "d_msgs": "can_delete_messages",
    "b_users": "can_restrict_members",
    "i_users": "can_invite_users",
    "p_msgs": "can_pin_messages",
    "m_chat": "can_manage_chat", 
    "m_live": "can_manage_voice_chats",
    "a_admin": "can_promote_members"
}

def get_adm_kb(target_id, perms):
    labels = {
        "c_info": "Change Group Info",
        "d_msgs": "Delete Messages",
        "b_users": "Ban Users",
        "i_users": "Invite Users via Link",
        "p_msgs": "Pin Messages",
        "m_chat": "Manage Stories & Tags", 
        "m_live": "Manage Live Streams",
        "a_admin": "Add New Admins"
    }
    buttons = []
    for k, name in labels.items():
        status = "✅" if perms[ADM_PERMS_MAP[k]] else "❌"
        buttons.append([InlineKeyboardButton(f"{status} {name}", callback_data=f"adm_t_{target_id}_{k}")])
    
    buttons.append([
        InlineKeyboardButton("✅ Confirm", callback_data=f"adm_confirm_{target_id}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"adm_cancel_{target_id}")
    ])
    return InlineKeyboardMarkup(buttons)
    
# ════════════════════════════════════════════════
#  TARGET RESOLUTION & SENDS
# ════════════════════════════════════════════════
async def resolve_target(context, chat_id: int, arg: str, reply_user=None):
    if reply_user and (arg is None or arg == ""):
        uid = reply_user.id
        return uid, mention_html(uid, reply_user.full_name or "User")
    if arg is None: return None, "Unknown"
    arg = arg.strip()
    if re.fullmatch(r"-?\d+", arg):
        uid = int(arg)
        try:
            member = await context.bot.get_chat_member(chat_id, uid)
            return uid, mention_html(uid, member.user.full_name or f"User{uid}")
        except Exception:
            return uid, f'<a href="tg://user?id={uid}">{uid}</a>'
    username = arg.lstrip("@").lower()
    cache_key = f"{chat_id}_{username}"
    if cache_key in member_cache:
        uid = member_cache[cache_key].get("id")
        if uid: return uid, mention_html(uid, member_cache[cache_key].get("name", username))
    try:
        member = await context.bot.get_chat_member(chat_id, f"@{username}")
        uid = member.user.id
        name = member.user.full_name or username
        member_cache[cache_key] = {"id": uid, "name": name}
        return uid, mention_html(uid, name)
    except Exception: pass
    return None, f"@{escape_html(username)}"

async def safe_send(bot, chat_id: int, text: str, parse_mode=ParseMode.HTML, reply_to: int = None, retries: int = 3) -> bool:
    for attempt in range(retries):
        try:
            kwargs = dict(chat_id=chat_id, text=text, parse_mode=parse_mode)
            if reply_to: kwargs["reply_to_message_id"] = reply_to
            await bot.send_message(**kwargs)
            return True
        except RetryAfter as e: await asyncio.sleep(e.retry_after + 0.1)
        except (TimedOut, NetworkError): await asyncio.sleep(0.5 * (attempt + 1))
        except (BadRequest, Forbidden): return False
        except Exception:
            if attempt < retries - 1: await asyncio.sleep(0.3)
    return False

async def safe_send_photo(bot, chat_id: int, photo, caption: str, parse_mode=ParseMode.HTML) -> bool:
    try:
        await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption, parse_mode=parse_mode)
        return True
    except RetryAfter as e:
        await asyncio.sleep(e.retry_after + 0.1)
        return await safe_send_photo(bot, chat_id, photo, caption, parse_mode)
    except Exception: return False

# ════════════════════════════════════════════════
#  WELCOME / GOODBYE SYSTEM
# ════════════════════════════════════════════════
def build_welcome_text(template: str, user, chat) -> str:
    name_str = f"@{user.username}" if user.username else mention_html(user.id, user.full_name or "User")
    group_str = escape_html(chat.title or "Group")
    text = template.replace("{name}", name_str).replace("{group}", group_str)
    return f"<blockquote>{text}</blockquote>"

async def send_welcome_goodbye(bot, chat_id: int, user_id: int, caption: str):
    sent = False
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count > 0:
            file_id = photos.photos[0][-1].file_id
            sent = await safe_send_photo(bot, chat_id, file_id, caption)
    except Exception: pass
    if not sent: await safe_send(bot, chat_id, caption)

async def process_welcome(bot, chat, user, chat_id_str: str):
    if user.is_bot or is_duplicate_action(chat.id, user.id, "welcome"): return
    template = welcome_data.get(chat_id_str, {}).get("template", DEFAULT_WELCOME)
    caption = build_welcome_text(template, user, chat)
    await send_welcome_goodbye(bot, chat.id, user.id, caption)

async def process_goodbye(bot, chat, user, chat_id_str: str):
    if user.is_bot or is_duplicate_action(chat.id, user.id, "goodbye"): return
    template = goodbye_data.get(chat_id_str, {}).get("template", DEFAULT_GOODBYE)
    caption = build_welcome_text(template, user, chat)
    await send_welcome_goodbye(bot, chat.id, user.id, caption)

async def on_service_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg = update.message
    if not chat or not msg: return

    # New Members (Welcome)
    if msg.new_chat_members:
        text_template = welcome_data.get(str(chat.id), DEFAULT_WELCOME)
        for user in msg.new_chat_members:
            if user.id == context.bot.id: continue
            out_text = text_template.replace("{name}", mention_html(user.id, user.first_name)).replace("{group}", escape_html(chat.title))
            await msg.reply_text(out_text, parse_mode=ParseMode.HTML)

    # Left Member (Goodbye)
    if msg.left_chat_member:
        user = msg.left_chat_member
        if user.id == context.bot.id: return
        text_template = goodbye_data.get(str(chat.id), DEFAULT_GOODBYE)
        out_text = text_template.replace("{name}", mention_html(user.id, user.first_name)).replace("{group}", escape_html(chat.title))
        await msg.reply_text(out_text, parse_mode=ParseMode.HTML)

async def on_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if result.new_chat_member.user.id == context.bot.id:
        if result.new_chat_member.status in [ChatMember.LEFT, ChatMember.BANNED]:
            chat_id = str(update.effective_chat.id)
            # Clean up group data if bot is removed
            for data in [welcome_data, goodbye_data, lock_data, call_data, speed_data]:
                data.pop(chat_id, None)

# Welcome / Goodbye Commands
async def cmd_setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == ChatType.PRIVATE: return await update.message.reply_text("❌ Group ထဲတွင်သာ သုံးနိုင်သည်။")
    if not is_authorized(update.effective_user): return await update.message.reply_text("❌ Permission မရှိပါ။")
    if not context.args: return await update.message.reply_text("📝 <b>Usage:</b> /setwelcome {name} မင်္ဂလာပါ {group} မှ ကြိုဆိုပါသည်\n\nVariables: <code>{name}</code> <code>{group}</code>", parse_mode=ParseMode.HTML)
    cid = str(update.effective_chat.id)
    if cid not in welcome_data: welcome_data[cid] = {}
    welcome_data[cid]["template"] = " ".join(context.args)
    schedule_save(WELCOME_FILE, welcome_data)
    await update.message.reply_text("✅ Welcome message ပြောင်းလဲပြီး။")

async def cmd_setgoodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == ChatType.PRIVATE: return await update.message.reply_text("❌ Group ထဲတွင်သာ သုံးနိုင်သည်။")
    if not is_authorized(update.effective_user): return await update.message.reply_text("❌ Permission မရှိပါ။")
    if not context.args: return await update.message.reply_text("📝 <b>Usage:</b> /setgoodbye {name} ထွက်သွားပါပြီ\n\nVariables: <code>{name}</code> <code>{group}</code>", parse_mode=ParseMode.HTML)
    cid = str(update.effective_chat.id)
    if cid not in goodbye_data: goodbye_data[cid] = {}
    goodbye_data[cid]["template"] = " ".join(context.args)
    schedule_save(GOODBYE_FILE, goodbye_data)
    await update.message.reply_text("✅ Goodbye message ပြောင်းလဲပြီး။")

async def cmd_resetwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user): return await update.message.reply_text("❌ Permission မရှိပါ။")
    cid = str(update.effective_chat.id)
    welcome_data.pop(cid, None); goodbye_data.pop(cid, None)
    schedule_save(WELCOME_FILE, welcome_data); schedule_save(GOODBYE_FILE, goodbye_data)
    await update.message.reply_text("✅ Welcome/Goodbye default ပြန်သွားပြီး။")

# ════════════════════════════════════════════════
#  ATTACK LOOP (ULTRA FAST)
# ════════════════════════════════════════════════
async def ultra_attack_loop(context, chat_id: int, target: str, display_html: str, target_id: Optional[int] = None):
    if not CACHED_ATTACK_LINES: reload_attack_cache()
    ready_messages = [f"{display_html} {html.escape(line)}" for line in CACHED_ATTACK_LINES]
    if not ready_messages: return attacking_single.pop(chat_id, None)
    total = len(ready_messages)
    idx = 0
    while chat_id in attacking_single:
        for _ in range(10): 
            msg_text = ready_messages[idx]
            idx = (idx + 1) if (idx + 1) < total else 0
            asyncio.create_task(context.bot.send_message(
                chat_id=chat_id, text=msg_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True, read_timeout=1.0, write_timeout=1.0
            ))
        delay = get_attack_delay(chat_id)
        await asyncio.sleep(delay if delay > 0 else 0.01)

async def enhanced_multiple_loop(context, chat_id: int, targets: List[str], displays: List[str]):
    if not CACHED_ATTACK_LINES: reload_attack_cache()
    escaped_lines = [html.escape(line) for line in CACHED_ATTACK_LINES]
    ready_messages = []
    max_len = max(len(escaped_lines), len(displays)) * 2 
    for i in range(max_len):
        ready_messages.append(f"{displays[i % len(displays)]} {escaped_lines[i % len(escaped_lines)]}")
    total = len(ready_messages)
    idx = 0
    while chat_id in attacking_multiple:
        for _ in range(10):
            msg_text = ready_messages[idx]
            idx = (idx + 1) if (idx + 1) < total else 0
            asyncio.create_task(context.bot.send_message(
                chat_id=chat_id, text=msg_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True, read_timeout=1.0, write_timeout=1.0
            ))
        delay = get_attack_delay(chat_id)
        await asyncio.sleep(delay if delay > 0 else 0.01)

async def stop_all_attacks(chat_id: int):
    for key in [("single", chat_id), ("multiple", chat_id)]:
        task = attack_tasks.pop(key, None)
        if task and not task.done():
            task.cancel()
            try: await asyncio.wait_for(asyncio.shield(task), timeout=1.0)
            except Exception: pass
    for d in [attacking_single, attacking_single_display, attacking_multiple, attacking_multiple_displays]:
        d.pop(chat_id, None)

# Attack Commands
async def cmd_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user): return await update.message.reply_text("❌ Permission မရှိပါ။")
    chat_id = update.effective_chat.id
    reply_user = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    arg = context.args[0] if context.args else None
    if not arg and not reply_user: return await update.message.reply_text("📌 <b>Usage:</b> /attack @username | ID | (reply)", parse_mode=ParseMode.HTML)
    target_id, display_html = await resolve_target(context, chat_id, arg, reply_user)
    await stop_all_attacks(chat_id)
    target_str = str(target_id) if target_id else (arg or "unknown")
    attacking_single[chat_id] = target_str
    attacking_single_display[chat_id] = display_html
    attack_tasks[("single", chat_id)] = asyncio.create_task(ultra_attack_loop(context, chat_id, target_str, display_html, target_id))
    await update.message.reply_text(f"ဖာသယ်မသားကို Crucial X Bot မှအဝလိုးပြီလေ\nဖာသယ်မသား: {display_html}\nရပ်မယ်ဆို: /stop", parse_mode=ParseMode.HTML)
    update_stats("attacks_started", chat_id, update.effective_user.id)

async def cmd_multiple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user): return await update.message.reply_text("❌ Permission မရှိပါ။")
    if not context.args: return await update.message.reply_text("📌 <b>Usage:</b> /multiple @user1 @user2 @user3 ...", parse_mode=ParseMode.HTML)
    chat_id = update.effective_chat.id
    targets, displays = [], []
    for arg in context.args:
        tid, disp = await resolve_target(context, chat_id, arg, None)
        targets.append(str(tid) if tid else arg); displays.append(disp)
    await stop_all_attacks(chat_id)
    attacking_multiple[chat_id] = targets
    attacking_multiple_displays[chat_id] = displays
    attack_tasks[("multiple", chat_id)] = asyncio.create_task(enhanced_multiple_loop(context, chat_id, targets, displays))
    disp_str = ", ".join(displays[:5]) + (f" ... ({len(displays)} targets)" if len(displays) > 5 else "")
    await update.message.reply_text(f"Multiple ဖြင့် Crucial X Bot မှ စတင်ပါပြီ\nဖာသယ်မသား: {disp_str}\nရပ်ရန်: /stopall", parse_mode=ParseMode.HTML)
    update_stats("attacks_started", chat_id, update.effective_user.id)

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user): return await update.message.reply_text("❌ Permission မရှိပါ။")
    await stop_all_attacks(update.effective_chat.id)
    await update.message.reply_text("🛑 Attack ရပ်လိုက်ပြီ။")

async def cmd_stopall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user): return await update.message.reply_text("❌ Permission မရှိပါ။")
    chat_id = update.effective_chat.id
    await stop_all_attacks(chat_id)
    ct = call_tasks.pop(chat_id, None)
    if ct and not ct.done(): ct.cancel()
    await update.message.reply_text("🛑 Attack & Call အားလုံး ရပ်လိုက်ပြီ။")

async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    reload_attack_cache()
    await update.message.reply_text("✅ Attack messages တွေကို RAM ပေါ်မှာ အသစ်ပြန်တင်လိုက်ပါပြီ။")

async def cmd_speed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user): return await update.message.reply_text("❌ Permission မရှိပါ။")
    chat_id = update.effective_chat.id
    if not context.args:
        current = get_attack_delay(chat_id)
        return await update.message.reply_text(f"⚡ <b>Speed Settings</b>\nCurrent delay: <code>{current}s</code>\nUsage: /speed [seconds]", parse_mode=ParseMode.HTML)
    try:
        val = max(MIN_DELAY, min(MAX_DELAY, float(context.args[0])))
        attack_delay[chat_id] = val
        speed_data[str(chat_id)] = val
        schedule_save(SPEED_FILE, speed_data)
        await update.message.reply_text(f"✅ Speed ပြောင်းလဲပြီး: <code>{val}s</code>", parse_mode=ParseMode.HTML)
    except ValueError: await update.message.reply_text("❌ ဂဏန်းသာ ထည့်ပါ။ eg: /speed 0.05")

# ════════════════════════════════════════════════
#  ADMIN COMMANDS
# ════════════════════════════════════════════════
# --- Target User ကို ရှာပေးတဲ့ Helper (Helpers အပိုင်းမှာ ထားပါ) ---
async def _get_target_user(update: Update, context, chat_id: int):
    # 1. Reply ပြန်ထားရင် အဲဒီလူကို ယူမယ်
    if update.message.reply_to_message: 
        return update.message.reply_to_message.from_user
    
    # 2. Argument (ID သို့ Username) ပါရင် အဲဒီလူကို ရှာမယ်
    if context.args:
        arg = context.args[0].lstrip("@")
        try:
            # ID ဆိုရင် int ပြောင်းမယ်၊ Username ဆိုရင် @ ထည့်မယ်
            user_id_or_name = int(arg) if arg.lstrip("-").isdigit() else f"@{arg}"
            member = await context.bot.get_chat_member(chat_id, user_id_or_name)
            return member.user
        except Exception: 
            pass
            
    return None


async def cmd_adm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    if chat.type == ChatType.PRIVATE: return
    if not is_authorized(user): return await update.message.reply_text("❌ Permission မရှိပါ။")
    
    target = await _get_target_user(update, context, chat.id)
    if not target: return await update.message.reply_text("📌 <b>Usage:</b> /adm [title] (reply or @username or ID)", parse_mode=ParseMode.HTML)
    if target.is_bot: return await update.message.reply_text("❌ Bot ကို Admin ပေးလို့မရပါ။")

    title = ""
    if update.message.reply_to_message: title = " ".join(context.args)
    elif context.args:
        title = " ".join(context.args[1:]) if (context.args[0].startswith("@") or context.args[0].lstrip("-").isdigit()) else " ".join(context.args)

    s_key = f"adm_{target.id}"
    context.chat_data[s_key] = {
        "admin_id": user.id, "target_id": target.id, "target_name": target.full_name, "title": title.strip(),
        "perms": {p: True for p in ADM_PERMS_MAP.values()} 
    }
    context.chat_data[s_key]["perms"]["can_promote_members"] = False 

    await update.message.reply_text(
        f"⚙️ <b>{escape_html(target.full_name)}</b> အတွက် Admin Rights များ\n(Anonymous မပါဝင်ပါ)",
        reply_markup=get_adm_kb(target.id, context.chat_data[s_key]["perms"]),
        parse_mode=ParseMode.HTML
    )

async def adm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user, chat = update.effective_user, update.effective_chat
    if not is_authorized(user): return await query.answer("❌ Permission မရှိပါ။", show_alert=True)

    data = query.data.split("_")
    action, target_id = data[1], data[2]
    s_key = f"adm_{target_id}"
    session = context.chat_data.get(s_key)

    if not session or session["admin_id"] != user.id:
        return await query.answer("❌ Session သက်တမ်းကုန်ပြီ (သို့) သင်နှိပ်ပိုင်ခွင့်မရှိပါ။", show_alert=True)

    if action == "t":
        p_key = ADM_PERMS_MAP["_".join(data[3:])]
        session["perms"][p_key] = not session["perms"][p_key]
        await query.edit_message_reply_markup(reply_markup=get_adm_kb(target_id, session["perms"]))
        await query.answer()

    elif action == "confirm":
        try:
            await context.bot.promote_chat_member(chat_id=chat.id, user_id=int(target_id), is_anonymous=False, **session["perms"])
            if session["title"]:
                try: await context.bot.set_chat_administrator_custom_title(chat_id=chat.id, user_id=int(target_id), custom_title=session["title"])
                except: pass
            
            m_target = mention_html(int(target_id), session["target_name"])
            m_admin = mention_html(user.id, user.full_name)
            t_name = f" [{escape_html(session['title'])}]" if session['title'] else ""
            
            await query.edit_message_text(f"✅ {m_target} ကို {m_admin} မှ{t_name} admin ခန့်အပ်လိုက်ပါသည်", parse_mode=ParseMode.HTML)
            del context.chat_data[s_key]
        except Exception as e: await query.answer(f"❌ Error: {str(e)}", show_alert=True)

    elif action == "cancel":
        await query.edit_message_text("❌ Admin ခန့်အပ်ခြင်းကို ဖျက်သိမ်းလိုက်သည်။")
        if s_key in context.chat_data: del context.chat_data[s_key]

async def cmd_unadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    if chat.type == ChatType.PRIVATE: return
    
    # Permission Check
    if not is_authorized(user): 
        return await update.message.reply_text("❌ Permission မရှိပါ။")
    
    # Target User ကို ရှာမယ်
    target = await _get_target_user(update, context, chat.id)
    if not target: 
        return await update.message.reply_text("📌 <b>Usage:</b> /unadmin (reply or @username or ID)", parse_mode=ParseMode.HTML)
    
    try:
        # Permission အားလုံးကို False ပေးပြီး Admin ဖြုတ်မယ်
        await context.bot.promote_chat_member(
            chat_id=chat.id, 
            user_id=target.id, 
            can_change_info=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_manage_voice_chats=False,
            can_manage_chat=False
        )
        
        target_mention = mention_html(target.id, target.full_name or "User")
        admin_mention = mention_html(user.id, user.full_name)
        
        await update.message.reply_text(
            f"✅ {target_mention} ကို {admin_mention} မှ Admin အဖြစ်မှ ဖယ်ရှားလိုက်ပါသည်", 
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e: 
        await update.message.reply_text(f"❌ Unadmin လုပ်၍မရပါ: {escape_html(str(e))}", parse_mode=ParseMode.HTML)
        

# ════════════════════════════════════════════════
#  SEND / BROADCAST COMMANDS
# ════════════════════════════════════════════════
async def cmd_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user): return await update.message.reply_text("❌ Permission မရှိပါ။")
    reply_msg = update.message.reply_to_message
    if not context.args and not reply_msg: return await update.message.reply_text("📌 Usage: /send [message] (သို့) Reply ပြန်ပြီး /send")
    try:
        sent_msg = await reply_msg.forward(chat_id=update.effective_chat.id) if reply_msg else await context.bot.send_message(chat_id=update.effective_chat.id, text=escape_html(" ".join(context.args)), parse_mode=ParseMode.HTML)
        if sent_msg:
            try: await sent_msg.pin()
            except Exception: pass
    except Exception as e: await update.message.reply_text(f"❌ Error: {e}")

async def cmd_senduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user): return await update.message.reply_text("❌ Permission မရှိပါ။")
    if len(context.args) < 1 and not update.message.reply_to_message: return await update.message.reply_text("📌 Usage: /user @username [message]")
    target_id, _ = await resolve_target(context, update.effective_chat.id, context.args[0])
    if not target_id: return await update.message.reply_text("❌ User ရှာမတွေ့ပါ။")
    reply_msg = update.message.reply_to_message
    try:
        sent_msg = await reply_msg.forward(chat_id=target_id) if reply_msg else await context.bot.send_message(chat_id=target_id, text=escape_html(" ".join(context.args[1:])), parse_mode=ParseMode.HTML)
        if sent_msg:
            await update.message.reply_text(f"✅ User ထံသို့ ပို့ပြီးပါပြီ။")
            try: await sent_msg.pin()
            except Exception: pass
    except Exception: await update.message.reply_text("❌ Message ပို့မရပါ။")

async def cmd_sendall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return await update.message.reply_text("❌ Owner Only Command")
    reply_msg = update.message.reply_to_message
    if not context.args and not reply_msg: return await update.message.reply_text("📌 Usage: /sendall [message] (သို့) Reply")
    groups = load_json(GROUPS_FILE, {})
    success = 0
    await update.message.reply_text(f"📡 {len(groups)} groups သို့ Forward လုပ်ပြီး Pin ထောက်နေပါသည်...")
    for gid in groups:
        try:
            sent_msg = await reply_msg.forward(chat_id=int(gid)) if reply_msg else await context.bot.send_message(chat_id=int(gid), text=escape_html(" ".join(context.args)), parse_mode=ParseMode.HTML)
            if sent_msg:
                success += 1
                try: await sent_msg.pin()
                except Exception: pass
        except Exception: pass
        await asyncio.sleep(0.05)
    await update.message.reply_text(f"✅ Group {success} ခုသို့ ပို့ဆောင်ပြီး Pin ထောက်ပြီးပါပြီ။")

async def cmd_announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    reply_msg = update.message.reply_to_message
    groups = load_json(GROUPS_FILE, {})
    success = 0
    for gid in groups:
        try:
            sent_msg = await reply_msg.forward(chat_id=int(gid)) if reply_msg else await context.bot.send_message(chat_id=int(gid), text="📢 <b>ANNOUNCEMENT</b>\n\n" + escape_html(" ".join(context.args)), parse_mode=ParseMode.HTML)
            if sent_msg:
                success += 1
                try: await sent_msg.pin()
                except: pass
        except Exception: pass
        await asyncio.sleep(0.05)
    await update.message.reply_text(f"✅ Announced to {success} groups.")

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    reply_msg = update.message.reply_to_message
    all_ids = list(set(list(load_json(GROUPS_FILE, {}).keys()) + list(load_json(PRIVATE_USERS_FILE, {}).keys())))
    success = 0
    for cid in all_ids:
        try:
            sent_msg = await reply_msg.forward(chat_id=int(cid)) if reply_msg else await context.bot.send_message(chat_id=int(cid), text=f"📻 <b>BROADCAST</b>\n━━━━━━━━━━━━━━━\n{escape_html(' '.join(context.args))}", parse_mode=ParseMode.HTML)
            if sent_msg:
                success += 1
                try: await sent_msg.pin()
                except: pass
        except Exception: pass
        await asyncio.sleep(0.05)
    await update.message.reply_text(f"✅ Broadcast to {success} chats.")

# ════════════════════════════════════════════════
#  CALL COMMAND 
# ════════════════════════════════════════════════
async def _call_loop(context: ContextTypes.DEFAULT_TYPE, chat_id: int, caller_id: int, message: str, call_type: str = "all"):
    tags = []
    
    # User တွေကို စုစည်းခြင်း
    if call_type == "admin":
        try:
            admins = await context.bot.get_chat_administrators(chat_id)
            for a in admins:
                if not a.user.is_bot: 
                    name = a.user.first_name.strip() if a.user.first_name else "ㅤ"
                    tags.append(f'<a href="tg://user?id={a.user.id}">{html.escape(name)}</a>')
        except Exception: 
            pass
    else:
        members_dict = load_json(MEMBERS_FILE, {}).get(str(chat_id), {})
        for uid, info in members_dict.items():
            if int(uid) != caller_id: 
                name = info.get("name", "").strip() or "ㅤ"
                tags.append(f'<a href="tg://user?id={uid}">{html.escape(name)}</a>')

    if not tags:
        call_data[chat_id] = {"active": False}
        return

    # ၅ ယောက်တစ်စုခွဲပြီး Tag မယ် (Rate Limit မထိအောင်)
    chunk_size = 5
    for i in range(0, len(tags), chunk_size):
        if not (chat_id in call_data and call_data[chat_id].get("active")): 
            break  # Stopcall နှိပ်ရင် ရပ်မယ်
            
        chunk = tags[i : i + chunk_size]
        mentions_part = " | ".join(chunk)
        final_text = f"<blockquote>{html.escape(message)}\n\n{mentions_part} |</blockquote>" if message.strip() else f"<blockquote>{mentions_part} |</blockquote>"
        
        try:
            # Task အသစ်တွေ ပွားမယ့်အစား await နဲ့ တိုက်ရိုက်ပို့မယ်
            await context.bot.send_message(
                chat_id=chat_id, 
                text=final_text, 
                parse_mode=ParseMode.HTML, 
                disable_web_page_preview=True
            )
            await asyncio.sleep(2.5) # FloodWait မဖြစ်အောင် 2.5s နားမယ်
        except Exception as e:
            await asyncio.sleep(5) # Error တက်ရင် ခဏပိုနားမယ်

    call_data[chat_id] = {"active": False} # အကုန်ခေါ်ပြီးရင် အလိုလိုရပ်မယ်

async def cmd_call(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    if chat.type == ChatType.PRIVATE or not is_authorized(user): return
    if call_data.get(chat.id, {}).get("active"): 
        return await update.message.reply_text("⚠️ Call ခေါ်နေဆဲ ဖြစ်ပါတယ်။ ပြီးမှ ထပ်သုံးပါ။")
        
    call_data[chat.id] = {"active": True}
    call_tasks[chat.id] = asyncio.create_task(_call_loop(context, chat.id, user.id, " ".join(context.args), "all"))
    await update.message.reply_text("**ဒီနေရာက မန်ဘာများကို စတင်ခေါ်ပါပြီ**")

async def cmd_adm_call(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    if chat.type == ChatType.PRIVATE or not is_authorized(user): return
    if call_data.get(chat.id, {}).get("active"): 
        return await update.message.reply_text("⚠️ Call ခေါ်နေဆဲ ဖြစ်ပါတယ်။ ပြီးမှ ထပ်သုံးပါ။")
        
    call_data[chat.id] = {"active": True}
    call_tasks[chat.id] = asyncio.create_task(_call_loop(context, chat.id, user.id, " ".join(context.args), "admin"))
    await update.message.reply_text("**ဒီ Group က ဆရာများကို စတင်ခေါ်ပါပြီ**")

async def cmd_stopcall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user): return
    chat_id = update.effective_chat.id
    if chat_id in call_data: 
        call_data[chat_id]["active"] = False
    task = call_tasks.pop(chat_id, None)
    if task: 
        task.cancel()
    await update.message.reply_text("✅ ခေါ်ဆိုခြင်းကို ရပ်တန့်လိုက်ပါသည်။")
    
# ════════════════════════════════════════════════
#  BOT ADMIN MANAGEMENT (OWNER ONLY)
# ════════════════════════════════════════════════
async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return await update.message.reply_text("❌ Owner Only")
    if not context.args: return await update.message.reply_text("📌 Usage: /addadmin @username or ID")
    arg = context.args[0].lstrip("@")
    if arg.lstrip("-").isdigit():
        uid = int(arg)
        ADMIN_IDS.add(uid); admins_data["ids"] = list(ADMIN_IDS)
        schedule_save(ADMINS_FILE, admins_data)
        await update.message.reply_text(f"✅ ID {uid} ကို Bot Admin ထည့်ပြီ")
    else:
        uname = arg.lower()
        ADMIN_USERNAMES.add(uname); admins_data["usernames"] = list(ADMIN_USERNAMES)
        schedule_save(ADMINS_FILE, admins_data)
        await update.message.reply_text(f"✅ @{uname} ကို Bot Admin ထည့်ပြီ")

async def cmd_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return await update.message.reply_text("❌ Owner Only")
    if not context.args: return await update.message.reply_text("📌 Usage: /removeadmin @username or ID")
    arg = context.args[0].lstrip("@")
    if arg.lstrip("-").isdigit():
        uid = int(arg)
        ADMIN_IDS.discard(uid); admins_data["ids"] = list(ADMIN_IDS)
        schedule_save(ADMINS_FILE, admins_data)
        await update.message.reply_text(f"✅ ID {uid} ကို Bot Admin ဖြုတ်ပြီ")
    else:
        uname = arg.lower()
        ADMIN_USERNAMES.discard(uname); admins_data["usernames"] = list(ADMIN_USERNAMES)
        schedule_save(ADMINS_FILE, admins_data)
        await update.message.reply_text(f"✅ @{uname} ကို Bot Admin ဖြုတ်ပြီ")

async def cmd_listadmins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return await update.message.reply_text("❌ Owner Only")
    ids_str = "\n".join([f"  • <code>{i}</code>" for i in ADMIN_IDS]) or "  None"
    names_str = "\n".join([f"  • @{u}" for u in ADMIN_USERNAMES]) or "  None"
    owner_str = "\n".join([f"  • <code>{o}</code>" for o in OWNER_IDS])
    await update.message.reply_text(f"👑 <b>Owners:</b>\n{owner_str}\n\n🛡️ <b>Admin IDs:</b>\n{ids_str}\n\n👤 <b>Admin Usernames:</b>\n{names_str}", parse_mode=ParseMode.HTML)

# ════════════════════════════════════════════════
#  MEMBER TRACKING
# ════════════════════════════════════════════════
async def track_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user or user.is_bot or chat.type == ChatType.PRIVATE:
        return

    chat_id = str(chat.id)
    user_id = str(user.id)
    
    if chat_id not in member_cache:
        member_cache[chat_id] = load_json(MEMBERS_FILE, {}).get(chat_id, {})
        
    name = (user.first_name or "") + (" " + user.last_name if user.last_name else "")
    member_cache[chat_id][user_id] = {"name": name.strip() or "User"}
    
    # Save member list (Background save to keep it ultra fast)
    all_members = load_json(MEMBERS_FILE, {})
    all_members[chat_id] = member_cache[chat_id]
    schedule_save(MEMBERS_FILE, all_members)

# ════════════════════════════════════════════════
#  INFO / UTILITY COMMANDS
# ════════════════════════════════════════════════
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    encoded_text = urllib.parse.quote(f"ဟိုင်း Crucial X Zq : ကျနော်ကို Bot Permission လေပေးပါ User Id : {user_id}")
    keyboard = [[InlineKeyboardButton("Request Permission", url=f"https://t.me/{OWNER_USERNAME}?text={encoded_text}")], [InlineKeyboardButton("Support Group", url=f"https://t.me/{SUPPORT_GROUP}"), InlineKeyboardButton("Support Channel", url=f"https://t.me/{SUPPORT_CHANNEL}")]]
    await update.message.reply_text(text="<b>Crucial X Zq Bot အလုပ်လုပ်နေပါသည်</b><b>ဒီပြိုင်းဆိုင်းရှား Crucial X Zq Bot ကို Permission လိုချင်ရင် ငဇန် Channel ကို အရင် Join ပြီ အောက်က Request Permission ဆိုတဲ့ Button ကိုနှိပ်ပြီ Bot Permission လာတောင်းပေးပါ</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def cmd_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """```
CRUCIAL X ZQ BOT
====================
/start - Start
/show - Commands 
/ping - Ping
/id - Get ID
/stats - Stats
/setwelcome - Set Wel
/setgoodbye - Set Bye
/resetwelcome - Rst Wel
/attack - Attack
/multiple - Multi
/stop - Stop
/stopall - Stop All
/speed - Speed
/adm - Group Adm
/unadmin - Unadmin
/admin - Bot Adm
/radmin - Del Adm
/list_admins - Adm List
/send - Send
/user - DM User
/sendall - Send All
/announce - Announce
/broadcast - Bcast
/call - Call Tag
/adm_call - Adm Call Tag
/stopcall - End Call
/reload - Reload
====================
```"""
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t0 = time.time()
    msg = await update.message.reply_text("🏓 Pong...")
    await msg.edit_text(f"🏓 Pong! <code>{round((time.time() - t0) * 1000, 1)}ms</code>", parse_mode=ParseMode.HTML)

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user): return await update.message.reply_text("❌ Permission မရှိပါ။")
    await update.message.reply_text(f"📊 <b>Bot Stats</b>\n\n⚔️ Attacks started: <code>{stats_data.get('attacks_started', 0)}</code>\n👥 Known groups: <code>{len(load_json(GROUPS_FILE, {}))}</code>\n👤 Known users: <code>{len(load_json(PRIVATE_USERS_FILE, {}))}</code>", parse_mode=ParseMode.HTML)

async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"👤 <b>Your ID:</b> <code>{update.effective_user.id}</code>\n💬 <b>Chat ID:</b> <code>{update.effective_chat.id}</code>"
    if update.message.reply_to_message: text += f"\n↩️ <b>Reply User ID:</b> <code>{update.message.reply_to_message.from_user.id}</code>"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if isinstance(context.error, RetryAfter):
        await asyncio.sleep(context.error.retry_after)
    elif isinstance(context.error, (TimedOut, NetworkError)):
        await asyncio.sleep(2)

async def post_init(application: Application):
    await application.bot.set_my_commands([
        ("start", "Bot စတင်းရန်"),
        ("show", "Show Commands"),
        ("id", "Target id"),
        ("attack", "စတင်း Attack ရန်"),
        ("stop", "Attack ရပ်ရန်"),
        ("speed", "Attack Speed ချိန်ရန်"),
        ("call", "Call Tag"),
        ("adm_call", "Admin Call Tag"),
        ("stopcall", "Tag ရပ်တန့်ရန်"),
    ])


# ════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════
def main():
    # RAM ပေါ်သို့ Attack စာသားများ ကြိုတင်တင်ထားခြင်း
    reload_attack_cache()
    
    # --- Replit အတွက် Web Server ဖွင့်သည့်အပိုင်း ---
    print("Starting Flask web server for Replit...")
    try:
        keep_alive()
    except Exception as e:
        print(f"⚠️ Keep-alive server starting error: {e}")
    # ----------------------------------------------
    
    # Application တည်ဆောက်ခြင်း
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .connection_pool_size(2000)
        .read_timeout(1)
        .write_timeout(1)
        .pool_timeout(1)
        .connect_timeout(1)
        .post_init(post_init)
        .build()
    )

    # ════════════════════════════════════════════════
    #  HANDLERS REGISTRATION
    # ════════════════════════════════════════════════

    # Error Handling
    app.add_error_handler(error_handler)
    
    # Service Messages (Welcome/Goodbye) & Member Tracking
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER, on_service_message))
    app.add_handler(ChatMemberHandler(on_chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, track_member))
    
    # Inline Button (Callback) Handler - /adm အလုပ်လုပ်ရန် အရေးကြီးသည်
    app.add_handler(CallbackQueryHandler(adm_callback, pattern="^adm_"))
    
    # Basic & Information Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("show", cmd_show))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("reload", cmd_reload))
    
    # Welcome & Goodbye Config Commands
    app.add_handler(CommandHandler("setwelcome", cmd_setwelcome))
    app.add_handler(CommandHandler("setgoodbye", cmd_setgoodbye))
    app.add_handler(CommandHandler("resetwelcome", cmd_resetwelcome))
    
    # Attack System Commands
    app.add_handler(CommandHandler("attack", cmd_attack))
    app.add_handler(CommandHandler("multiple", cmd_multiple))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("stopall", cmd_stopall))
    app.add_handler(CommandHandler("speed", cmd_speed))
    
    # Admin Management Commands
    app.add_handler(CommandHandler("adm", cmd_adm))
    app.add_handler(CommandHandler("unadmin", cmd_unadmin))
    app.add_handler(CommandHandler("admin", cmd_addadmin))
    app.add_handler(CommandHandler("radmin", cmd_removeadmin))
    app.add_handler(CommandHandler("list_admins", cmd_listadmins))
    
    # Broadcast & Messaging Commands
    app.add_handler(CommandHandler("send", cmd_send))
    app.add_handler(CommandHandler("user", cmd_senduser))
    app.add_handler(CommandHandler("sendall", cmd_sendall))
    app.add_handler(CommandHandler("announce", cmd_announce))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    
    # Tagging (Call) System Commands
    app.add_handler(CommandHandler("call", cmd_call))
    app.add_handler(CommandHandler("adm_call", cmd_adm_call))
    app.add_handler(CommandHandler("stopcall", cmd_stopcall))
    
    # Auto-save Background Job (၅ မိနစ်တစ်ကြိမ်)
    if app.job_queue: 
        app.job_queue.run_repeating(auto_save_task, interval=300, first=300)

    print(f"🚀 Ultra Fast Bot {VERSION} is running...")
    print("Press Ctrl+C to stop.")
    
    # Bot ကို စတင်လည်ပတ်ခြင်း
    app.run_polling(
        allowed_updates=Update.ALL_TYPES, 
        drop_pending_updates=True, 
        close_loop=False
    )

if __name__ == "__main__":
    main()
