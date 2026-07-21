import os
import logging
import sys

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

logger.info("🚀 Bot is starting...")

try:
    from telegram import Update, ChatMember
    from telegram.ext import Application, CommandHandler, ContextTypes
    logger.info("✅ Imports successful")
except Exception as e:
    logger.error(f"❌ Import error: {e}")
    sys.exit(1)

# Get token
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN not set!")
    logger.error("Please add it in Railway: Variables → TELEGRAM_BOT_TOKEN")
    sys.exit(1)

logger.info("✅ Token found")

# --- Helper Functions ---
async def is_admin(chat, user_id):
    try:
        member = await chat.get_member(user_id)
        return member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except:
        return False

async def get_target_user(update):
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
    logger.info(f"Start command from {update.effective_user.username or update.effective_user.first_name}")
    await update.message.reply_text(
        f"👋 Hello! I'm working!\n\n"
        "Commands:\n"
        "/kick @user - Kick user\n"
        "/ban @user - Ban user\n"
        "/mute @user - Mute user (1 hour)\n"
        "/warn @user - Warn user (3 = mute)\n"
        "/unban @user - Unban user\n"
        "/info - Group info"
    )

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        logger.info(f"Muted {target.id} by {user.id}")
    except Exception as e:
        logger.error(f"Mute error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    if not hasattr(context.bot_data, 'warns'):
        context.bot_data['warns'] = {}
    
    user_id = target.id
    context.bot_data['warns'][user_id] = context.bot_data['warns'].get(user_id, 0) + 1
    warn_count = context.bot_data['warns'][user_id]
    
    await update.message.reply_text(f"⚠️ {target.first_name} warned! ({warn_count}/3)")
    
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
            await update.message.reply_text(f"🔇 {target.first_name} auto-muted (3 warnings)!")
            context.bot_data['warns'][user_id] = 0
        except Exception as e:
            logger.error(f"Auto-mute error: {e}")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")

# --- Error Handler ---
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error: {context.error}")

# --- Main Function ---
def main():
    logger.info("🚀 Creating application...")
    
    try:
        app = Application.builder().token(TOKEN).build()
        logger.info("✅ Application created")
    except Exception as e:
        logger.error(f"❌ Failed to create application: {e}")
        return
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("info", info))
    
    app.add_error_handler(error_handler)
    
    logger.info("🚀 Starting polling...")
    logger.info("✅ Bot is running! Send /start on Telegram")
    
    try:
        app.run_polling()
    except Exception as e:
        logger.error(f"❌ Polling error: {e}")
        raise

if __name__ == "__main__":
    try:
        logger.info("🎯 Bot started")
        main()
    except Exception as e:
        logger.error(f"💥 FATAL ERROR: {e}")
        logger.error("Bot crashed!")
        sys.exit(1)
