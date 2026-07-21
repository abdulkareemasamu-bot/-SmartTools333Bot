import os
import logging
from telegram import Update, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Bot Token ---
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN not set!")
    exit(1)

# --- Helper Functions ---
async def is_admin(chat, user_id):
    """Check if user is admin in the chat."""
    try:
        member = await chat.get_member(user_id)
        return member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except:
        return False

async def get_target_user(update):
    """Get target user from reply or command."""
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
        "/kick - Kick user\n"
        "/ban - Ban user\n"
        "/mute - Mute user (1 hour)\n"
        "/warn - Warn user (3 = mute)\n"
        "/unban - Unban user\n"
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
        await update.message.reply_text(f"✅ {target.first_name} has been kicked!")
        logger.info(f"User {target.id} kicked by {user.id} in {chat.id}")
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
        await update.message.reply_text(f"✅ {target.first_name} has been banned!")
        logger.info(f"User {target.id} banned by {user.id} in {chat.id}")
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
        await update.message.reply_text(f"✅ @{username} has been unbanned!")
        logger.info(f"User @{username} unbanned by {user.id} in {chat.id}")
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
        from datetime import datetime, timedelta
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
        logger.info(f"User {target.id} muted by {user.id} in {chat.id}")
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
            from datetime import datetime, timedelta
            until = datetime.now() + timedelta(hours=1)
            
            await chat.restrict_member(
                user_id,
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_polls=False,
                can_send_other_messages=False,
                until_date=until
            )
            await update.message.reply_text(f"🔇 {target.first_name} auto-muted for 1 hour (3 warnings)!")
            context.bot_data['warns'][user_id] = 0
            logger.info(f"User {user_id} auto-muted after 3 warnings in {chat.id}")
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
            f"🤖 Bot: @{bot.username}\n\n"
            f"*Admins:*\n{admin_list}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Info error: {e}")
        await update.message.reply_text("❌ Failed to get info.")

# --- Main Function ---
def main():
    logger.info("🚀 Starting Group Management Bot...")
    logger.info("✅ Bot is running!")
    
    # Create app
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
    
    # Start polling
    app.run_polling()

if __name__ == "__main__":
    main()
