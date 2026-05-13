import os
import logging
import asyncio
import json
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

load_dotenv()

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VinylBot")

try:
    from vision_gatekeeper import VisionGatekeeper
    from discogs_engine import DiscogsEngine
except ImportError:
    from src.vision_gatekeeper import VisionGatekeeper
    from src.discogs_engine import DiscogsEngine

class VinylBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment.")
            
        self.vision = VisionGatekeeper(os.getenv("OPENROUTER_API_KEY"))
        self.discogs = DiscogsEngine()
        
        self.app = ApplicationBuilder().token(self.token).build()
        self.app.add_handler(MessageHandler(filters.PHOTO, self.handle_image))

    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        status_msg = await update.message.reply_text("🔍 Analyzing album cover...")
        logger.debug("Processing new photo upload")

        try:
            # 1. Vision Stage
            photo_file = await update.message.photo[-1].get_file()
            photo_path = f"/tmp/{photo_file.file_id}.jpg"
            await photo_file.download_to_drive(photo_path)
            
            logger.debug("Starting Vision Stage")
            vision_data = self.vision.extract_metadata(photo_path)
            
            if "error" in vision_data:
                raise Exception(f"Vision Error: {vision_data['error']}")
            
            await status_msg.edit_text(f"💿 {vision_data['artist']} — {vision_data['album']}")

            # 2. Discogs Stage
            logger.debug(f"Starting Discogs Stage for {vision_data['artist']} - {vision_data['album']}")
            discogs_data = self.discogs.search_release(vision_data['artist'], vision_data['album'])
            
            if "error" in discogs_data:
                raise Exception(f"Discogs Error: {discogs_data['error']}")
            
            logger.debug(f"Discogs Success: {discogs_data}")
            
            # Using the native Discogs fields
            price = discogs_data.get('current_price', 0.0)
            available = discogs_data.get('available_count', 0)
            artist = discogs_data.get('artist', 'Unknown Artist')
            title = discogs_data.get('title', 'Unknown Title')
            year = discogs_data.get('year', 'Unknown')

            market_snapshot = (
                f"💰 **Market Snapshot:**\n"
                f"• Lowest Price: ${price:.2f}\n"
                f"• For Sale: {available}"
            )
            
            await status_msg.edit_text(f"💿 {artist} — {title}\n\n{market_snapshot}")

            # 3. Reasoning Stage
            logger.debug("Starting Reasoning Stage")
            reasoning_prompt = (
                f"You are an expert vinyl record investor. "
                f"Analyze this release: {artist} - {title} ({year}). "
                f"Market Data: Lowest Price ${price:.2f}, "
                f"Available Listings: {available}. "
                f"Return a JSON object with the keys 'verdict' and 'reason'. "
                f"The verdict must be 'BUY', 'HOLD', or 'SKIP'. "
                f"The reason should be a concise 1-sentence justification."
            )
            
            verdict_data = self.vision.ask_reasoning(reasoning_prompt)
            
            if "error" in verdict_data:
                raise Exception(f"Reasoning Error: {verdict_data['error']}")

            logger.debug(f"Reasoning Success: {verdict_data}")
            
            final_verdict = (
                f"⚖️ **Verdict: {verdict_data['verdict']}**\n"
                f"{verdict_data['reason']}"
            )
            
            await status_msg.edit_text(
                f"💿 {artist} — {title}\n\n"
                f"{market_snapshot}\n\n"
                f"{final_verdict}"
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Pipeline Failure: {error_msg}")
            await status_msg.edit_text(f"❌ Error: {error_msg}")

    def run(self):
        logger.info("Bot is starting...")
        self.app.run_polling()

if __name__ == "__main__":
    bot = VinylBot()
    bot.run()
