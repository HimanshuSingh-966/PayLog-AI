# PayLog AI Bot v2.5

An intelligent Telegram expense tracking bot with AI-powered features.

## Features

### Core Features
- Dual wallet system (Total Stack + Wallet) with transfers
- Smart lending with partial payment tracking
- Natural language transaction input
- Google Sheets integration for data storage

### AI-Powered Features
- **Context-aware parsing**: "same place", "usual amount", "morning coffee"
- **Natural language queries**: "How much did I spend on food last week?"
- **Financial health scoring**: 0-100 score with detailed breakdown
- **Predictive analytics**: Budget depletion forecasts
- **Smart notifications**: Budget alerts, weekly summaries, goal tracking
- **Anomaly detection**: Flags unusual spending patterns

### Supported AI Providers
1. Google AI Studio (Gemini) - Primary
2. Groq (LLaMA) - Backup
3. OpenRouter - Fallback

## Quick Start

1. Set environment variables:
   ```
   BOT_TOKEN=your_telegram_bot_token
   GOOGLE_SHEETS_CREDS={"type":"service_account",...}
   SPREADSHEET_ID=your_spreadsheet_id
   GOOGLE_AI_API_KEY=your_google_ai_key
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the bot:
   ```bash
   python main.py
   ```

## Commands

- `/start` - Initialize the bot and show menu

## Natural Language Examples

- "Spent 500 on groceries at DMart"
- "Transfer 1000 from total to wallet"
- "Lent 5000 to John"
- "Received 2000 from John"
- "How much did I spend last week?"
- "What's my financial health?"
- "Where can I cut costs?"

## Deployment

See [DEPLOYMENT_BACK4APP.md](DEPLOYMENT_BACK4APP.md) for Back4App deployment instructions.

## File Structure

```
paylog-ai-bot/
├── main.py           # Main Telegram bot
├── ai_service.py     # Multi-agent AI service
├── analytics.py      # Analytics & predictions
├── user_prefs.py     # User preferences & goals
├── requirements.txt  # Python dependencies
├── Dockerfile        # Container deployment
└── README.md
```
