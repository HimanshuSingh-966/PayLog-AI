# PayLog AI Bot - Back4App Deployment Guide

This guide explains how to deploy your PayLog AI Telegram Bot on Back4App Containers.

## Prerequisites

1. A Back4App account (https://www.back4app.com/)
2. Your bot's environment variables ready:
   - `BOT_TOKEN` - Telegram Bot Token from @BotFather
   - `GOOGLE_SHEETS_CREDS` - Google Service Account JSON (stringified)
   - `SPREADSHEET_ID` - Your Google Spreadsheet ID
   - `GOOGLE_AI_API_KEY` (optional) - Google AI Studio API key
   - `GROQ_API_KEY` (optional) - Groq API key as backup

## Step 1: Create Required Files

### Dockerfile

Create a `Dockerfile` in your project root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py .

# Expose port for health checks
EXPOSE 8000

# Run the bot
CMD ["python", "main.py"]
```

### Procfile (Alternative to Dockerfile)

If you prefer using a Procfile:

```
worker: python main.py
```

## Step 2: Prepare Your Repository

1. Push your code to GitHub:
```bash
git init
git add .
git commit -m "PayLog AI Bot"
git remote add origin https://github.com/YOUR_USERNAME/paylog-ai-bot.git
git push -u origin main
```

## Step 3: Deploy on Back4App

### Option A: Using Back4App Containers (Recommended)

1. Go to https://www.back4app.com/ and log in
2. Click "Build new app" → Select "Containers"
3. Connect your GitHub account
4. Select your repository
5. Configure the deployment:
   - **Name**: paylog-ai-bot
   - **Branch**: main
   - **Root Directory**: / (or where your files are)
   - **Dockerfile Path**: ./Dockerfile

6. Add Environment Variables:
   Click "Environment Variables" and add:
   ```
   BOT_TOKEN=your_telegram_bot_token
   GOOGLE_SHEETS_CREDS={"type":"service_account",...}
   SPREADSHEET_ID=your_spreadsheet_id
   GOOGLE_AI_API_KEY=your_google_ai_key
   PORT=8000
   ```

7. Click "Deploy"

### Option B: Using Back4App Cloud Code

1. Create a new Back4App app
2. Go to Server Settings → Cloud Code
3. Upload your Python files
4. Configure cloud functions to call your bot logic

## Step 4: Set Telegram Webhook (For Production)

After deployment, update your bot to use webhooks instead of polling for better performance:

1. Get your Back4App container URL (e.g., `https://your-app.b4a.run`)

2. Modify `main.py` to support webhooks:

```python
# Add webhook support for production
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # Your Back4App URL

if WEBHOOK_URL:
    # Use webhook mode
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )
else:
    # Use polling mode (development)
    application.run_polling(allowed_updates=Update.ALL_TYPES)
```

3. Add `WEBHOOK_URL` environment variable in Back4App

## Step 5: Verify Deployment

1. Check the Back4App logs for any errors
2. Send a message to your Telegram bot
3. Verify it responds correctly

## Environment Variables Summary

| Variable | Required | Description |
|----------|----------|-------------|
| BOT_TOKEN | Yes | Telegram Bot Token |
| GOOGLE_SHEETS_CREDS | Yes | Google Service Account JSON |
| SPREADSHEET_ID | Yes | Google Spreadsheet ID |
| GOOGLE_AI_API_KEY | No | Google AI Studio key (primary AI) |
| GROQ_API_KEY | No | Groq API key (backup AI) |
| OPENROUTER_API_KEY | No | OpenRouter key (fallback AI) |
| PORT | No | Server port (default: 8000) |
| WEBHOOK_URL | No | Full URL for webhook mode |

## Troubleshooting

### Bot not responding
- Check Back4App logs for errors
- Verify BOT_TOKEN is correct
- Ensure the container is running

### Google Sheets not working
- Verify GOOGLE_SHEETS_CREDS is properly escaped JSON
- Check SPREADSHEET_ID is correct
- Ensure the service account has access to the spreadsheet

### AI features not working
- Check that at least one AI API key is set
- Review logs for API errors
- The bot will use fallback parsing if all AI providers fail

## Scaling

Back4App Containers auto-scale based on demand. For high-traffic bots:
1. Enable auto-scaling in container settings
2. Consider using Redis for session storage
3. Use webhook mode instead of polling

## Cost Considerations

- Back4App free tier: 1 container with limited resources
- Paid plans: More containers, better performance
- Telegram bots typically have low resource needs
