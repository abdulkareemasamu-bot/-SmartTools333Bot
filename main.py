import os
import io
import logging
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Simple HTTP Server for Railway ---
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

# --- Bot Functions ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message."""
    logger.info(f"Received /start from {update.effective_user.username}")
    await update.message.reply_text(
        "👋 *Hello! I'm ShrinkPicBot!*\n\n"
        "Send me an image as a *FILE* with a target size in KB in the caption.\n\n"
        "Example: Send an image with caption `250` to compress it under 250 KB.",
        parse_mode='Markdown'
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image documents."""
    document = update.message.document
    caption = update.message.caption
    
    logger.info(f"Received document: {document.file_name}, caption: {caption}")
    
    # Check if it's an image
    if not document.mime_type or not document.mime_type.startswith('image/'):
        await update.message.reply_text("❌ Please send an image file.")
        return

    # Check caption
    if not caption or not caption.strip().isdigit():
        await update.message.reply_text(
            "⚠️ Please provide a target size in KB in the caption.\n"
            "Example: Send an image with caption `250`"
        )
        return

    target_size_kb = int(caption.strip())
    
    if target_size_kb < 10:
        await update.message.reply_text("⚠️ Target size must be at least 10 KB.")
        return

    await update.message.reply_text(f"🔄 Compressing to under {target_size_kb} KB...")
    
    try:
        # Download file
        file = await document.get_file()
        image_bytes = await file.download_as_bytearray()
        
        # Compress
        img = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB
        if img.mode in ('RGBA', 'LA'):
            img = img.convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        output = io.BytesIO()
        quality = 95
        
        while quality >= 5:
            output.seek(0)
            output.truncate(0)
            img.save(output, format='JPEG', quality=quality, optimize=True)
            if output.tell() / 1024 <= target_size_kb:
                break
            quality -= 10
        
        output.seek(0)
        
        # Send back
        await update.message.reply_document(
            document=output,
            filename=f"compressed_{document.file_name or 'image.jpg'}",
            caption=f"✅ Compressed! Size: {len(output.getvalue()) / 1024:.1f} KB"
        )
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos sent as photos."""
    await update.message.reply_text(
        "📸 Please send the image as a *FILE* (not as a photo).\n\n"
        "Tap 📎 → Select 'File' → Choose your image",
        parse_mode='Markdown'
    )

# --- Main ---
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
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Start
    logger.info("🚀 Starting bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
