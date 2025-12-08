# PayLog AI Bot - Back4App Deployment Guide

This guide explains how to deploy your PayLog AI Telegram Bot on Back4App Containers.

## Features Overview

### Smart Notifications
- **Budget Alerts**: "You're 80% through monthly budget", "Budget exceeded!"
- **Weekly Summaries**: AI-generated weekly spending summaries with comparisons
- **Goal Tracking**: Progress bars, milestone notifications, "₹5000 more to your ₹50k goal"
- **Anomaly Detection**: "This ₹5000 is 5x your average spending"

### Context-Aware Parsing
- **"same place"** → AI remembers your last merchant
- **"usual amount"** → AI knows your typical spending per category
- **"morning coffee"** → AI recognizes category (food) + typical amount (~₹50-100)
- **Relative dates**: "yesterday", "2 days ago", "last week"

### Natural Language Queries
- "How much did I spend on food last week?"
- "Am I spending more than last month?"
- "Where can I cut costs?"
- "What's my financial health?"
- AI responds conversationally with real data

### Wallet System
- **Dual wallets**: Total Stack (savings) + Wallet (daily spending)
- **Transfers**: "Transfer 1000 from total to wallet"
- **Balance tracking** with burn rate calculations

### Lending Management
- **Full payments**: "John returned 5000"
- **Partial payments**: "Received 500 from John" (when he owes 2000)
- Automatic remaining balance tracking
- Pending loan reminders

### Financial Health Score
- **0-100 score** calculated daily
- Factors: savings rate, budget adherence, spending trend, goal progress
- Historical tracking: "Your score dropped 15 points - here's why..."

### Predictive Analytics
- **Runway prediction**: "You'll run out of money by Dec 25"
- **Month-end forecast**: Predict total monthly spending
- **Budget suggestions**: "Cut ₹2000 from dining out"

---

## Prerequisites

1. A Back4App account (https://www.back4app.com/)
2. Your bot's environment variables ready:
   - `BOT_TOKEN` - Telegram Bot Token from @BotFather
   - `GOOGLE_SHEETS_CREDS` - Google Service Account JSON (stringified)
   - `SPREADSHEET_ID` - Your Google Spreadsheet ID
   - `GOOGLE_AI_API_KEY` (optional) - Google AI Studio API key
   - `GROQ_API_KEY` (optional) - Groq API key as backup

## Step 1: Dockerfile (Already Created)

The `Dockerfile` is already in your project:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .

EXPOSE 8000

CMD ["python", "main.py"]
```

## Step 2: Push to GitHub

```bash
git init
git add .
git commit -m "PayLog AI Bot v2.5"
git remote add origin https://github.com/YOUR_USERNAME/paylog-ai-bot.git
git push -u origin main
```

## Step 3: Deploy on Back4App

### Using Back4App Containers (Recommended)

1. Go to https://www.back4app.com/ and log in
2. Click **"Build new app"** → Select **"Containers"**
3. Connect your GitHub account
4. Select your repository
5. Configure the deployment:
   - **Name**: paylog-ai-bot
   - **Branch**: main
   - **Root Directory**: /
   - **Dockerfile Path**: ./Dockerfile

6. **Add Environment Variables:**
   
   | Variable | Value |
   |----------|-------|
   | BOT_TOKEN | your_telegram_bot_token |
   | GOOGLE_SHEETS_CREDS | {"type":"service_account",...} |
   | SPREADSHEET_ID | your_spreadsheet_id |
   | GOOGLE_AI_API_KEY | your_google_ai_key |
   | PORT | 8000 |

7. Click **"Deploy"**

## Step 4: Set Telegram Webhook (For Production)

For production, use webhooks instead of polling:

1. Get your Back4App container URL (e.g., `https://your-app.b4a.run`)

2. Modify `main.py` - replace the `main()` function:

```python
def main():
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    WEBHOOK_URL = os.getenv('WEBHOOK_URL')
    
    if WEBHOOK_URL:
        logger.info(f"Starting PayLog AI Bot in webhook mode...")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
        )
    else:
        logger.info("Starting PayLog AI Bot in polling mode...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
```

3. Add `WEBHOOK_URL` environment variable in Back4App

## Step 5: Verify Deployment

1. Check Back4App logs for any errors
2. Send `/start` to your Telegram bot
3. Test features:
   - "Spent 500 on groceries at DMart"
   - "Transfer 1000 from total to wallet"
   - "How much did I spend last week?"
   - "What's my financial health?"

## Environment Variables Summary

| Variable | Required | Description |
|----------|----------|-------------|
| BOT_TOKEN | Yes | Telegram Bot Token |
| GOOGLE_SHEETS_CREDS | Yes | Google Service Account JSON |
| SPREADSHEET_ID | Yes | Google Spreadsheet ID |
| GOOGLE_AI_API_KEY | No | Google AI Studio key (primary) |
| GROQ_API_KEY | No | Groq API key (backup) |
| OPENROUTER_API_KEY | No | OpenRouter key (fallback) |
| PORT | No | Server port (default: 8000) |
| WEBHOOK_URL | No | Full URL for webhook mode |

## Google Sheets Setup

1. Create a new Google Spreadsheet
2. Copy the Spreadsheet ID from the URL
3. Create a Service Account in Google Cloud Console
4. Download the JSON credentials
5. Share the spreadsheet with the service account email
6. Stringify the JSON and add as `GOOGLE_SHEETS_CREDS`

The bot will automatically create two sheets:
- `transactions` - All income/expense records
- `lending` - All lending records

## Troubleshooting

### Bot not responding
- Check Back4App logs for errors
- Verify BOT_TOKEN is correct
- Ensure the container is running

### Google Sheets not working
- Verify GOOGLE_SHEETS_CREDS is properly escaped JSON
- Check SPREADSHEET_ID is correct
- Ensure the service account has edit access to the spreadsheet

### AI features not working
- Check that at least one AI API key is set
- Review logs for API errors
- The bot uses fallback parsing if all AI providers fail

### Webhook issues
- Ensure WEBHOOK_URL includes https://
- Check that the URL is publicly accessible
- Verify the container port matches the exposed port

## Scaling

Back4App Containers auto-scale based on demand:
1. Enable auto-scaling in container settings
2. Use webhook mode (more efficient than polling)
3. Consider Redis for multi-instance session storage

## Cost Considerations

- **Back4App free tier**: 1 container with limited resources
- **Paid plans**: More containers, better performance
- **Google AI Studio**: Free tier available (15 RPM)
- **Groq**: Free tier with rate limits
- Telegram bots typically have low resource needs
