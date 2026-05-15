# Second Life, Inc

A specialized tool for managing vinyl catalog data and marketplace intelligence.

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/xn-ml-sia/second-life-inc.git
cd second-life-inc
```

### 2. Environment Setup
We use a Python virtual environment to manage dependencies.

```bash
# Create the virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
The application relies on environment variables for authentication. **Do not commit your `.env` file.**

Create a `.env` file in the root directory:
```bash
touch .env
```

Add the following keys to your `.env` file:
```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Discogs API Configuration
DISCOGS_TOKEN=your_discogs_personal_access_token_here

# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:e2b
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

## 🛠 Tech Stack
- **Language:** Python 3.x
- **Intelligence:** Ollama (Local) / OpenRouter (Cloud)
- **Integrations:** Telegram Bot API, Discogs API
