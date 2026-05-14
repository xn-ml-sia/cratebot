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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
        self.vision = VisionGatekeeper(os.getenv("OPENROUTER_API_KEY"))
        self.discogs = DiscogsEngine()
        self.session = SessionManager()
        self.exporter = CSVExporter()
        self.app = ApplicationBuilder().token(self.token).build()
        self.app.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
        self.app.add_handler(CommandHandler("export", self.handle_export))
        self.app.add_handler(CommandHandler("clear", self.handle_clear))

    async def handle_export(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            records = self.session.get_all_records()
            if not records:
                await update.message.reply_text("❌ No records found.")
                return
            filepath = self.exporter.export_session(records)
            with open(filepath, 'rb') as f:
                await update.message.reply_document(document=f, filename=os.path.basename(filepath), caption=f"✅ Exported {len(records)} items.")
        except Exception as e:
            await update.message.reply_text(f"❌ Export failed: {e}")

    async def handle_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.session.clear_history()
        await update.message.reply_text("🧹 Session cleared.")

    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        status_msg = await update.message.reply_text("🔍 Analyzing...")
        try:
            photo_file = await update.message.photo[-1].get_file()
            photo_path = f"/tmp/{photo_file.file_id}.jpg"
            await photo_file.download_to_drive(photo_path)
            vision_data = self.vision.extract_metadata(photo_path)
            if "error" in vision_data: raise Exception(vision_data['error'])
            
            discogs_data = self.discogs.search_release(vision_data['artist'], vision_data['album'])
            if "error" in discogs_data: raise Exception(discogs_data['error'])
            
            price = discogs_data.get('current_price', 0.0)
            available = discogs_data.get('available_count', 0)
            artist = discogs_data.get('artist', 'Unknown')
            title = discogs_data.get('title', 'Unknown')
            year = discogs_data.get('year', 'Unknown')

            market_snapshot = f"💰 **Market Snapshot:**\n• Lowest Price: ${price:.2f}\n• For Sale: {available}"
            await status_msg.edit_text(f"💿 {artist} — {title}\n\n{market_snapshot}")

            prompt = (
                f"You are an expert vinyl record investor and grading specialist. "
                f"Analyze this release: {artist} - {title} ({year}). "
                f"Market Data: Lowest Price ${price:.2f}, Available: {available}. "
                f"Return ONLY a JSON object with keys: "
                f"'verdict' (BUY/HOLD/SKIP), 'reason' (1 sentence), "
                f"'media_condition' (Discogs term), 'sleeve_condition' (Discogs term)."
            )
            verdict_data = self.vision.ask_reasoning(prompt)
            if "error" in verdict_data: raise Exception(verdict_data['error'])
            
            v = verdict_data.get('verdict', 'HOLD')
            r = verdict_data.get('reason', '')
            mc = verdict_data.get('media_condition', 'Near Mint')
            sc = verdict_data.get('sleeve_condition', 'Near Mint')

            await status_msg.edit_text(f"💿 {artist} — {title}\n\n{market_snapshot}\n\n⚖️ **{v}**\n{r}")
            self.session.add_record(discogs_data.get('id'), artist, title, year, price, available, v, r, mc, sc)
        except Exception as e:
            await status_msg.edit_text(f"❌ Error: {e}")

    def run(self):
        self.app.run_polling()

if __name__ == "__main__":
    VinylBot().run()
