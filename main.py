import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN not set!")
    exit(1)

logger.info("✅ Bot starting...")

# --- Commands ---
def start(update: Update, context: CallbackContext):
    """Start command."""
    user = update.effective_user
    logger.info(f"Start from {user.username or user.first_name}")
    update.message.reply_text(
        f"👋 Hello {user.first_name}!\n\n"
        "I'm a Group Management Bot.\n"
        "Add me to a group with Admin permissions.\n\n"
        "Commands:\n"
        "/start - Welcome\n"
        "/help - Help\n"
        "/kick @user - Kick user\n"
        "/ban @user - Ban user\n"
        "/mute @user - Mute for 1 hour\n"
        "/warn @user - Warn user\n"
        "/info - Group info"
    )

def help_command(update: Update, context: CallbackContext):
    """Help command."""
    update.message.reply_text(
        "🤖 Group Management Bot\n\n"
        "Commands:\n"
        "/kick @user - Kick user from group\n"
        "/ban @user - Ban user from group\n"
        "/mute @user - Mute user for 1 hour\n"
        "/warn @user - Warn user (3 = mute)\n"
        "/info - Group information\n\n"
        "Usage: Reply to user's message or use @username"
    )

def kick(update: Update, context: CallbackContext):
    """Kick user."""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == "private":
        update.message.reply_text("❌ This command only works in groups.")
        return
    
    # Check if admin
    try:
        member = chat.get_member(user.id)
        if member.status not in ['administrator', 'creator']:
            update.message.reply_text("❌ Only admins can use this command.")
            return
    except:
        update.message.reply_text("❌ Error checking permissions.")
        return
    
    # Get target
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
                for member in chat.get_members():
                    if member.user.username and member.user.username.lower() == username.lower():
                        target = member.user
                        break
            except:
                pass
    
    if not target:
        update.message.reply_text("❌ Reply to a user or use: /kick @username")
        return
    
    if target.id == context.bot.id:
        update.message.reply_text("❌ I can't kick myself!")
        return
    
    try:
        chat.ban_member(target.id)
        chat.unban_member(target.id)
        update.message.reply_text(f"✅ {target.first_name} has been kicked!")
        logger.info(f"Kicked {target.id}")
    except Exception as e:
        logger.error(f"Kick error: {e}")
        update.message.reply_text("❌ Failed to kick. Make me admin!")

def ban(update: Update, context: CallbackContext):
    """Ban user."""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == "private":
        update.message.reply_text("❌ This command only works in groups.")
        return
    
    try:
        member = chat.get_member(user.id)
        if member.status not in ['administrator', 'creator']:
            update.message.reply_text("❌ Only admins can use this command.")
            return
    except:
        update.message.reply_text("❌ Error checking permissions.")
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
                for member in chat.get_members():
                    if member.user.username and member.user.username.lower() == username.lower():
                        target = member.user
                        break
            except:
                pass
    
    if not target:
        update.message.reply_text("❌ Reply to a user or use: /ban @username")
        return
    
    if target.id == context.bot.id:
        update.message.reply_text("❌ I can't ban myself!")
        return
    
    try:
        chat.ban_member(target.id)
        update.message.reply_text(f"✅ {target.first_name} has been banned!")
        logger.info(f"Banned {target.id}")
    except Exception as e:
        logger.error(f"Ban error: {e}")
        update.message.reply_text("❌ Failed to ban. Make me admin!")

def mute(update: Update, context: CallbackContext):
    """Mute user for 1 hour."""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == "private":
        update.message.reply_text("❌ This command only works in groups.")
        return
    
    try:
        member = chat.get_member(user.id)
        if member.status not in ['administrator', 'creator']:
            update.message.reply_text("❌ Only admins can use this command.")
            return
    except:
        update.message.reply_text("❌ Error checking permissions.")
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
                for member in chat.get_members():
                    if member.user.username and member.user.username.lower() == username.lower():
                        target = member.user
                        break
            except:
                pass
    
    if not target:
        update.message.reply_text("❌ Reply to a user or use: /mute @username")
        return
    
    if target.id == context.bot.id:
        update.message.reply_text("❌ I can't mute myself!")
        return
    
    try:
        from datetime import datetime, timedelta
        until = datetime.now() + timedelta(hours=1)
        chat.restrict_member(
            target.id,
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            until_date=until
        )
        update.message.reply_text(f"🔇 {target.first_name} muted for 1 hour!")
        logger.info(f"Muted {target.id}")
    except Exception as e:
        logger.error(f"Mute error: {e}")
        update.message.reply_text("❌ Failed to mute. Make me admin!")

def warn(update: Update, context: CallbackContext):
    """Warn user."""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == "private":
        update.message.reply_text("❌ This command only works in groups.")
        return
    
    try:
        member = chat.get_member(user.id)
        if member.status not in ['administrator', 'creator']:
            update.message.reply_text("❌ Only admins can use this command.")
            return
    except:
        update.message.reply_text("❌ Error checking permissions.")
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
                for member in chat.get_members():
                    if member.user.username and member.user.username.lower() == username.lower():
                        target = member.user
                        break
            except:
                pass
    
    if not target:
        update.message.reply_text("❌ Reply to a user or use: /warn @username")
        return
    
    if target.id == context.bot.id:
        update.message.reply_text("❌ I can't warn myself!")
        return
    
    # Warn counter
    if not hasattr(context.bot_data, 'warns'):
        context.bot_data['warns'] = {}
    
    user_id = target.id
    context.bot_data['warns'][user_id] = context.bot_data['warns'].get(user_id, 0) + 1
    warn_count = context.bot_data['warns'][user_id]
    
    update.message.reply_text(f"⚠️ {target.first_name} warned! ({warn_count}/3)")
    
    if warn_count >= 3:
        try:
            from datetime import datetime, timedelta
            until = datetime.now() + timedelta(hours=1)
            chat.restrict_member(
                user_id,
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_polls=False,
                can_send_other_messages=False,
                until_date=until
            )
            update.message.reply_text(f"🔇 {target.first_name} auto-muted (3 warnings)!")
            context.bot_data['warns'][user_id] = 0
        except Exception as e:
            logger.error(f"Auto-mute error: {e}")

def info(update: Update, context: CallbackContext):
    """Get group info."""
    chat = update.effective_chat
    
    if chat.type == "private":
        update.message.reply_text("❌ This command only works in groups.")
        return
    
    user = update.effective_user
    try:
        member = chat.get_member(user.id)
        if member.status not in ['administrator', 'creator']:
            update.message.reply_text("❌ Only admins can use this command.")
            return
    except:
        update.message.reply_text("❌ Error checking permissions.")
        return
    
    try:
        admins = chat.get_administrators()
        admin_list = "\n".join([f"👑 {a.user.first_name}" for a in admins[:10]])
        bot = context.bot.get_me()
        
        update.message.reply_text(
            f"📊 *Group Info*\n\n"
            f"📌 Name: {chat.title}\n"
            f"🆔 ID: {chat.id}\n"
            f"👑 Admins: {len(admins)}\n"
            f"🤖 Bot: @{bot.username}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Info error: {e}")
        update.message.reply_text("❌ Failed to get info.")

def error_handler(update, context):
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")

# --- Main ---
def main():
    logger.info("🚀 Starting bot...")
    
    # Create updater
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # Add handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("kick", kick))
    dp.add_handler(CommandHandler("ban", ban))
    dp.add_handler(CommandHandler("mute", mute))
    dp.add_handler(CommandHandler("warn", warn))
    dp.add_handler(CommandHandler("info", info))
    
    dp.add_error_handler(error_handler)
    
    # Start
    logger.info("✅ Bot is running! Send /start")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
