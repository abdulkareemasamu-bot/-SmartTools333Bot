import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- HTTP Server for Railway ---
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

# --- Bot Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when /start is issued."""
    user = update.effective_user
    logger.info(f"Start command from {user.username or user.first_name}")
    await update.message.reply_text(
        f"👋 Hello {user.first_name}!\n\n"
        "I'm your Group Management Bot.\n"
        "Add me to a group with admin permissions to start managing."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message."""
    await update.message.reply_text(
        "🤖 *Group Management Bot*\n\n"
        "*Commands:*\n"
        "/start - Welcome message\n"
        "/help - This message\n"
        "/kick @user - Kick a user\n"
        "/ban @user - Ban a user\n"
        "/mute @user - Mute for 1 hour\n"
        "/warn @user - Warn a user\n"
        "/groupinfo - Group stats\n\n"
        "*How to use:*\n"
        "Reply to a user's message and use the command\n"
        "Or use: /command @username",
        parse_mode='Markdown'
    )

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kick a user."""
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if in group
    if chat.type == "private":
        await update.message.reply_text("❌ This command only works in groups.")
        return
    
    # Check if user is admin
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ Only admins can use this command.")
            return
    except:
        await update.message.reply_text("❌ Error checking permissions.")
        return
    
    # Get target user
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    else:
        text = update.message.text
        parts = text.split()
        if len(parts) > 1:
            username = parts[1].strip()
            if username.startswith('@'):
                username = username[1:]
            try:
                async for member in chat.get_members():
                    if member.user.username and member.user.username.lower() == username.lower():
                        target = member.user
                        break
            except:
                pass
    
    if not target:
        await update.message.reply_text("❌ Reply to a user's message or use: /kick @username")
        return
    
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
        await update.message.reply_text("❌ Failed to kick user. Make sure I have admin permissions.")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user."""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == "private":
        await update.message.reply_text("❌ This command only works in groups.")
        return
    
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ Only admins can use this command.")
            return
    except:
        await update.message.reply_text("❌ Error checking permissions.")
        return
    
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    else:
        text = update.message.text
        parts = text.split()
        if len(parts) > 1:
            username = parts[1].strip()
            if username.startswith('@'):
                username = username[1:]
            try:
                async for member in chat.get_members():
                    if member.user.username and member.user.username.lower() == username.lower():
                        target = member.user
                        break
            except:
                pass
    
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

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mute a user for 1 hour."""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == "private":
        await update.message.reply_text("❌ This command only works in groups.")
        return
    
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ Only admins can use this command.")
            return
    except:
        await update.message.reply_text("❌ Error checking permissions.")
        return
    
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    else:
        text = update.message.text
        parts = text.split()
        if len(parts) > 1:
            username = parts[1].strip()
            if username.startswith('@'):
                username = username[1:]
            try:
                async for member in chat.get_members():
                    if member.user.username and member.user.username.lower() == username.lower():
                        target = member.user
                        break
            except:
                pass
    
    if not target:
        await update.message.reply_text("❌ Reply to a user's message or use: /mute @username")
        return
    
    if target.id == context.bot.id:
        await update.message.reply_text("❌ I can't mute myself!")
        return
    
    try:
        from datetime import datetime, timedelta
        until_date = datetime.now() + timedelta(hours=1)
        await chat.restrict_member(
            target.id,
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            until_date=until_date
        )
        await update.message.reply_text(f"🔇 {target.first_name} has been muted for 1 hour!")
        logger.info(f"User {target.id} muted in {chat.id} by {user.id}")
    except Exception as e:
        logger.error(f"Mute error: {e}")
        await update.message.reply_text("❌ Failed to mute user.")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Warn a user."""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == "private":
        await update.message.reply_text("❌ This command only works in groups.")
        return
    
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ Only admins can use this command.")
            return
    except:
        await update.message.reply_text("❌ Error checking permissions.")
        return
    
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    else:
        text = update.message.text
        parts = text.split()
        if len(parts) > 1:
            username = parts[1].strip()
            if username.startswith('@'):
                username = username[1:]
            try:
                async for member in chat.get_members():
                    if member.user.username and member.user.username.lower() == username.lower():
                        target = member.user
                        break
            except:
                pass
    
    if not target:
        await update.message.reply_text("❌ Reply to a user's message or use: /warn @username")
        return
    
    if target.id == context.bot.id:
        await update.message.reply_text("❌ I can't warn myself!")
        return
    
    # Simple warning counter using context
    if not hasattr(context.bot_data, 'warns'):
        context.bot_data['warns'] = {}
    
    user_id = target.id
    if user_id not in context.bot_data['warns']:
        context.bot_data['warns'][user_id] = 0
    context.bot_data['warns'][user_id] += 1
    
    warn_count = context.bot_data['warns'][user_id]
    
    await update.message.reply_text(
        f"⚠️ {target.first_name} has been warned! (Warning {warn_count}/3)"
    )
    
    # Auto-mute after 3 warnings
    if warn_count >= 3:
        try:
            from datetime import datetime, timedelta
            until_date = datetime.now() + timedelta(hours=1)
            await chat.restrict_member(
                user_id,
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_polls=False,
                can_send_other_messages=False,
                until_date=until_date
            )
            await update.message.reply_text(
                f"🔇 {target.first_name} has been muted for 1 hour (3 warnings reached)!"
            )
            context.bot_data['warns'][user_id] = 0
            logger.info(f"User {user_id} auto-muted after 3 warnings in {chat.id}")
        except Exception as e:
            logger.error(f"Auto-mute error: {e}")

async def groupinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get group info."""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == "private":
        await update.message.reply_text("❌ This command only works in groups.")
        return
    
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ Only admins can use this command.")
            return
    except:
        await update.message.reply_text("❌ Error checking permissions.")
        return
    
    try:
        admins = await chat.get_administrators()
        admin_names = [f"👑 {admin.user.first_name}" for admin in admins[:10]]
        admin_list = "\n".join(admin_names) if admin_names else "No admins found"
        
        bot_info = await context.bot.get_me()
        
        await update.message.reply_text(
            f"📊 *Group Info*\n\n"
            f"📌 Name: {chat.title}\n"
            f"🆔 ID: {chat.id}\n"
            f"👑 Admins: {len(admins)}\n"
            f"🤖 Bot: @{bot_info.username}\n\n"
            f"*Admins:*\n{admin_list}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Groupinfo error: {e}")
        await update.message.reply_text("❌ Failed to get group info.")

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
        logger.error("Add it in Railway: Variables → TELEGRAM_BOT_TOKEN")
        return

    # Start health server
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    # Create bot
    app = Application.builder().token(token).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("groupinfo", groupinfo))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    # Start
    logger.info("🚀 Starting Group Management Bot...")
    logger.info("✅ Bot is running! Send /start on Telegram.")
    
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise

if __name__ == "__main__":
    main()
