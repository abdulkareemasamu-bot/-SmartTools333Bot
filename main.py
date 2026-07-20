import os
import logging
import asyncio
import re
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ChatMember, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ChatMemberHandler,
)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- HTTP Server for Railway Health Checks ---
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK')
    
    def log_message(self, format, *args):
        return

def run_health_server():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"✅ Health server running on port {port}")
    server.serve_forever()

# --- Bad Words List (Customizable) ---
BAD_WORDS = [
    'spam', 'fuck', 'shit', 'damn',
    'badword', 'scam', 'phishing',
    # Add more words as needed
]

# --- User Data Storage ---
user_warns = {}
user_mutes = {}
message_counter = {}

# --- Helper Functions ---
def is_admin(chat_member):
    """Check if user is an admin."""
    if not chat_member:
        return False
    return chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]

def get_target_user(text):
    """Extract target user from command text."""
    if not text:
        return None
    parts = text.split()
    if not parts:
        return None
    # Check if it's a mention or reply
    for part in parts:
        if part.startswith('@'):
            return part[1:]
        if part.startswith('(') and part.endswith(')'):
            continue
    return None

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message for private chat."""
    logger.info(f"Start command from {update.effective_user.username}")
    await update.message.reply_text(
        "👋 *Hello! I'm your Group Management Bot!*\n\n"
        "Add me to your group with admin permissions and I'll help you manage it.\n\n"
        "*Available Commands:*\n"
        "/kick @username - Kick a user\n"
        "/ban @username - Ban a user\n"
        "/mute @username - Mute a user for 1 hour\n"
        "/unban @username - Unban a user\n"
        "/warn @username - Warn a user\n"
        "/groupinfo - Get group information (admins only)\n"
        "/help - Show this help\n\n"
        "*Auto Features:*\n"
        "👋 Automatic welcome messages\n"
        "🛡️ Anti-spam protection\n"
        "📊 Member tracking",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message."""
    await update.message.reply_text(
        "🤖 *Group Management Bot Help*\n\n"
        "*Admin Commands:*\n"
        "/kick @username - Kick user from group\n"
        "/ban @username - Ban user from group\n"
        "/unban @username - Unban user\n"
        "/mute @username - Mute user for 1 hour\n"
        "/warn @username - Give warning to user\n"
        "/groupinfo - Show group stats\n\n"
        "*Auto Features:*\n"
        "🔄 Welcome/Goodbye messages\n"
        "🛡️ Bad word filter (anti-spam)\n"
        "📊 Member tracking\n\n"
        "*How to use:*\n"
        "1. Add bot to group with admin permissions\n"
        "2. Users must be admin to use admin commands\n"
        "3. Commands work with @username or reply to message",
        parse_mode='Markdown'
    )

async def groupinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get group information."""
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if user is admin
    chat_member = await chat.get_member(user.id)
    if not is_admin(chat_member):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    
    try:
        admins = await chat.get_administrators()
        admin_list = "\n".join([f"👑 {admin.user.first_name}" for admin in admins[:10]])
        
        # Get approximate member count from admin list
        member_count = len(await chat.get_administrators()) + 50  # Approximate
        
        # Get bot info
        bot_info = await context.bot.get_me()
        
        await update.message.reply_text(
            f"📊 *Group Information*\n\n"
            f"📌 Name: {chat.title}\n"
            f"🆔 ID: {chat.id}\n"
            f"👥 Members: ~{member_count}+ (approximate)\n"
            f"👑 Admins: {len(admins)}\n"
            f"🤖 Bot: @{bot_info.username}\n"
            f"📅 Since: Running\n\n"
            f"*Admins:*\n{admin_list}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Groupinfo error: {e}")
        await update.message.reply_text("❌ Could not get group information.")

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kick a user from the group."""
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if user is admin
    chat_member = await chat.get_member(user.id)
    if not is_admin(chat_member):
        await update.message.reply_text("❌ Only admins can kick users.")
        return
    
    # Get target user
    target_username = get_target_user(update.message.text)
    target = None
    
    # If replying to a message
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif target_username:
        try:
            # Try to find user by username
            async for member in chat.get_members():
                if member.user.username == target_username:
                    target = member.user
                    break
        except:
            pass
    
    if not target:
        await update.message.reply_text("❌ Please specify a user to kick.\nUsage: /kick @username")
        return
    
    # Don't allow kicking bot
    if target.id == context.bot.id:
        await update.message.reply_text("❌ I can't kick myself!")
        return
    
    try:
        await chat.ban_member(target.id)
        await chat.unban_member(target.id)  # Unban to allow rejoin
        await update.message.reply_text(f"✅ {target.first_name} has been kicked!")
        logger.info(f"User {target.id} kicked from {chat.id} by {user.id}")
    except Exception as e:
        logger.error(f"Kick error: {e}")
        await update.message.reply_text("❌ Failed to kick user. Check bot permissions.")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user from the group."""
    chat = update.effective_chat
    user = update.effective_user
    
    chat_member = await chat.get_member(user.id)
    if not is_admin(chat_member):
        await update.message.reply_text("❌ Only admins can ban users.")
        return
    
    target_username = get_target_user(update.message.text)
    target = None
    
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif target_username:
        try:
            async for member in chat.get_members():
                if member.user.username == target_username:
                    target = member.user
                    break
        except:
            pass
    
    if not target:
        await update.message.reply_text("❌ Please specify a user to ban.\nUsage: /ban @username")
        return
    
    if target.id == context.bot.id:
        await update.message.reply_text("❌ I can't ban myself!")
        return
    
    try:
        await chat.ban_member(target.id)
        await update.message.reply_text(f"✅ {target.first_name} has been banned!")
        logger.info(f"User {target.id} banned from {chat.id} by {user.id}")
    except Exception as e:
        logger.error(f"Ban error: {e}")
        await update.message.reply_text("❌ Failed to ban user.")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban a user."""
    chat = update.effective_chat
    user = update.effective_user
    
    chat_member = await chat.get_member(user.id)
    if not is_admin(chat_member):
        await update.message.reply_text("❌ Only admins can unban users.")
        return
    
    target_username = get_target_user(update.message.text)
    if not target_username:
        await update.message.reply_text("❌ Please specify a username to unban.\nUsage: /unban @username")
        return
    
    try:
        await chat.unban_member(target_username)
        await update.message.reply_text(f"✅ {target_username} has been unbanned!")
        logger.info(f"User {target_username} unbanned from {chat.id} by {user.id}")
    except Exception as e:
        logger.error(f"Unban error: {e}")
        await update.message.reply_text("❌ Failed to unban user.")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mute a user for 1 hour."""
    chat = update.effective_chat
    user = update.effective_user
    
    chat_member = await chat.get_member(user.id)
    if not is_admin(chat_member):
        await update.message.reply_text("❌ Only admins can mute users.")
        return
    
    target_username = get_target_user(update.message.text)
    target = None
    
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif target_username:
        try:
            async for member in chat.get_members():
                if member.user.username == target_username:
                    target = member.user
                    break
        except:
            pass
    
    if not target:
        await update.message.reply_text("❌ Please specify a user to mute.\nUsage: /mute @username")
        return
    
    if target.id == context.bot.id:
        await update.message.reply_text("❌ I can't mute myself!")
        return
    
    try:
        # Mute by restricting permissions for 1 hour
        until_date = datetime.now() + timedelta(hours=1)
        await chat.restrict_member(
            target.id,
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            until_date=until_date
        )
        user_mutes[target.id] = until_date
        await update.message.reply_text(
            f"🔇 {target.first_name} has been muted for 1 hour!"
        )
        logger.info(f"User {target.id} muted in {chat.id} by {user.id}")
    except Exception as e:
        logger.error(f"Mute error: {e}")
        await update.message.reply_text("❌ Failed to mute user. Check bot permissions.")

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Warn a user."""
    chat = update.effective_chat
    user = update.effective_user
    
    chat_member = await chat.get_member(user.id)
    if not is_admin(chat_member):
        await update.message.reply_text("❌ Only admins can warn users.")
        return
    
    target_username = get_target_user(update.message.text)
    target = None
    
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif target_username:
        try:
            async for member in chat.get_members():
                if member.user.username == target_username:
                    target = member.user
                    break
        except:
            pass
    
    if not target:
        await update.message.reply_text("❌ Please specify a user to warn.\nUsage: /warn @username")
        return
    
    if target.id == context.bot.id:
        await update.message.reply_text("❌ I can't warn myself!")
        return
    
    # Track warnings
    if target.id not in user_warns:
        user_warns[target.id] = 0
    user_warns[target.id] += 1
    
    warn_count = user_warns[target.id]
    
    await update.message.reply_text(
        f"⚠️ {target.first_name} has been warned! (Warning {warn_count}/3)"
    )
    
    # Auto-mute after 3 warnings
    if warn_count >= 3:
        try:
            until_date = datetime.now() + timedelta(hours=1)
            await chat.restrict_member(
                target.id,
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_polls=False,
                can_send_other_messages=False,
                until_date=until_date
            )
            user_mutes[target.id] = until_date
            await update.message.reply_text(
                f"🔇 {target.first_name} has been muted for 1 hour (3 warnings reached)!",
                parse_mode='Markdown'
            )
            user_warns[target.id] = 0  # Reset warnings after mute
            logger.info(f"User {target.id} auto-muted after 3 warnings in {chat.id}")
        except Exception as e:
            logger.error(f"Auto-mute error: {e}")

# --- Auto Moderation: Bad Word Filter ---
async def check_bad_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete messages with bad words."""
    if not update.message or not update.message.text:
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if user is admin (skip filter)
    try:
        chat_member = await chat.get_member(user.id)
        if is_admin(chat_member):
            return
    except:
        pass
    
    text = update.message.text.lower()
    
    for bad_word in BAD_WORDS:
        if bad_word in text:
            try:
                await update.message.delete()
                await update.message.reply_text(
                    f"⚠️ {user.first_name}, your message was deleted due to inappropriate content."
                )
                logger.info(f"Deleted bad word message from {user.id} in {chat.id}")
                break
            except Exception as e:
                logger.error(f"Bad word deletion error: {e}")

# --- Flood Control ---
async def check_flood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prevent message flooding."""
    if not update.message:
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    # Skip for admins
    try:
        chat_member = await chat.get_member(user.id)
        if is_admin(chat_member):
            return
    except:
        pass
    
    # Track messages per user
    key = f"{chat.id}_{user.id}"
    now = datetime.now()
    
    if key not in message_counter:
        message_counter[key] = []
    
    # Clean old messages (older than 5 seconds)
    message_counter[key] = [t for t in message_counter[key] if (now - t).total_seconds() < 5]
    message_counter[key].append(now)
    
    # If more than 5 messages in 5 seconds, mute
    if len(message_counter[key]) > 5:
        try:
            until_date = now + timedelta(minutes=5)
            await chat.restrict_member(
                user.id,
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_polls=False,
                can_send_other_messages=False,
                until_date=until_date
            )
            await update.message.reply_text(
                f"🔇 {user.first_name} has been muted for 5 minutes due to flooding!"
            )
            logger.info(f"User {user.id} muted for flooding in {chat.id}")
            message_counter[key] = []  # Reset counter
        except Exception as e:
            logger.error(f"Flood mute error: {e}")

# --- Welcome/Goodbye Messages ---
async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when new member joins."""
    for new_member in update.message.new_chat_members:
        if new_member.id == context.bot.id:
            # Bot joined
            await update.message.reply_text(
                "👋 Hello! I'm your Group Management Bot!\n\n"
                "I'll help you manage this group.\n"
                "Make sure I have admin permissions for full functionality.\n"
                "Type /help to see available commands."
            )
            return
        
        welcome_message = (
            f"👋 *Welcome to the group, {new_member.first_name}!*\n\n"
            f"📌 Please read the rules and be respectful.\n"
            f"🛡️ This group is moderated by a bot.\n"
            f"💬 Feel free to introduce yourself!"
        )
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
        logger.info(f"New member {new_member.id} joined {update.effective_chat.id}")

async def handle_left_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send goodbye message when member leaves."""
    if update.message.left_chat_member:
        user = update.message.left_chat_member
        if user.id != context.bot.id:  # Don't send message when bot leaves
            goodbye_message = (
                f"👋 {user.first_name} has left the group.\n"
                f"Goodbye! 👋"
            )
            await update.message.reply_text(goodbye_message)
            logger.info(f"Member {user.id} left {update.effective_chat.id}")

# --- Error Handler ---
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    logger.error(f"Update {update} caused error: {context.error}")

# --- Main Function ---
def main():
    # Get token
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not set!")
        return

    # Start health server
    import threading
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    # Create bot
    app = Application.builder().token(token).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("groupinfo", groupinfo))
    app.add_handler(CommandHandler("kick", kick_user))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("warn", warn_user))
    
    # Add message handlers for auto-moderation
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_bad_words))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_flood))
    
    # Add member join/leave handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, handle_left_member))
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    # Start
    logger.info("🚀 Starting Group Management Bot...")
    logger.info("✅ Bot is active!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
