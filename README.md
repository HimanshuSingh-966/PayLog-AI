# PayLog AI Bot v2.5

An intelligent Telegram expense tracking bot with AI-powered multi-agent system for personal finance management.

## Complete Feature List

### 1. Natural Language Expense Logging
- **Conversational input**: "Spent 500 on groceries at DMart"
- **Income tracking**: "Received salary 50000", "Got 2000 freelance payment"
- **Category auto-detection**: Automatically categorizes expenses (food, transport, shopping, etc.)
- **Merchant extraction**: Recognizes store names from natural language
- **Date handling**: "yesterday", "2 days ago", "last week"

### 2. AI-Powered Multi-Agent System
The bot uses specialized AI agents working together:
- **Parser Agent**: Extracts structured transaction data from natural language
- **Analyst Agent**: Generates spending insights and pattern analysis
- **Advisor Agent**: Provides personalized financial advice
- **Query Agent**: Answers natural language questions about your finances

### 3. Dual Wallet System with Transfers
- **Total Stack**: Long-term savings/main account
- **Wallet**: Daily spending money
- **Easy transfers**: "Transfer 1000 from total to wallet"
- **Balance validation**: Prevents overdrafts
- **Burn rate tracking**: Calculates daily spending rate

### 4. Smart Lending Tracker with Partial Payments
- **Record loans**: "Lent 5000 to John"
- **Partial payments**: "Received 500 from John" (when he owes 2000)
- **Automatic balance update**: Tracks remaining amount owed
- **Full payment detection**: "John has cleared all debts!"
- **Pending reminders**: Shows overdue loans with days elapsed

### 5. Context-Aware Parsing
The AI remembers your patterns:
- **"same place"** → Uses your last merchant
- **"usual amount"** → Uses your average spending for that category
- **"morning coffee"** → Recognizes as food category, ~₹50-100
- **Shortcuts**: Custom aliases like "gro" for "groceries"

### 6. Predictive Analytics
- **Budget depletion forecast**: "You'll run out of money by Dec 25"
- **Month-end spending prediction**: Projects total monthly expenses
- **Burn rate analysis**: "At current pace, you have 15 days of runway"
- **Trend detection**: "Your food spending is up 25% vs last week"

### 7. Anomaly Detection & Spending Alerts
- **Unusual transactions**: "This ₹5000 is 5x your daily average"
- **Category spikes**: "This shopping expense is 3x your typical amount"
- **Pattern recognition**: Flags out-of-character spending

### 8. Financial Health Score (0-100)
Daily score based on:
- **Savings rate** (max 25 points): % of income saved
- **Budget adherence** (max 20 points): Staying within limits
- **Spending trend** (max 15 points): Decreasing vs increasing
- **Emergency fund** (max 10 points): Runway days
- **Goal progress** (max 10 points): Active financial goals

Score tracking: "Your score dropped 15 points - here's why..."

### 9. Natural Conversational Queries
Ask anything about your finances:
- "How much did I spend on food last week?"
- "Am I spending more than last month?"
- "Where can I cut costs?"
- "What's my biggest expense category?"
- "Show my spending trend"

AI responds conversationally with real data from your transactions.

### 10. Proactive Smart Notifications
- **Budget threshold alerts**: 50%, 80%, 90%, 100% warnings
- **Weekly spending summaries**: Comparison vs previous week
- **Savings goal progress**: "₹5000 more to your ₹50k goal"
- **Income reminders**: Tracks expected salary dates

### 11. AI-Generated Budget Suggestions
- **Cost-cutting recommendations**: "Cut ₹2000 from dining out by cooking 3 more meals"
- **Category-specific advice**: Based on your spending patterns
- **Personalized tips**: Considers your income, expenses, and goals

---

## Supported AI Providers

| Provider | Model | Priority |
|----------|-------|----------|
| Google AI Studio | Gemini 2.0 Flash | Primary |
| Groq | LLaMA 3.1 8B | Backup |
| OpenRouter | Gemini 2.0 Flash | Fallback |

If all providers fail, the bot uses intelligent fallback parsing.

---

## Quick Start

1. **Set environment variables:**
   ```env
   BOT_TOKEN=your_telegram_bot_token
   GOOGLE_SHEETS_CREDS={"type":"service_account",...}
   SPREADSHEET_ID=your_spreadsheet_id
   GOOGLE_AI_API_KEY=your_google_ai_key
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the bot:**
   ```bash
   python main.py
   ```

---

## Usage Examples

### Expense Tracking
```
"Spent 500 on groceries at DMart"
"Paid 200 for uber to office"
"Bought shoes for 3000 at mall yesterday"
```

### Income
```
"Received salary 50000"
"Got 5000 freelance payment"
"Add 10000 to total"
```

### Transfers
```
"Transfer 1000 from total to wallet"
"Move 5000 from wallet to total"
```

### Lending
```
"Lent 5000 to John"
"Gave 2000 to Priya for dinner"
"Received 500 from John"
"John paid back 1000"
```

### Queries
```
"How much did I spend on food last week?"
"What's my financial health?"
"Where can I cut costs?"
"Am I on track for my savings goal?"
"Show me spending by category"
```

---

## Bot Menu Options

| Button | Function |
|--------|----------|
| 💰 Total Stack | View/manage savings account |
| 👛 Wallet | View/manage daily spending |
| 🔄 Transfer | Transfer between wallets |
| 🤝 Lending | Manage loans and returns |
| 📊 Reports | Transaction history & trends |
| 💡 Insights | AI-powered spending analysis |
| 📋 Summary | Financial overview |
| 🏥 Health Score | Financial health report |
| ⚙️ Settings | Budgets, aliases, alerts |
| ⚡ Quick Add | Preset transactions |
| ❓ Ask AI | Natural language queries |
| 🎯 My Goals | Track financial goals |

---

## Deployment

See [DEPLOYMENT_BACK4APP.md](DEPLOYMENT_BACK4APP.md) for Back4App deployment instructions.

---

## File Structure

```
paylog-ai-bot/
├── main.py           # Main Telegram bot (1525 lines)
├── ai_service.py     # Multi-agent AI service (700+ lines)
├── analytics.py      # Analytics & predictions (573 lines)
├── user_prefs.py     # User preferences & goals (532 lines)
├── requirements.txt  # Python dependencies
├── Dockerfile        # Container deployment
├── DEPLOYMENT_BACK4APP.md  # Deployment guide
└── README.md         # This file
```

---

## Tech Stack

- **Python 3.11+**
- **python-telegram-bot**: Telegram Bot API
- **Google AI / Groq / OpenRouter**: AI providers
- **gspread**: Google Sheets integration
- **pandas**: Data analysis
