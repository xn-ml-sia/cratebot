import os
import logging
import asyncio
import json
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from src.session_manager import SessionManager
from src.exporter import CSVExporter

load_dotenv()

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VinylBot")

try:
    from src.vision_gatekeeper import VisionGatekeeper
    from src.discogs_engine import DiscogsEngine
except ImportError:
    from vision_gatekeeper import VisionGatekeeper
    from discogs_engine import DiscogsEngine

class VinylBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment.")
            
        self.vision = VisionGatekeeper(os.getenv("OPENROUTER_API_KEY"))
        self.discogs = DiscogsEngine()
        self.session = SessionManager()
        self.exporter = CSVExporter()
        
        self.app = ApplicationBuilder().token(self.token).build()
        self.app.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
        self.app.add_handler(CommandHandler("export", self.handle_export))
        self.app.add_handler(CommandHandler("clear", self.handle_clear))

    async def handle_export(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Triggers the CSV export process."""
        chat_id = update.effective_chat.id
        await update.message.reply_text("📊 Generating your export...")
        
        try:
            records = self.session.get_all_records()
            if not records:
                await update.message.reply_text("❌ No records found in the current session to export.")
                return

            filepath = self.exporter.export_session(records)
            
            with open(filepath, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=os.path.basename(filepath),
                    caption=f"✅ Export complete. {len(records)} items included."
                )
        except Exception as e:
            logger.error(f"Export Error: {e}")
            await update.message.reply_text(f"❌ Export failed: {e}")

    async def handle_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Clears the session history."""
        try:
            self.session.clear_history()
            await update.message.reply_text("🧹 Session history cleared.")
        except Exception as e:
            await update.message.reply_text(f"❌ Error clearing history: {e}")

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
                f"You are an expert vinyl record investor and grading specialist. "
                f"Analyze this release: {artist} - {title} ({year}). "
                f"Market Data: Lowest Price ${price:.2f}, "
                f"Available Listings: {available}. "
                f"Visual Analysis: The user has provided a photo of the item. "
                f"Return a JSON object with the following keys:\n"
                f"1. 'verdict': 'BUY', 'HOLD', or 'SKIP'.\n"
                f"2. 'reason': A concise 1-sentence justification.\n"
                f"3. 'media_condition': A valid Discogs condition (e.g., 'Mint', 'Near Mint', 'Very Good Plus', 'Very Good', 'Good Plus', 'Good', 'Fair', 'Poor'). Base this on the visual quality of the photo.\n"
                f"4. 'sleeve_condition': A valid Discogs condition for the sleeve.\n"
                f"Return ONLY the JSON object."
            )
            
            verdict_data = self.vision.ask_reasoning(reasoning_prompt)
            
            if "error" in verdict_data:
                raise Exception(f"Reasoning Error: {verdict_data['error']}")

            logger.debug(f"Reasoning Success: {verdict_data}")
            
            verdict = verdict_data.get('verdict', 'HOLD')
            reason = verdict_data.get('reason', 'No reason provided.')
            media_cond = verdict_data.get('media_condition', 'Near Mint')
            sleeve_cond = verdict_data.get('sleeve_condition', 'Near Mint')
            
            final_verdict = (
                f"⚖️ **Verdict: {verdict}**\n"
                f"{reason}"
            )
            
            await status_msg.edit_text(
                f"💿 {artist} — {title}\n\n"
                f"{market_snapshot}\n\n"
                f"{final_verdict}"
            )

            # 4. Persistence Stage (NEW)
            self.session.add_record(
                release_id=discogs_data.get('id'),
                artist=artist,
                title=title,
                year=year,
                price=price,
                available=available,
                verdict=verdict,
                reason=reason,
                media_condition=media_cond,
                sleeve_condition=sleeve_cond
            )
            logger.info(f"Successfully recorded: {artist} - {title} (ID: {discogs_data.get('id')})")

        except Exception as e:

            logger.error(f"Pipeline Failure: {error_msg}")
            await status_msg.edit_text(f"❌ Error: {error_msg}")

    def run(self):
        logger.info("Bot is starting...")
        self.app.run_polling()

if __name__ == "__main__":
    bot = VinylBot()
    bot.run()
