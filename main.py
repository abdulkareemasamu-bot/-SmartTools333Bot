import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, ChatMember
from telegram.ext import Application, CommandHandler, ContextTypes

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
    logger.error("Add it in Railway: Variables → TELEGRAM_BOT_TOKEN")
    exit(1)

logger.info("✅ Bot starting...")

# --- Helper Functions ---
async def is_admin(chat, user_id):
    try:
        member = await chat.get_member(user_id)
        return member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except:
        return False

async def get_target_user(update):
    """Get target user from reply or command."""
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    
    text = update.message.text
    parts = text.split()
    if len(parts) > 1:
        username = parts[1].strip()
        if username.startswith('@'):
            username = username[1:]
        
        try:
            async for member in update.effective_chat.get_members():
                if member.user.username and member.user.username.lower() == username.lower():
                    return member.user
        except:
            pass
    
    return None

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command."""
    user = update.effective_user
    logger.info(f"Start from {user.username or user.first_name}")
    
    await update.message.reply_text(
        f"👋 *Hello {user.first_name}!*\n\n"
        "I'm a Group Management Bot.\n"
        "Add me to a group with Admin permissions.\n\n"
        "*Commands:*\n"
        "/start - Welcome\n"
        "/help - Help\n"
        "/kick @user - Kick user\n"
        "/ban @user - Ban user\n"
        "/mute @user - Mute user (1 hour)\n"
        "/warn @user - Warn user (3 = mute)\n"
        "/unban @user - Unban user\n"
        "/info - Group info\n\n"
        "*Usage:*\n"
        "Reply to a user's message with the command\n"
        "Or: /kick @username",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command."""
    await update.message.reply_text(
        "🤖 *Group Management Bot Help*\n\n"
        "*Admin Commands:*\n"
        "/kick @user - Kick user\n"
        "/ban @user - Ban user\n"
        "/mute @user - Mute for 1 hour\n"
        "/warn @user - Warn user (3 = mute)\n"
        "/unban @user - Unban user\n"
        "/info - Group info\n\n"
        "*How to use:*\n"
        "1. Reply to user's message with command\n"
        "2. Or use: /command @username\n\n"
        "*Note:*\n"
        "Bot must be admin to perform actions",
        parse_mode='Markdown'
    )

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kick user."""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == "private":
        await update.message.reply_text("❌ This command only works in groups.")
        return
    
    if not await is_admin(chat, user.id):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    
    target = await get_target_user(update)
    if not target:
        await update.message.reply_text("❌ Reply to a user or use: /kick @username")
        return
    
    if target.id == context.bot.id:
        await update.message.reply_text("❌ I can't kick myself!")
        return
    
    try:
        await chat.ban_member(target.id)
        await chat.unban_member(target.id)
        await update.message.reply_text(f"✅ {target.first_name} kicked!")
        logger.info(f"Kicked {target.id} by {user.id}")
    except Exception as e:
        logger.error(f"Kick error: {e}")
        await update.message.reply_text("❌ Failed to kick. Make me admin!")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban user."""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == "private":
        await update.message.reply_text("❌ This command only works in groups.")
        return
    
    if not await is_admin(chat, user.id):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    
    target = await get_target_user(update)
    if not target:
        await update.message.reply_text("❌ Reply to a user or use: /ban @username")
        return
    
    if target.id == context.bot.id:
        await update.message.reply_text("❌ I can't ban myself!")
        return
    
    try:
        await chat.ban_member(target.id)
        await update.message.reply_text(f"✅ {target.first_name} banned!")
        logger.info(f"Banned {target.id} by {user.id}")
    except Exception as e:
        logger.error(f"Ban error: {e}")
        await update.message.reply_text("❌ Failed to ban. Make me admin!")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban user."""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == "private":
        await update.message.reply_text("❌ This command only works in groups.")
        return
    
    if not await is_admin(chat, user.id):
        await update.message.reply_text("❌ Only admins can use this command.")
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
        await update.message.reply_text(f"✅ @{username} unbanned!")
        logger.info(f"Unbanned @{username} by {user.id}")
    except Exception as e:
        logger.error(f"Unban error: {e}")
        await update.message.reply_text("❌ Failed to unban.")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mute user for 1 hour."""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == "private":
        await update.message.reply_text("❌ This command only works in groups.")
        return
    
    if not await is_admin(chat, user.id):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    
    target = await get_target_user(update)
    if not target:
        await update.message.reply_text("❌ Reply to a user or use: /mute @username")
        return
    
    if target.id == context.bot.id:
        await update.message.reply_text("❌ I can't mute myself!")
        return
    
    try:
        until = datetime.now() + timedelta(hours=1)
        
        await chat.restrict_member(
            target.id,
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            until_date=until
        )
        await update.message.reply_text(f"🔇 {target.first_name} muted for 1 hour!")
        logger.info(f"Muted {target.id} by {user.id}")
    except Exception as e:
        logger.error(f"Mute error: {e}")
        await update.message.reply_text("❌ Failed to mute. Make me admin!")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Warn user."""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == "private":
        await update.message.reply_text("❌ This command only works in groups.")
        return
    
    if not await is_admin(chat, user.id):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    
    target = await get_target_user(update)
    if not target:
        await update.message.reply_text("❌ Reply to a user or use: /warn @username")
        return
    
    if target.id == context.bot.id:
        await update.message.reply_text("❌ I can't warn myself!")
        return
    
    # Get or create warn count
    if not hasattr(context.bot_data, 'warns'):
        context.bot_data['warns'] = {}
    
    user_id = target.id
    context.bot_data['warns'][user_id] = context.bot_data['warns'].get(user_id, 0) + 1
    warn_count = context.bot_data['warns'][user_id]
    
    await update.message.reply_text(f"⚠️ {target.first_name} warned! ({warn_count}/3)")
    
    # Auto-mute at 3 warnings
    if warn_count >= 3:
        try:
            until = datetime.now() + timedelta(hours=1)
            
            await chat.restrict_member(
                user_id,
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_polls=False,
                can_send_other_messages=False,
                until_date=until
            )
            await update.message.reply_text(f"🔇 {target.first_name} auto-muted (3 warnings)!")
            context.bot_data['warns'][user_id] = 0
            logger.info(f"User {user_id} auto-muted after 3 warnings")
        except Exception as e:
            logger.error(f"Auto-mute error: {e}")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get group info."""
    chat = update.effective_chat
    
    if chat.type == "private":
        await update.message.reply_text("❌ This command only works in groups.")
        return
    
    user = update.effective_user
    if not await is_admin(chat, user.id):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    
    try:
        admins = await chat.get_administrators()
        admin_list = "\n".join([f"👑 {a.user.first_name}" for a in admins[:10]])
        bot = await context.bot.get_me()
        
        await update.message.reply_text(
            f"📊 *Group Info*\n\n"
            f"📌 Name: {chat.title}\n"
            f"🆔 ID: {chat.id}\n"
            f"👑 Admins: {len(admins)}\n"
            f"🤖 Bot: @{bot.username}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Info error: {e}")
        await update.message.reply_text("❌ Failed to get info.")

# --- Error Handler ---
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error: {context.error}")

# --- Main Function ---
async def main():
    logger.info("🚀 Starting bot...")
    
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("info", info))
    
    app.add_error_handler(error_handler)
    
    logger.info("✅ Bot is running! Send /start on Telegram")
    
    # Start polling
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
