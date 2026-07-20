import os
import io
import logging
import asyncio
import threading
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image
from http.server import HTTPServer, BaseHTTPRequestHandler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Simple HTTP Server for Railway Health Checks ---
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK')
    
    def log_message(self, format, *args):
        return  # Suppress log messages

def run_health_server():
    """Run a simple HTTP server on the PORT environment variable."""
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"✅ Health server running on port {port}")
    server.serve_forever()

# --- Keep-Alive Function ---
async def keep_alive():
    """Keeps the bot active."""
    while True:
        try:
            logger.info("🔄 Keep-alive heartbeat...")
        except Exception as e:
            logger.error(f"Keep-alive error: {e}")
        await asyncio.sleep(300)  # Every 5 minutes

# --- Helper Function for Compression ---
async def compress_image(input_image_bytes, target_size_kb):
    """Compresses an image to be under a target size in KB."""
    try:
        img = Image.open(io.BytesIO(input_image_bytes))
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            img = img.convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        output = io.BytesIO()
        quality = 95
        min_quality = 5
        
        # Check if image is already under target size
        if len(input_image_bytes) / 1024 <= target_size_kb:
            return io.BytesIO(input_image_bytes)
        
        # Binary search for the best quality setting
        while min_quality <= quality:
            output.seek(0)
            output.truncate(0)
            img.save(output, format='JPEG', quality=quality, optimize=True)
            
            if output.tell() / 1024 <= target_size_kb:
                break
            quality -= 5
        else:
            output.seek(0)
            output.truncate(0)
            img.save(output, format='JPEG', quality=5, optimize=True)

        output.seek(0)
        return output
        
    except Exception as e:
        logger.error(f"Compression error: {e}")
        raise

# --- Bot Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message."""
    await update.message.reply_text(
        "👋 *Hello! I'm ShrinkPicBot!*\n\n"
        "I can compress your images to any size you want.\n\n"
        "📤 *How to use me:*\n"
        "1. Send me a photo as a *FILE* (📎 attachment menu → select 'File')\n"
        "2. In the caption, type the maximum size in *KB*\n\n"
        "📝 *Example:*\n"
        "Send an image with caption `250` to compress it under 250 KB.\n\n"
        "⚡ *Pro tip:* Send images as files to avoid Telegram's compression!",
        parse_mode='Markdown'
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles documents (images sent as files)."""
    document = update.message.document
    caption = update.message.caption

    # Check if it's an image
    if not document.mime_type or not document.mime_type.startswith('image/'):
        await update.message.reply_text("❌ Please send an *image* file.", parse_mode='Markdown')
        return

    # Check if a target size is provided
    if not caption or not caption.strip().isdigit():
        await update.message.reply_text(
            "⚠️ Please provide a target size in *KB* in the caption.\n\n"
            "📝 Example: Send an image with the caption `250`",
            parse_mode='Markdown'
        )
        return

    target_size_kb = int(caption.strip())
    
    # Validate target size
    if target_size_kb < 10:
        await update.message.reply_text("⚠️ Target size must be at least *10 KB*.", parse_mode='Markdown')
        return
    
    if target_size_kb > 10000:
        await update.message.reply_text("⚠️ Target size must be less than *10,000 KB* (10 MB).", parse_mode='Markdown')
        return

    status_msg = await update.message.reply_text(f"🔄 Compressing image to under *{target_size_kb} KB*...", parse_mode='Markdown')
    
    try:
        # Download the image file
        file = await document.get_file()
        image_bytes = await file.download_as_bytearray()

        # Compress the image
        compressed_image = await compress_image(image_bytes, target_size_kb)
        
        # Generate a filename
        original_name = document.file_name or "image.jpg"
        name_parts = original_name.rsplit('.', 1)
        new_name = f"compressed_{name_parts[0]}.jpg" if len(name_parts) > 1 else f"compressed_{original_name}.jpg"
        
        # Get compressed size
        compressed_size = len(compressed_image.getvalue()) / 1024
        
        # Send the compressed image back
        await update.message.reply_document(
            document=compressed_image,
            filename=new_name,
            caption=f"✅ *Compressed successfully!*\n\n📊 Size: *{compressed_size:.1f} KB* (Target: {target_size_kb} KB)",
            parse_mode='Markdown'
        )
        
        # Delete the status message
        await status_msg.delete()
        
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        await status_msg.edit_text(f"❌ Sorry, I couldn't compress that image. Please try again.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles photos sent without the file option."""
    await update.message.reply_text(
        "📸 *Oops!*\n\n"
        "You sent a photo as a 'Photo'.\n"
        "To compress images accurately, please send it as a *FILE*:\n\n"
        "📎 Tap the attachment icon → Select 'File' → Choose your image\n\n"
        "Then add your target size in the caption.",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message."""
    await update.message.reply_text(
        "❓ *Help Center*\n\n"
        "📤 *How to send an image as a file:*\n"
        "1. Tap the 📎 attachment icon\n"
        "2. Select 'File' (not Gallery/Camera)\n"
        "3. Choose your image from your device\n"
        "4. In the caption, type your target size in KB\n\n"
        "📝 *Example caption:* `150`\n\n"
        "🛠 *Commands:*\n"
        "/start - Show welcome message\n"
        "/help - Show this help message\n"
        "/stats - Show bot statistics",
        parse_mode='Markdown'
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics."""
    uptime = datetime.now() - context.bot_data.get('start_time', datetime.now())
    await update.message.reply_text(
        f"📊 *Bot Statistics*\n\n"
        f"⏰ Uptime: {str(uptime).split('.')[0]}\n"
        f"🔄 Status: Active\n"
        f"📦 Memory: Running",
        parse_mode='Markdown'
    )

# --- Error Handler ---
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")

# --- Main Function ---
def main():
    # Get the bot token from environment variables
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ No TELEGRAM_BOT_TOKEN found in environment variables.")
        logger.error("Please add it in Railway: Variables → TELEGRAM_BOT_TOKEN")
        return

    # Start health server in a separate thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    logger.info("🔄 Health server started")

    # Create the Application
    app = ApplicationBuilder().token(token).build()

    # Store start time
    app.bot_data['start_time'] = datetime.now()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    
    # Register message handlers
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Register error handler
    app.add_error_handler(error_handler)

    # Start the keep-alive task
    loop = asyncio.get_event_loop()
    loop.create_task(keep_alive())

    # Start the bot using long polling
    logger.info("🚀 Starting ShrinkPicBot...")
    logger.info("✅ Bot is active and waiting for messages!")
    
    try:
        # Run the bot
        app.run_polling()
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        raise

if __name__ == "__main__":
    main()
