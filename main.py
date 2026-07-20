import os
import logging
import asyncio
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ChatMember
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackContext,
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

# --- In-memory storage ---
user_warns = {}
user_mutes = {}
message_counter = {}

# --- Bad Words List ---
BAD_WORDS = ['spam', 'fuck', 'shit', 'damn', 'scam', 'phishing', 'porn', 'sex', 'nude']

# --- Helper Functions ---
async def is_user_admin(chat, user_id):
    """Check if user is admin."""
    try:
        member = await chat.get_member(user_id)
        return member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except:
        return False

async def get_user_from_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Extract target user from command or reply."""
    # Check if replying to a message
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    
    # Check if username is in command
    text = update.message.text
    parts = text.split()
    if len(parts) > 1:
        username = parts[1].strip()
        if username.startswith('@'):
            username = username[1:]
        # Try to find user by username
        try:
            async for member in update.effective_chat.get_members():
                if member.user.username and member.user.username.lower() == username.lower():
                    return member.user
        except:
            pass
    return None

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message."""
    user = update.effective_user
    logger.info(f"Start command from {user.username or user.first_name}")
    
    await update.message.reply_text(
        "👋 *Hello! I'm Group Manager Bot!*\n\n"
        "Add me to your group with *Admin* permissions.\n\n"
        "*Commands (Admins only):*\n"
        "/kick - Kick a user (reply to message or @username)\n"
        "/ban - Ban a user (reply to message or @username)\n"
        "/unban @username - Unban a user\n"
        "/mute - Mute a user for 1 hour\n"
        "/warn - Warn a user (3 warnings = mute)\n"
        "/groupinfo - Show group info\n"
        "/help - Show this help\n\n"
        "*Auto Features:*\n"
        "👋 Welcome/Goodbye messages\n"
        "🛡️ Bad word filter\n"
        "🔄 Flood control",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message."""
    await update.message.reply_text(
        "🤖 *Group Manager Bot Help*\n\n"
        "*How to use commands:*\n"
        "1. Reply to a user's message and use command (e.g., reply to user then /kick)\n"
        "2. Or use: /kick @username\n\n"
        "*Commands:*\n"
        "/kick @user - Kick user from group\n"
        "/ban @user - Ban user from group\n"
        "/unban @user - Unban user\n"
        "/mute @user - Mute user for 1 hour\n"
        "/warn @user - Give warning (3 = auto-mute)\n"
        "/groupinfo - Show group statistics\n\n"
        "*Auto Features:*\n"
        "🔄 Welcomes new members\n"
        "🛡️ Deletes messages with bad words\n"
        "🔇 Mutes flooders (5 messages in 5 seconds)",
        parse_mode='Markdown'
    )

async def groupinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get group information."""
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if user is admin
    if not await is_user_admin(chat, user.id):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    
    try:
        admins = await chat.get_administrators()
        admin_list = "\n".join([f"👑 {admin.user.first_name}" for admin in admins[:10]])
        
        # Get member count
        try:
            member_count = await chat.get_member_count()
        except:
            member_count = len(admins) + 5
        
        bot_info = await context.bot.get_me()
        
        await update.message.reply_text(
            f"📊 *Group Information*\n\n"
            f"📌 Name: {chat.title}\n"
            f"🆔 ID: {chat.id}\n"
            f"👥 Members: {member_count}\n"
            f"👑 Admins: {len(admins)}\n"
            f"🤖 Bot: @{bot_info.username}\n\n"
            f"*Admins:*\n{admin_list}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Groupinfo error: {e}")
        await update.message.reply_text("❌ Could not get group information.")

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kick a user."""
    chat = update.effective_chat
    user = update.effective_user
    
    if not await is_user_admin(chat, user.id):
        await update.message.reply_text("❌ Only admins can kick users.")
        return
    
    target = await get_user_from_command(update, context)
    if not target:
        await update.message.reply_text("❌ Reply to a user's message or use: /kick @username")
        return
    
    if target.id == context.bot.id:
        await update.message.reply_text("❌ I can't kick myself!")
        return
    
    try:
        await chat.ban_member(target.id)
        await chat.unban_member(target.id)
        await update.message.reply_text(f"✅ {target.first_name} has been kicked!")
        logger.info(f"User {target.id} kicked from {chat.id} by {user.id}")
    except Exception as e:
        logger.error(f"Kick error: {e}")
        await update.message.reply_text("❌ Failed to kick user. Check bot permissions.")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user."""
    chat = update.effective_chat
    user = update.effective_user
    
    if not await is_user_admin(chat, user.id):
        await update.message.reply_text("❌ Only admins can ban users.")
        return
    
    target = await get_user_from_command(update, context)
    if not target:
        await update.message.reply_text("❌ Reply to a user's message or use: /ban @username")
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

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban a user."""
    chat = update.effective_chat
    user = update.effective_user
    
    if not await is_user_admin(chat, user.id):
        await update.message.reply_text("❌ Only admins can unban users.")
        return
    
    text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ Usage: /unban @username")
        return
    
    username = parts[1].strip()
    if username.startswith('@'):
        username = username[1:]
    
    try:
        await chat.unban_member(username)
        await update.message.reply_text(f"✅ @{username} has been unbanned!")
        logger.info(f"User @{username} unbanned from {chat.id} by {user.id}")
    except Exception as e:
        logger.error(f"Unban error: {e}")
        await update.message.reply_text("❌ Failed to unban user. Make sure the username is correct.")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mute a user for 1 hour."""
    chat = update.effective_chat
    user = update.effective_user
    
    if not await is_user_admin(chat, user.id):
        await update.message.reply_text("❌ Only admins can mute users.")
        return
    
    target = await get_user_from_command(update, context)
    if not target:
        await update.message.reply_text("❌ Reply to a user's message or use: /mute @username")
        return
    
    if target.id == context.bot.id:
        await update.message.reply_text("❌ I can't mute myself!")
        return
    
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
        await update.message.reply_text(f"🔇 {target.first_name} has been muted for 1 hour!")
        logger.info(f"User {target.id} muted in {chat.id} by {user.id}")
    except Exception as e:
        logger.error(f"Mute error: {e}")
        await update.message.reply_text("❌ Failed to mute user. Check bot permissions.")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Warn a user."""
    chat = update.effective_chat
    user = update.effective_user
    
    if not await is_user_admin(chat, user.id):
        await update.message.reply_text("❌ Only admins can warn users.")
        return
    
    target = await get_user_from_command(update, context)
    if not target:
        await update.message.reply_text("❌ Reply to a user's message or use: /warn @username")
        return
    
    if target.id == context.bot.id:
        await update.message.reply_text("❌ I can't warn myself!")
        return
    
    # Track warnings
    user_id = target.id
    if user_id not in user_warns:
        user_warns[user_id] = 0
    user_warns[user_id] += 1
    
    warn_count = user_warns[user_id]
    
    await update.message.reply_text(
        f"⚠️ {target.first_name} has been warned! (Warning {warn_count}/3)"
    )
    
    # Auto-mute after 3 warnings
    if warn_count >= 3:
        try:
            until_date = datetime.now() + timedelta(hours=1)
            await chat.restrict_member(
                user_id,
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_polls=False,
                can_send_other_messages=False,
                until_date=until_date
            )
            user_mutes[user_id] = until_date
            await update.message.reply_text(
                f"🔇 {target.first_name} has been muted for 1 hour (3 warnings reached)!",
                parse_mode='Markdown'
            )
            user_warns[user_id] = 0
            logger.info(f"User {user_id} auto-muted after 3 warnings in {chat.id}")
        except Exception as e:
            logger.error(f"Auto-mute error: {e}")

# --- Auto Moderation ---

async def filter_bad_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete messages with bad words."""
    if not update.message or not update.message.text:
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    # Skip if user is admin
    try:
        if await is_user_admin(chat, user.id):
            return
    except:
        pass
    
    text = update.message.text.lower()
    
    for bad_word in BAD_WORDS:
        if bad_word in text:
            try:
                await update.message.delete()
                await update.message.reply_text(
                    f"⚠️ {user.first_name}, your message was deleted for inappropriate content."
                )
                logger.info(f"Deleted bad word message from {user.id} in {chat.id}")
                break
            except Exception as e:
                logger.error(f"Bad word deletion error: {e}")

async def flood_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prevent message flooding."""
    if not update.message:
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    # Skip if user is admin
    try:
        if await is_user_admin(chat, user.id):
            return
    except:
        pass
    
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
            message_counter[key] = []
        except Exception as e:
            logger.error(f"Flood mute error: {e}")

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when new member joins."""
    if not update.message.new_chat_members:
        return
    
    for new_member in update.message.new_chat_members:
        if new_member.id == context.bot.id:
            # Bot joined
            await update.message.reply_text(
                "👋 Hello! I'm your Group Manager Bot!\n\n"
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

async def goodbye_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send goodbye message when member leaves."""
    if update.message.left_chat_member:
        user = update.message.left_chat_member
        if user.id != context.bot.id:
            await update.message.reply_text(
                f"👋 {user.first_name} has left the group.\nGoodbye! 👋"
            )
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
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("groupinfo", groupinfo))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("warn", warn))
    
    # Auto-moderation handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_bad_words))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, flood_control))
    
    # Member join/leave handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_member))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    # Start
    logger.info("🚀 Starting Group Management Bot...")
    logger.info("✅ Bot is active! Waiting for messages...")
    
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise

if __name__ == "__main__":
    main()
