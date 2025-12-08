import logging
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import gspread
from google.oauth2.service_account import Credentials
import json
from dotenv import load_dotenv
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import re
import csv
import io
from ai_service import PayLogAIService
from analytics import ExpenseAnalytics
from user_prefs import UserPreferences

load_dotenv()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
GOOGLE_SHEETS_CREDS = os.getenv('GOOGLE_SHEETS_CREDS')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
PORT = int(os.getenv('PORT', 8000))

if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable is required")
    logger.info("Please set BOT_TOKEN in your .env file and restart the bot")
    import sys
    sys.exit(0)
if not GOOGLE_SHEETS_CREDS:
    logger.warning("GOOGLE_SHEETS_CREDS not found - Google Sheets functionality will be disabled")
if not SPREADSHEET_ID:
    logger.warning("SPREADSHEET_ID not found - Google Sheets functionality will be disabled")

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'PayLog AI Bot is running!')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

def start_web_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    logger.info(f"Starting HTTP server on port {PORT}")
    server.serve_forever()

class ExpenseTracker:
    def __init__(self):
        self.gc = None
        self.spreadsheet = None
        self.transactions_sheet = None
        self.lending_sheet = None
        self.ai_service = PayLogAIService()
        self.init_google_sheets()
        
    def init_google_sheets(self):
        try:
            if not GOOGLE_SHEETS_CREDS or not SPREADSHEET_ID:
                logger.warning("Google Sheets credentials or Spreadsheet ID missing")
                return
                
            creds_dict = json.loads(GOOGLE_SHEETS_CREDS)
            credentials = Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://spreadsheets.google.com/feeds',
                       'https://www.googleapis.com/auth/drive']
            )
            self.gc = gspread.authorize(credentials)
            self.spreadsheet = self.gc.open_by_key(SPREADSHEET_ID)
            
            try:
                self.transactions_sheet = self.spreadsheet.worksheet('transactions')
            except gspread.WorksheetNotFound:
                self.transactions_sheet = self.spreadsheet.add_worksheet(
                    title='transactions', rows=1000, cols=9
                )
                self.transactions_sheet.append_row([
                    'date', 'type', 'wallet_type', 'amount', 'description', 'balance_total', 'balance_wallet', 'category', 'merchant'
                ])
            
            try:
                self.lending_sheet = self.spreadsheet.worksheet('lending')
            except gspread.WorksheetNotFound:
                self.lending_sheet = self.spreadsheet.add_worksheet(
                    title='lending', rows=1000, cols=8
                )
                self.lending_sheet.append_row([
                    'date', 'person', 'amount', 'status', 'description', 'return_date', 'return_to', 'remaining'
                ])
                
            logger.info("Google Sheets initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing Google Sheets: {e}")
            logger.warning("Bot will continue without Google Sheets functionality")

    def get_current_balances(self):
        try:
            if self.transactions_sheet:
                records = self.transactions_sheet.get_all_records()
                if records:
                    last_record = records[-1]
                    return float(last_record.get('balance_total', 0)), float(last_record.get('balance_wallet', 0))
            return 0, 0
        except Exception as e:
            logger.error(f"Error getting balances: {e}")
            return 0, 0

    def add_transaction(self, transaction_type, wallet_type, amount, description, category='', merchant='', date_override=None):
        try:
            total_balance, wallet_balance = self.get_current_balances()
            
            if wallet_type == 'total':
                if transaction_type == 'add':
                    total_balance += amount
                else:
                    total_balance -= amount
            elif wallet_type == 'wallet':
                if transaction_type == 'add':
                    wallet_balance += amount
                else:
                    wallet_balance -= amount
            
            trans_date = date_override if date_override else datetime.now()
            row_data = [
                trans_date.strftime('%d/%m/%Y'),
                transaction_type,
                wallet_type,
                amount,
                description,
                total_balance,
                wallet_balance,
                category,
                merchant
            ]
            
            if self.transactions_sheet:
                self.transactions_sheet.append_row(row_data)
            
            return total_balance, wallet_balance
            
        except Exception as e:
            logger.error(f"Error adding transaction: {e}")
            return 0, 0

    def transfer_between_wallets(self, from_wallet: str, to_wallet: str, amount: float, description: str = "Transfer"):
        """Transfer money between Total Stack and Wallet"""
        try:
            total_balance, wallet_balance = self.get_current_balances()
            
            if from_wallet == 'total' and to_wallet == 'wallet':
                if total_balance < amount:
                    return False, "Insufficient balance in Total Stack", 0, 0
                total_balance -= amount
                wallet_balance += amount
            elif from_wallet == 'wallet' and to_wallet == 'total':
                if wallet_balance < amount:
                    return False, "Insufficient balance in Wallet", 0, 0
                wallet_balance -= amount
                total_balance += amount
            else:
                return False, "Invalid transfer", 0, 0
            
            trans_date = datetime.now()
            row_data = [
                trans_date.strftime('%d/%m/%Y'),
                'transfer',
                f"{from_wallet}_to_{to_wallet}",
                amount,
                description,
                total_balance,
                wallet_balance,
                'transfer',
                ''
            ]
            
            if self.transactions_sheet:
                self.transactions_sheet.append_row(row_data)
            
            return True, "Transfer successful", total_balance, wallet_balance
            
        except Exception as e:
            logger.error(f"Error transferring: {e}")
            return False, str(e), 0, 0

    def get_all_transactions(self):
        try:
            if self.transactions_sheet:
                return self.transactions_sheet.get_all_records()
            return []
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []

    def get_all_lending(self):
        try:
            if self.lending_sheet:
                return self.lending_sheet.get_all_records()
            return []
        except Exception as e:
            logger.error(f"Error getting lending: {e}")
            return []

    def add_lending(self, person, amount, description):
        try:
            now = datetime.now()
            row_data = [
                now.strftime('%d/%m/%Y'),
                person,
                amount,
                'lent',
                description,
                '',
                '',
                amount  # remaining amount
            ]
            
            if self.lending_sheet:
                self.lending_sheet.append_row(row_data)
                
        except Exception as e:
            logger.error(f"Error adding lending: {e}")

    def return_lending(self, person, amount, return_to):
        """Handle full or partial lending return"""
        try:
            if not self.lending_sheet:
                return False, "Sheets not connected"
                
            records = self.lending_sheet.get_all_records()
            
            remaining_to_apply = amount
            
            for i, record in enumerate(records):
                if remaining_to_apply <= 0:
                    break
                    
                if record['person'].lower() == person.lower() and record['status'] == 'lent':
                    row_num = i + 2
                    loan_amount = float(record['amount'])
                    current_remaining = float(record.get('remaining', loan_amount))
                    
                    if remaining_to_apply >= current_remaining:
                        # Full payment of this loan
                        remaining_to_apply -= current_remaining
                        self.lending_sheet.update_cell(row_num, 4, 'returned')
                        self.lending_sheet.update_cell(row_num, 6, datetime.now().strftime('%d/%m/%Y'))
                        self.lending_sheet.update_cell(row_num, 7, return_to)
                        self.lending_sheet.update_cell(row_num, 8, 0)
                    else:
                        # Partial payment
                        new_remaining = current_remaining - remaining_to_apply
                        remaining_to_apply = 0
                        self.lending_sheet.update_cell(row_num, 4, 'partial')
                        self.lending_sheet.update_cell(row_num, 8, new_remaining)
            
            if remaining_to_apply < amount:
                # Some money was applied
                applied = amount - remaining_to_apply
                self.add_transaction('add', return_to, applied, f'Returned by {person}', category='lending')
                return True, f"₹{applied:,.0f} applied to {person}'s loans"
            
            return False, f"No pending loans found for {person}"
            
        except Exception as e:
            logger.error(f"Error returning lending: {e}")
            return False, str(e)

    def get_pending_lending_for_person(self, person: str) -> float:
        """Get total pending amount for a person"""
        try:
            records = self.get_all_lending()
            total = 0
            for r in records:
                if r['person'].lower() == person.lower() and r['status'] in ['lent', 'partial']:
                    total += float(r.get('remaining', r['amount']))
            return total
        except:
            return 0

    def undo_last_transaction(self):
        try:
            if not self.transactions_sheet:
                return False, "Sheets not connected"
            
            records = self.transactions_sheet.get_all_records()
            if len(records) < 1:
                return False, "No transactions to undo"
            
            last_row = len(records) + 1
            self.transactions_sheet.delete_rows(last_row)
            return True, "Last transaction undone successfully"
            
        except Exception as e:
            logger.error(f"Error undoing transaction: {e}")
            return False, str(e)

    def export_to_csv(self, transactions):
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Date', 'Type', 'Wallet', 'Amount', 'Category', 'Description', 'Merchant'])
        
        for t in transactions:
            writer.writerow([
                t.get('date', ''),
                t.get('type', ''),
                t.get('wallet_type', ''),
                t.get('amount', ''),
                t.get('category', ''),
                t.get('description', ''),
                t.get('merchant', '')
            ])
        
        return output.getvalue()

tracker = ExpenseTracker()
user_preferences = {}

def get_user_prefs(user_id: int) -> UserPreferences:
    if user_id not in user_preferences:
        user_preferences[user_id] = UserPreferences(user_id)
    return user_preferences[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user:
        return
    
    if context.user_data:
        context.user_data.clear()
    user_id = update.message.from_user.id
    prefs = get_user_prefs(user_id)
        
    keyboard = [
        [KeyboardButton("💰 Total Stack"), KeyboardButton("👛 Wallet")],
        [KeyboardButton("🔄 Transfer"), KeyboardButton("🤝 Lending")],
        [KeyboardButton("📊 Reports"), KeyboardButton("💡 Insights")],
        [KeyboardButton("📋 Summary"), KeyboardButton("🏥 Health Score")],
        [KeyboardButton("⚙️ Settings"), KeyboardButton("🔄 Undo Last")],
        [KeyboardButton("⚡ Quick Add"), KeyboardButton("❓ Ask AI")],
        [KeyboardButton("📝 Batch Entry"), KeyboardButton("🎯 My Goals")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_msg = """
🎯 **Welcome to PayLog AI v2.5 - Intelligent Expense Tracker!**

🤖 **AI-Powered Features:**
• 💬 Natural language input - just type naturally!
• 🧠 Context-aware parsing ("same place", "usual amount")
• 📈 Predictive analytics & forecasting
• 🏥 Financial health scoring
• 🎯 Goal tracking & smart notifications
• ❓ Natural queries ("How much did I spend on food?")

📱 **Main Features:**
• 💰 Dual wallet system with transfers
• 🤝 Smart lending with partial payments
• 📊 AI-powered insights & reports
• 🔔 Proactive budget alerts
• ⚡ Quick add with presets

🚀 **Try saying:**
"Spent 500 on groceries at DMart"
"Transfer 1000 from total to wallet"
"How much did I spend last week?"
"What's my financial health?"

Choose an option below or just type naturally!
    """
    
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup)

async def handle_natural_language(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    if not update.message or not update.message.from_user:
        return
    user_id = update.message.from_user.id
    prefs = get_user_prefs(user_id)
    
    # Apply aliases
    aliases = prefs.get_all_aliases()
    for shortcut, full in aliases.items():
        if shortcut in text.lower():
            text = text.lower().replace(shortcut, full)
    
    # Get full context for AI parsing
    user_context = prefs.get_full_context()
    
    # Handle natural queries
    if any(word in text.lower() for word in ['how much', 'what is', 'tell me', 'show me', 'am i', 'where can', 'why']):
        await update.message.reply_text("🤖 Analyzing your question...")
        
        transactions = tracker.get_all_transactions()
        total_balance, wallet_balance = tracker.get_current_balances()
        
        user_data = {
            'total_balance': total_balance,
            'wallet_balance': wallet_balance,
            'budget': prefs.get_total_budget('monthly'),
            'goals': prefs.get_active_goals()
        }
        
        response = tracker.ai_service.answer_query(text, transactions, user_data)
        await update.message.reply_text(f"🤖 **AI Response:**\n\n{response}")
        return
    
    # Handle transfers
    if 'transfer' in text.lower():
        await handle_transfer_command(update, context, text)
        return
    
    # Handle expense/income
    if any(keyword in text.lower() for keyword in ['spent', 'paid', 'bought', 'subtract', 'sub', 'expense']):
        await update.message.reply_text("🤖 Analyzing your expense...")
        
        parsed = tracker.ai_service.parse_natural_language(text, user_context)
        
        if not parsed.get('amount'):
            await update.message.reply_text("❌ Couldn't extract amount. Please try: 'Spent 500 on groceries'")
            return
        
        amount = float(parsed['amount'])
        category = parsed.get('category', 'other')
        description = parsed.get('description', text)
        merchant = parsed.get('merchant', '')
        wallet_type = parsed.get('wallet_type', user_context.get('last_wallet', 'wallet'))
        
        # Handle time reference
        trans_date = datetime.now()
        time_ref = parsed.get('time_reference', 'today').lower()
        if 'yesterday' in time_ref:
            trans_date = datetime.now() - timedelta(days=1)
        elif 'days ago' in time_ref:
            days_match = re.search(r'(\d+)\s*days?\s*ago', time_ref)
            if days_match:
                trans_date = datetime.now() - timedelta(days=int(days_match.group(1)))
        
        total_bal, wallet_bal = tracker.add_transaction('subtract', wallet_type, amount, description, category=category, merchant=merchant, date_override=trans_date)
        
        # Update user context and history
        prefs.add_to_history(description, category, amount, merchant, wallet_type)
        prefs.update_context(category=category, amount=amount, wallet=wallet_type, merchant=merchant, description=description)
        
        # Generate alerts
        transactions = tracker.get_all_transactions()
        daily_avg = ExpenseAnalytics.calculate_daily_average(transactions)
        category_avg = ExpenseAnalytics.calculate_category_average(transactions, category)
        
        alert_msg = ""
        
        # Anomaly detection
        anomaly = tracker.ai_service.detect_anomaly(amount, category, daily_avg, category_avg)
        if anomaly:
            alert_msg += f"\n\n{anomaly}"
        
        # Budget check
        budget = prefs.get_budget(category, 'monthly')
        if budget > 0:
            category_totals = ExpenseAnalytics.get_category_totals(transactions, 30)
            spent = category_totals.get(category, 0)
            budget_status = tracker.ai_service.check_budget_status(spent, budget, 'month')
            if budget_status['status'] in ['warning', 'critical', 'exceeded']:
                alert_msg += f"\n\n{budget_status['message']}"
        
        await update.message.reply_text(
            f"✅ **Expense Recorded!**\n\n"
            f"💰 Amount: ₹{amount:,.2f}\n"
            f"📂 Category: {category}\n"
            f"🏪 Merchant: {merchant if merchant else 'N/A'}\n"
            f"📅 Date: {trans_date.strftime('%d %b %Y')}\n"
            f"📝 Description: {description}\n\n"
            f"💳 **Updated Balances:**\n"
            f"   • Total: ₹{total_bal:,.2f}\n"
            f"   • Wallet: ₹{wallet_bal:,.2f}"
            f"{alert_msg}"
        )
        
    elif any(keyword in text.lower() for keyword in ['add', 'received', 'income', 'salary', 'got']):
        await update.message.reply_text("🤖 Processing income...")
        
        parsed = tracker.ai_service.parse_natural_language(text, user_context)
        
        if not parsed.get('amount'):
            await update.message.reply_text("❌ Couldn't extract amount.")
            return
        
        amount = float(parsed['amount'])
        description = parsed.get('description', text)
        wallet_type = parsed.get('wallet_type', 'total')
        
        total_bal, wallet_bal = tracker.add_transaction('add', wallet_type, amount, description, category='income')
        
        # Update income in preferences
        if 'salary' in text.lower():
            prefs.set_income(amount, datetime.now().day)
        
        await update.message.reply_text(
            f"✅ **Income Added!**\n\n"
            f"💰 Amount: ₹{amount:,.2f}\n"
            f"📝 {description}\n\n"
            f"💳 **Updated Balances:**\n"
            f"   • Total: ₹{total_bal:,.2f}\n"
            f"   • Wallet: ₹{wallet_bal:,.2f}"
        )
        
    elif any(keyword in text.lower() for keyword in ['lent', 'lend', 'gave', 'loan']):
        await handle_lending_natural(update, context, text, prefs)
        
    elif any(keyword in text.lower() for keyword in ['returned', 'paid back', 'got back']):
        await handle_return_natural(update, context, text, prefs)
        
    else:
        # Try context-aware handling
        context_data = prefs.get_context()
        if context_data.get('last_category'):
            if any(word in text.lower() for word in ['more', 'that', 'same', 'again']):
                try:
                    amount_match = re.search(r'(\d+(?:\.\d+)?)', text)
                    if amount_match:
                        amount = float(amount_match.group(1))
                        category = context_data['last_category']
                        wallet_type = context_data.get('last_wallet', 'wallet')
                        
                        total_bal, wallet_bal = tracker.add_transaction('subtract', wallet_type, amount, text, category=category)
                        
                        await update.message.reply_text(
                            f"✅ Added ₹{amount} to {category}!\n"
                            f"💳 Balance: ₹{total_bal if wallet_type=='total' else wallet_bal:,.2f}"
                        )
                        return
                except:
                    pass
        
        await update.message.reply_text(
            "🤔 I didn't understand that. Try:\n"
            "• 'Spent 500 on groceries'\n"
            "• 'Transfer 1000 from total to wallet'\n"
            "• 'How much did I spend on food last week?'\n"
            "• 'What's my financial health?'"
        )

async def handle_transfer_command(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle wallet transfer commands"""
    # Parse transfer command
    amount_match = re.search(r'(\d+(?:\.\d+)?)', text)
    if not amount_match:
        await update.message.reply_text("❌ Please specify an amount. Example: 'Transfer 1000 from total to wallet'")
        return
    
    amount = float(amount_match.group(1))
    text_lower = text.lower()
    
    from_wallet = 'total' if 'from total' in text_lower or 'from stack' in text_lower else 'wallet'
    to_wallet = 'wallet' if 'to wallet' in text_lower else 'total'
    
    if from_wallet == to_wallet:
        # Try to infer from context
        if 'to wallet' in text_lower:
            from_wallet = 'total'
        elif 'to total' in text_lower or 'to stack' in text_lower:
            from_wallet = 'wallet'
        else:
            await update.message.reply_text("❌ Please specify: 'Transfer 1000 from total to wallet' or vice versa")
            return
    
    success, message, total_bal, wallet_bal = tracker.transfer_between_wallets(from_wallet, to_wallet, amount, "Transfer")
    
    if success:
        from_name = "Total Stack" if from_wallet == "total" else "Wallet"
        to_name = "Wallet" if to_wallet == "wallet" else "Total Stack"
        await update.message.reply_text(
            f"✅ **Transfer Successful!**\n\n"
            f"💸 ₹{amount:,.2f} transferred from {from_name} to {to_name}\n\n"
            f"💳 **Updated Balances:**\n"
            f"   • Total Stack: ₹{total_bal:,.2f}\n"
            f"   • Wallet: ₹{wallet_bal:,.2f}"
        )
    else:
        await update.message.reply_text(f"❌ Transfer failed: {message}")

async def handle_lending_natural(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, prefs: UserPreferences):
    """Handle natural language lending"""
    parsed = tracker.ai_service.parse_natural_language(text, prefs.get_full_context())
    
    amount = float(parsed.get('amount', 0))
    if not amount:
        await update.message.reply_text("❌ Please specify amount: 'Lent 5000 to John'")
        return
    
    # Extract person name
    person_match = re.search(r'(?:to|gave)\s+(\w+)', text.lower())
    person = person_match.group(1).title() if person_match else "Unknown"
    
    tracker.add_lending(person, amount, text)
    
    await update.message.reply_text(
        f"✅ **Lending Recorded!**\n\n"
        f"👤 Person: {person}\n"
        f"💰 Amount: ₹{amount:,.2f}\n"
        f"📝 {text}\n\n"
        f"💡 Say 'Received X from {person}' when they pay back!"
    )

async def handle_return_natural(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, prefs: UserPreferences):
    """Handle natural language return"""
    parsed = tracker.ai_service.parse_natural_language(text, prefs.get_full_context())
    
    amount = float(parsed.get('amount', 0))
    if not amount:
        await update.message.reply_text("❌ Please specify amount: 'Received 5000 from John'")
        return
    
    # Extract person name
    person_match = re.search(r'(?:from|by)\s+(\w+)', text.lower())
    person = person_match.group(1).title() if person_match else None
    
    if not person:
        await update.message.reply_text("❌ Please specify who returned: 'Received 5000 from John'")
        return
    
    pending = tracker.get_pending_lending_for_person(person)
    
    success, message = tracker.return_lending(person, amount, 'wallet')
    
    if success:
        new_pending = tracker.get_pending_lending_for_person(person)
        result_msg = f"✅ **Payment Received!**\n\n{message}\n"
        
        if new_pending > 0:
            result_msg += f"\n📊 {person} still owes: ₹{new_pending:,.2f}"
        else:
            result_msg += f"\n🎉 {person} has cleared all debts!"
        
        await update.message.reply_text(result_msg)
    else:
        await update.message.reply_text(f"❌ {message}")

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or not update.message.from_user:
        return
        
    text = update.message.text
    user_id = update.message.from_user.id
    prefs = get_user_prefs(user_id)
    
    if not hasattr(context, 'user_data') or context.user_data is None:
        context.user_data = {}
    
    if text in ["💰 Total Stack", "👛 Wallet"]:
        context.user_data['category'] = 'total' if text == "💰 Total Stack" else 'wallet'
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Money", callback_data=f"add_{context.user_data['category']}"),
             InlineKeyboardButton("➖ Subtract Money", callback_data=f"subtract_{context.user_data['category']}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        total_balance, wallet_balance = tracker.get_current_balances()
        current_balance = total_balance if context.user_data['category'] == 'total' else wallet_balance
        
        transactions = tracker.get_all_transactions()
        
        msg = f"🏦 **{text}**\n💰 Current Balance: ₹{current_balance:,.2f}\n\n"
        
        if text == "👛 Wallet":
            burn_rate, days_left = ExpenseAnalytics.get_burn_rate(wallet_balance, transactions)
            msg += f"📊 Burn rate: ₹{burn_rate:.2f}/day\n"
            if days_left < 999:
                msg += f"⏳ Days left: {days_left}\n\n"
            
            if wallet_balance < 500:
                suggestion = tracker.ai_service.suggest_wallet_transfer(wallet_balance, total_balance)
                if suggestion:
                    msg += f"{suggestion}\n\n"
        
        msg += "⬇️ What would you like to do?"
        
        await update.message.reply_text(msg, reply_markup=reply_markup)
    
    elif text == "🔄 Transfer":
        keyboard = [
            [InlineKeyboardButton("💰→👛 Total to Wallet", callback_data="transfer_total_wallet")],
            [InlineKeyboardButton("👛→💰 Wallet to Total", callback_data="transfer_wallet_total")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        total_balance, wallet_balance = tracker.get_current_balances()
        
        await update.message.reply_text(
            f"🔄 **Transfer Between Wallets**\n\n"
            f"💰 Total Stack: ₹{total_balance:,.2f}\n"
            f"👛 Wallet: ₹{wallet_balance:,.2f}\n\n"
            f"⬇️ Choose transfer direction:",
            reply_markup=reply_markup
        )
    
    elif text == "🏥 Health Score":
        await update.message.reply_text("🏥 Calculating your financial health...")
        
        transactions = tracker.get_all_transactions()
        total_balance, wallet_balance = tracker.get_current_balances()
        
        # Gather data for health score
        summary = ExpenseAnalytics.get_income_expense_summary(transactions, 30)
        trend = ExpenseAnalytics.detect_trend(transactions)
        budget = prefs.get_total_budget('monthly')
        goals = prefs.get_active_goals()
        
        health_data = {
            'income': summary['income'] or prefs.get_income().get('monthly', 0),
            'expenses': summary['expenses'],
            'savings': total_balance + wallet_balance,
            'budget': budget,
            'trend': trend.split()[0] if ' ' in trend else trend,
            'goals': goals
        }
        
        health_result = tracker.ai_service.calculate_financial_health_score(health_data)
        
        # Save health score
        prefs.update_health_score(health_result['score'], health_result['factors'])
        
        # Check trend
        health_trend = prefs.get_health_trend()
        trend_emoji = "📈" if health_trend == 'improving' else "📉" if health_trend == 'declining' else "➡️"
        
        msg = f"🏥 **Financial Health Report**\n\n"
        msg += f"📊 **Score: {health_result['score']}/100** (Grade: {health_result['grade']})\n"
        msg += f"{trend_emoji} Trend: {health_trend.title()}\n\n"
        msg += f"{health_result['message']}\n\n"
        msg += f"📋 **Breakdown:**\n"
        
        for factor, points, desc in health_result['factors']:
            emoji = "✅" if points.startswith('+') else "❌" if points.startswith('-') else "➡️"
            msg += f"{emoji} {factor}: {points} - {desc}\n"
        
        await update.message.reply_text(msg)
    
    elif text == "❓ Ask AI":
        await update.message.reply_text(
            "❓ **Ask AI Anything!**\n\n"
            "You can ask questions like:\n"
            "• 'How much did I spend on food last week?'\n"
            "• 'Am I spending more than last month?'\n"
            "• 'Where can I cut costs?'\n"
            "• 'What's my biggest expense category?'\n"
            "• 'Show my spending trend'\n\n"
            "Just type your question!"
        )
        context.user_data['waiting_for'] = 'ai_query'
    
    elif text == "💡 Insights":
        await update.message.reply_text("🤖 Generating AI insights...")
        
        transactions = tracker.get_all_transactions()
        if not transactions:
            await update.message.reply_text("📊 No data yet. Start tracking expenses!")
            return
        
        recent_trans = transactions[-50:]
        trans_data = "\n".join([f"{t['date']}: ₹{t['amount']} - {t['description']} ({t['category']})" 
                                for t in recent_trans])
        
        # Get comparison data
        comparison = ExpenseAnalytics.compare_periods(transactions, 'week')
        
        insights = tracker.ai_service.get_spending_insights(trans_data, "month")
        
        daily_avg = ExpenseAnalytics.calculate_daily_average(transactions)
        category_breakdown = ExpenseAnalytics.get_category_breakdown(transactions)
        forecast, pace = ExpenseAnalytics.forecast_month_end(transactions)
        
        report = f"💡 **AI Insights**\n\n"
        report += f"📊 **Quick Stats:**\n"
        report += f"• Daily average: ₹{daily_avg:.2f}\n"
        report += f"• Month forecast: ₹{forecast:.2f} ({pace} pace)\n"
        
        if comparison['saved']:
            report += f"• 🎉 Saved ₹{abs(comparison['difference']):,.0f} vs last week!\n\n"
        else:
            report += f"• 📈 Spent ₹{abs(comparison['difference']):,.0f} more than last week\n\n"
        
        if category_breakdown:
            report += "📂 **Category Breakdown:**\n"
            for cat, pct in sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True)[:5]:
                report += f"• {cat}: {pct:.1f}%\n"
            report += f"\n"
        
        report += f"🤖 **AI Analysis:**\n{insights}"
        
        await update.message.reply_text(report)
    
    elif text == "⚡ Quick Add":
        keyboard = [
            [InlineKeyboardButton("₹50 Coffee", callback_data="quick_50_food"),
             InlineKeyboardButton("₹100 Snacks", callback_data="quick_100_food")],
            [InlineKeyboardButton("₹500 Groceries", callback_data="quick_500_groceries"),
             InlineKeyboardButton("₹500 Fuel", callback_data="quick_500_fuel")],
            [InlineKeyboardButton("₹200 Transport", callback_data="quick_200_transport"),
             InlineKeyboardButton("₹1000 Shopping", callback_data="quick_1000_shopping")],
            [InlineKeyboardButton("⭐ My Frequent", callback_data="frequent_trans")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚡ **Quick Add Transaction**\n\n"
            "Choose a preset or see your frequent transactions:",
            reply_markup=reply_markup
        )
    
    elif text == "🤝 Lending":
        keyboard = [
            [InlineKeyboardButton("💸 Lend Money", callback_data="lend_money"),
             InlineKeyboardButton("💰 Money Returned", callback_data="money_returned")],
            [InlineKeyboardButton("📊 Lending Analytics", callback_data="lending_analytics")],
            [InlineKeyboardButton("⏰ Pending Reminders", callback_data="lending_reminders")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🤝 **Lending Management**\n\n"
            "💡 You can also say:\n"
            "• 'Lent 5000 to John'\n"
            "• 'Received 2000 from John'\n\n"
            "⬇️ Choose an action:",
            reply_markup=reply_markup
        )
    
    elif text == "📊 Reports":
        keyboard = [
            [InlineKeyboardButton("📅 Today", callback_data="history_day"),
             InlineKeyboardButton("📆 Week", callback_data="history_week")],
            [InlineKeyboardButton("🗓️ Month", callback_data="history_month"),
             InlineKeyboardButton("📅 Year", callback_data="history_year")],
            [InlineKeyboardButton("📈 Trends", callback_data="show_trends")],
            [InlineKeyboardButton("📊 Weekly Summary", callback_data="weekly_summary")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📊 **Transaction Reports**\n\n⬇️ Select time period:",
            reply_markup=reply_markup
        )
    
    elif text == "📋 Summary":
        await update.message.reply_text("⏳ Generating summary...")
        
        transactions = tracker.get_all_transactions()
        lending = tracker.get_all_lending()
        
        if not transactions:
            await update.message.reply_text("No data yet.")
            return
        
        total_balance, wallet_balance = tracker.get_current_balances()
        
        summary_data = ExpenseAnalytics.get_income_expense_summary(transactions, 30)
        lending_stats = ExpenseAnalytics.analyze_lending(lending)
        runout = ExpenseAnalytics.predict_runout_date(wallet_balance, transactions)
        
        summary = f"""
📊 **FINANCIAL SUMMARY**
━━━━━━━━━━━━━━━━━━━━━
💰 **Current Balances:**
   • Total Stack: ₹{total_balance:,.2f}
   • Wallet: ₹{wallet_balance:,.2f}
   • Combined: ₹{total_balance + wallet_balance:,.2f}

📈 **This Month:**
   • Income: ₹{summary_data['income']:,.2f}
   • Expenses: ₹{summary_data['expenses']:,.2f}
   • Savings: ₹{summary_data['savings']:,.2f}
   • Savings Rate: {summary_data['savings_rate']:.1f}%

🤝 **Lending:**
   • Total Lent: ₹{lending_stats['total_lent']:,.2f}
   • Pending: ₹{lending_stats['pending']:,.2f}

⏳ **Runway:**
   {runout['message'] if runout['days_left'] < 999 else '✅ You have a healthy runway'}
━━━━━━━━━━━━━━━━━━━━━
        """
        await update.message.reply_text(summary)
    
    elif text == "⚙️ Settings":
        keyboard = [
            [InlineKeyboardButton("🏷️ Manage Aliases", callback_data="manage_aliases")],
            [InlineKeyboardButton("💰 Set Budgets", callback_data="set_budgets")],
            [InlineKeyboardButton("💵 Set Income", callback_data="set_income")],
            [InlineKeyboardButton("🔔 Alert Settings", callback_data="alert_settings")],
            [InlineKeyboardButton("⭐ Frequent Transactions", callback_data="frequent_trans")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚙️ **Settings & Preferences**\n\n⬇️ Choose an option:",
            reply_markup=reply_markup
        )
    
    elif text == "🔄 Undo Last":
        success, message = tracker.undo_last_transaction()
        if success:
            await update.message.reply_text(f"✅ {message}")
        else:
            await update.message.reply_text(f"❌ {message}")
    
    elif text == "📝 Batch Entry":
        await update.message.reply_text(
            "📝 **Batch Entry Mode**\n\n"
            "Enter multiple transactions, one per line:\n\n"
            "**Format:** amount category description\n\n"
            "**Example:**\n"
            "500 groceries weekly shopping\n"
            "200 fuel petrol refill\n"
            "100 food lunch\n\n"
            "Send your transactions now:"
        )
        context.user_data['waiting_for'] = 'batch_transactions'
    
    elif text == "🎯 My Goals":
        goals = prefs.get_active_goals()
        total_balance, wallet_balance = tracker.get_current_balances()
        
        if not goals:
            keyboard = [
                [InlineKeyboardButton("➕ Add Goal", callback_data="add_goal")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "🎯 **Your Goals**\n\n"
                "No goals set yet.\n\n"
                "💡 Set goals to track savings, spending limits, or financial targets!",
                reply_markup=reply_markup
            )
        else:
            transactions = tracker.get_all_transactions()
            goal_progress = ExpenseAnalytics.calculate_goal_progress(goals, total_balance + wallet_balance, transactions)
            
            msg = "🎯 **Your Active Goals:**\n\n"
            for i, gp in enumerate(goal_progress[:5], 1):
                progress_bar = "█" * int(gp['progress'] / 10) + "░" * (10 - int(gp['progress'] / 10))
                status_emoji = "✅" if gp['completed'] else "🔥" if gp['progress'] >= 75 else "📊"
                
                msg += f"{status_emoji} **{gp['description']}**\n"
                msg += f"   [{progress_bar}] {gp['progress']:.0f}%\n"
                msg += f"   ₹{gp['current']:,.0f} / ₹{gp['target']:,.0f}\n"
                if gp['days_remaining']:
                    msg += f"   ⏳ {gp['days_remaining']} days left\n"
                msg += f"\n"
            
            # Check for goal notifications
            notifications = tracker.ai_service.check_goal_progress(goals, total_balance + wallet_balance)
            if notifications:
                msg += "🔔 **Updates:**\n"
                for n in notifications[:2]:
                    msg += f"{n}\n"
            
            keyboard = [
                [InlineKeyboardButton("➕ Add New Goal", callback_data="add_goal")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(msg, reply_markup=reply_markup)
    
    else:
        await handle_natural_language(update, context, text)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.data:
        return
        
    await query.answer()
    data = query.data
    
    if not hasattr(context, 'user_data') or context.user_data is None:
        context.user_data = {}
    
    if data.startswith('quick_'):
        parts = data.split('_')
        amount = float(parts[1])
        category = parts[2]
        
        total_bal, wallet_bal = tracker.add_transaction('subtract', 'wallet', amount, f"Quick: {category}", category=category)
        
        await query.edit_message_text(
            f"✅ Quick transaction added!\n"
            f"💰 ₹{amount} - {category}\n"
            f"💳 Wallet: ₹{wallet_bal:,.2f}"
        )
    
    elif data.startswith('transfer_'):
        parts = data.split('_')
        from_wallet = parts[1]
        to_wallet = parts[2]
        
        context.user_data['transfer_from'] = from_wallet
        context.user_data['transfer_to'] = to_wallet
        context.user_data['waiting_for'] = 'transfer_amount'
        
        from_name = "Total Stack" if from_wallet == "total" else "Wallet"
        to_name = "Wallet" if to_wallet == "wallet" else "Total Stack"
        
        await query.edit_message_text(
            f"🔄 **Transfer: {from_name} → {to_name}**\n\n"
            f"💵 Enter the amount to transfer:"
        )
    
    elif data == 'weekly_summary':
        await query.edit_message_text("📊 Generating weekly summary...")
        
        transactions = tracker.get_all_transactions()
        summary = tracker.ai_service.generate_weekly_summary(transactions)
        
        await query.edit_message_text(summary)
    
    elif data == 'set_budgets':
        await query.edit_message_text(
            "💰 **Set Monthly Budget**\n\n"
            "Reply with budget details:\n\n"
            "**Format:** category amount\n\n"
            "**Example:**\n"
            "food 10000\n"
            "shopping 5000\n"
            "entertainment 3000\n\n"
            "Send your budgets:"
        )
        context.user_data['waiting_for'] = 'budget_details'
    
    elif data == 'set_income':
        await query.edit_message_text(
            "💵 **Set Monthly Income**\n\n"
            "Reply with your monthly income:\n\n"
            "**Example:** 50000\n\n"
            "This helps calculate savings rate and health score."
        )
        context.user_data['waiting_for'] = 'income_amount'
    
    elif data.startswith('add_') or data.startswith('subtract_'):
        action, category = data.split('_')
        context.user_data['action'] = action
        context.user_data['category'] = category
        context.user_data['waiting_for'] = 'amount'
        
        action_text = "add to" if action == "add" else "subtract from"
        category_text = "Total Stack" if category == "total" else "Wallet"
        
        await query.edit_message_text(
            f"💰 **{action_text.title()} {category_text}**\n\n"
            f"💵 Please enter the amount to {action_text} {category_text.lower()}:\n\n"
            f"💡 Example: 500 or 1500.50"
        )
    
    elif data == 'lend_money':
        await query.edit_message_text(
            "💸 **Lend Money**\n\n"
            "👤 Please enter the person's name:\n\n"
            "💡 Example: John"
        )
        context.user_data['action'] = 'lend'
        context.user_data['waiting_for'] = 'person_name'
    
    elif data == 'money_returned':
        await query.edit_message_text(
            "💰 **Money Returned**\n\n"
            "👤 Please enter the name of the person who returned money:\n\n"
            "💡 You can also send partial amounts!\n"
            "💡 Example: John"
        )
        context.user_data['action'] = 'return'
        context.user_data['waiting_for'] = 'return_person'
    
    elif data == 'lending_reminders':
        lending = tracker.get_all_lending()
        pending = [l for l in lending if l['status'] in ['lent', 'partial']]
        
        if not pending:
            await query.edit_message_text("✅ No pending loans!")
            return
        
        reminders = "⏰ **Pending Loan Reminders:**\n\n"
        
        for loan in pending:
            loan_date = datetime.strptime(str(loan['date']), '%d/%m/%Y')
            days_ago = (datetime.now() - loan_date).days
            remaining = float(loan.get('remaining', loan['amount']))
            
            status_emoji = "🔴" if days_ago > 30 else "⚠️" if days_ago > 14 else "📌"
            reminders += f"{status_emoji} **{loan['person']}**\n"
            reminders += f"   Amount: ₹{remaining:,.2f}"
            if loan['status'] == 'partial':
                reminders += f" (partial - originally ₹{float(loan['amount']):,.0f})"
            reminders += f"\n   Days ago: {days_ago}\n"
            reminders += f"   Note: {loan['description']}\n\n"
        
        await query.edit_message_text(reminders)
    
    elif data == 'lending_analytics':
        await query.edit_message_text("🤖 Analyzing lending patterns...")
        
        lending = tracker.get_all_lending()
        stats = ExpenseAnalytics.analyze_lending(lending)
        
        lending_text = "\n".join([f"{l['date']}: ₹{l['amount']} to {l['person']} ({l['status']})" for l in lending[-20:]])
        
        ai_analysis = tracker.ai_service.analyze_lending_patterns(lending_text) if lending_text else "No lending data yet."
        
        report = f"""
🤝 **Lending Analytics**

📊 **Statistics:**
• Total Lent: ₹{stats['total_lent']:,.2f}
• Total Returned: ₹{stats['total_returned']:,.2f}
• Pending: ₹{stats['pending']:,.2f}
• Avg Amount: ₹{stats['avg_amount']:,.2f}
• Avg Return Time: {stats['avg_return_days']:.0f} days

👥 **Pending from:**
"""
        for p in stats['pending_persons'][:5]:
            report += f"• {p['person']}: ₹{p['amount']:,.2f}\n"
        
        report += f"\n🤖 **AI Insights:**\n{ai_analysis}"
        
        await query.edit_message_text(report)
    
    elif data.startswith('history_'):
        period = data.split('_')[1]
        await query.edit_message_text("⏳ Loading history...")
        
        transactions = tracker.get_all_transactions()
        now = datetime.now()
        
        period_map = {'day': 1, 'week': 7, 'month': 30, 'year': 365}
        days = period_map.get(period, 30)
        
        cutoff = now - timedelta(days=days)
        filtered = [t for t in transactions if datetime.strptime(str(t['date']), '%d/%m/%Y') >= cutoff]
        
        if not filtered:
            await query.edit_message_text(f"No transactions in the last {period}.")
            return
        
        history = f"📊 **Transaction History ({period.upper()}):**\n\n"
        for t in filtered[-15:]:
            history += f"📅 {t['date']}\n"
            trans_type = str(t['type']).title() if isinstance(t['type'], str) else t['type']
            history += f"💰 {trans_type} ₹{t['amount']} - {t['description']}\n"
            if t.get('merchant'):
                history += f"🏪 {t['merchant']}\n"
            history += f"\n"
        
        await query.edit_message_text(history)
    
    elif data == 'show_trends':
        await query.edit_message_text("📈 Analyzing trends...")
        
        transactions = tracker.get_all_transactions()
        
        categories = set(t.get('category', 'other') for t in transactions if t['type'] == 'subtract')
        
        trends = "📈 **Spending Trends (4 weeks):**\n\n"
        for cat in list(categories)[:5]:
            cat_str = str(cat) if cat else 'other'
            trend = ExpenseAnalytics.detect_trend(transactions, cat_str, 4)
            trends += f"• {cat_str}: {trend}\n"
        
        await query.edit_message_text(trends)
    
    elif data == 'manage_aliases':
        user_id = query.from_user.id
        prefs = get_user_prefs(user_id)
        
        aliases = prefs.get_all_aliases()
        
        msg = "🏷️ **Your Aliases:**\n\n"
        if aliases:
            for shortcut, full in aliases.items():
                msg += f"• {shortcut} → {full}\n"
            msg += "\n"
        else:
            msg += "No aliases set yet.\n\n"
        
        msg += "💡 To add alias, type:\n'set alias gro for groceries'"
        
        await query.edit_message_text(msg)
    
    elif data == 'frequent_trans':
        await query.edit_message_text("⭐ Finding frequent transactions...")
        
        transactions = tracker.get_all_transactions()
        frequent = ExpenseAnalytics.get_frequent_transactions(transactions, 8)
        
        if not frequent:
            await query.edit_message_text("No frequent transactions found yet.")
            return
        
        keyboard = []
        for ft in frequent[:6]:
            btn_text = f"₹{ft['amount']} - {ft['description'][:20]}"
            callback = f"quick_{int(ft['amount'])}_{ft['category']}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("⭐ **Quick Add Frequent:**", reply_markup=reply_markup)
    
    elif data == 'add_goal':
        await query.edit_message_text(
            "🎯 **Add New Goal**\n\n"
            "Reply with goal details in this format:\n\n"
            "**Format:** type target description [deadline]\n\n"
            "**Types:** savings, spending_limit, investment\n\n"
            "**Example:**\n"
            "savings 50000 Save for vacation 2025-12-31\n"
            "spending_limit 5000 Monthly food budget"
        )
        context.user_data['waiting_for'] = 'goal_details'

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        await handle_menu(update, context)
        return
    
    if not hasattr(context, 'user_data') or context.user_data is None:
        context.user_data = {}
    
    if not update.message or not update.message.from_user:
        return
    user_id = update.message.from_user.id
    prefs = get_user_prefs(user_id)
    text = update.message.text.strip()
    
    # Handle alias setting
    if text.lower().startswith('set alias'):
        match = re.match(r'set alias (\w+) for (.+)', text.lower())
        if match:
            shortcut, full = match.groups()
            prefs.add_alias(shortcut, full)
            await update.message.reply_text(f"✅ Alias set: '{shortcut}' → '{full}'")
            return
    
    if 'waiting_for' not in context.user_data:
        await handle_menu(update, context)
        return
    
    waiting_for = context.user_data['waiting_for']
    
    if waiting_for == 'transfer_amount':
        try:
            amount = float(text)
            from_wallet = context.user_data.get('transfer_from', 'total')
            to_wallet = context.user_data.get('transfer_to', 'wallet')
            
            success, message, total_bal, wallet_bal = tracker.transfer_between_wallets(from_wallet, to_wallet, amount, "Transfer")
            
            if success:
                from_name = "Total Stack" if from_wallet == "total" else "Wallet"
                to_name = "Wallet" if to_wallet == "wallet" else "Total Stack"
                await update.message.reply_text(
                    f"✅ **Transfer Successful!**\n\n"
                    f"💸 ₹{amount:,.2f} transferred from {from_name} to {to_name}\n\n"
                    f"💳 **Updated Balances:**\n"
                    f"   • Total Stack: ₹{total_bal:,.2f}\n"
                    f"   • Wallet: ₹{wallet_bal:,.2f}"
                )
            else:
                await update.message.reply_text(f"❌ {message}")
            
            context.user_data.clear()
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number.")
    
    elif waiting_for == 'ai_query':
        await update.message.reply_text("🤖 Analyzing your question...")
        
        transactions = tracker.get_all_transactions()
        total_balance, wallet_balance = tracker.get_current_balances()
        
        user_data = {
            'total_balance': total_balance,
            'wallet_balance': wallet_balance,
            'budget': prefs.get_total_budget('monthly'),
            'goals': prefs.get_active_goals()
        }
        
        response = tracker.ai_service.answer_query(text, transactions, user_data)
        await update.message.reply_text(f"🤖 **AI Response:**\n\n{response}")
        context.user_data.clear()
    
    elif waiting_for == 'budget_details':
        try:
            lines = text.strip().split('\n')
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 2:
                    category = parts[0].lower()
                    amount = float(parts[1])
                    prefs.set_budget(category, amount, 'monthly')
            
            await update.message.reply_text(
                f"✅ Budgets saved!\n\n"
                f"💰 Total monthly budget: ₹{prefs.get_total_budget('monthly'):,.2f}"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
        context.user_data.clear()
    
    elif waiting_for == 'income_amount':
        try:
            income = float(text)
            prefs.set_income(income, datetime.now().day)
            await update.message.reply_text(
                f"✅ Monthly income set to ₹{income:,.2f}\n\n"
                f"💡 This helps calculate your savings rate and financial health score."
            )
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number.")
        context.user_data.clear()
    
    elif waiting_for == 'amount':
        try:
            amount = float(text)
            if amount <= 0:
                await update.message.reply_text("❌ Please enter a positive amount.")
                return
                
            context.user_data['amount'] = amount
            action = context.user_data.get('action', 'add')
            category = context.user_data.get('category', 'total')
            
            action_text = "adding to" if action == "add" else "subtracting from"
            category_text = "Total Stack" if category == "total" else "Wallet"
            
            await update.message.reply_text(
                f"💰 **₹{amount:,.2f}** will be {action_text} {category_text}\n\n"
                f"📝 Please enter a description:\n\n"
                f"💡 Example: Salary, Groceries, etc."
            )
            context.user_data['waiting_for'] = 'description'
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number.")
    
    elif waiting_for == 'description':
        description = text
        action = context.user_data.get('action', 'add')
        category = context.user_data.get('category', 'total')
        amount = context.user_data.get('amount', 0)
        
        wallet_type = context.user_data.get('category', 'total')
        total_balance, wallet_balance = tracker.add_transaction(action, wallet_type, amount, description, category='manual')
        
        action_text = "Added to" if action == "add" else "Subtracted from"
        category_text = "Total Stack" if wallet_type == "total" else "Wallet"
        
        await update.message.reply_text(
            f"✅ **Transaction Successful!**\n\n"
            f"💰 Amount: ₹{amount:,.2f} {action_text.lower()} {category_text.lower()}\n"
            f"📝 Description: {description}\n\n"
            f"💳 **Updated Balances:**\n"
            f"   • Total Stack: ₹{total_balance:,.2f}\n"
            f"   • Wallet: ₹{wallet_balance:,.2f}"
        )
        
        context.user_data.clear()
    
    elif waiting_for == 'person_name':
        context.user_data['person'] = text
        await update.message.reply_text(
            f"👤 **Lending to: {text}**\n\n"
            f"💵 Please enter the amount:\n\n"
            f"💡 Example: 5000"
        )
        context.user_data['waiting_for'] = 'lend_amount'
    
    elif waiting_for == 'lend_amount':
        try:
            amount = float(text)
            context.user_data['lend_amount'] = amount
            await update.message.reply_text(
                f"💸 **Lending ₹{amount:,.2f} to {context.user_data['person']}**\n\n"
                f"📝 Please enter a description:\n\n"
                f"💡 Example: Personal loan, Dinner split, etc."
            )
            context.user_data['waiting_for'] = 'lend_description'
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid amount.")
    
    elif waiting_for == 'lend_description':
        person = context.user_data['person']
        amount = context.user_data['lend_amount']
        
        tracker.add_lending(person, amount, text)
        
        await update.message.reply_text(
            f"✅ **Lending Recorded!**\n\n"
            f"👤 Person: {person}\n"
            f"💰 Amount: ₹{amount:,.2f}\n"
            f"📝 Description: {text}\n\n"
            f"💡 Say 'Received X from {person}' when they pay back (even partial amounts)!"
        )
        context.user_data.clear()
    
    elif waiting_for == 'return_person':
        context.user_data['return_person'] = text
        pending = tracker.get_pending_lending_for_person(text)
        
        msg = f"👤 **Money from: {text}**\n\n"
        if pending > 0:
            msg += f"📊 Total pending: ₹{pending:,.2f}\n\n"
        msg += f"💵 Please enter the amount returned:\n"
        msg += f"💡 You can enter partial amounts!"
        
        await update.message.reply_text(msg)
        context.user_data['waiting_for'] = 'return_amount'
    
    elif waiting_for == 'return_amount':
        try:
            amount = float(text)
            person = context.user_data['return_person']
            
            success, message = tracker.return_lending(person, amount, 'wallet')
            
            if success:
                new_pending = tracker.get_pending_lending_for_person(person)
                result_msg = f"✅ **Payment Received!**\n\n{message}\n"
                
                if new_pending > 0:
                    result_msg += f"\n📊 {person} still owes: ₹{new_pending:,.2f}"
                else:
                    result_msg += f"\n🎉 {person} has cleared all debts!"
                
                await update.message.reply_text(result_msg)
            else:
                await update.message.reply_text(f"❌ {message}")
            
            context.user_data.clear()
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid amount.")
    
    elif waiting_for == 'goal_details':
        try:
            parts = text.strip().split(None, 3)
            if len(parts) >= 3:
                goal_type = parts[0]
                target = float(parts[1])
                description = parts[2]
                deadline = parts[3] if len(parts) > 3 else None
                
                prefs.add_goal(goal_type, target, description, deadline)
                
                await update.message.reply_text(
                    f"✅ **Goal Added!**\n\n"
                    f"🎯 Type: {goal_type}\n"
                    f"💰 Target: ₹{target:,.2f}\n"
                    f"📝 {description}\n" +
                    (f"📅 Deadline: {deadline}\n" if deadline else "")
                )
            else:
                await update.message.reply_text(
                    "❌ Invalid format. Please use:\n"
                    "type target description [deadline]"
                )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
        
        context.user_data.clear()
    
    elif waiting_for == 'batch_transactions':
        lines = text.strip().split('\n')
        success_count = 0
        failed_lines = []
        
        for line in lines:
            try:
                parts = line.strip().split(None, 2)
                if len(parts) >= 2:
                    amount = float(parts[0])
                    category = parts[1].lower()
                    description = parts[2] if len(parts) > 2 else f"{category} expense"
                    
                    tracker.add_transaction('subtract', 'wallet', amount, description, category=category)
                    success_count += 1
                else:
                    failed_lines.append(line)
            except:
                failed_lines.append(line)
        
        result_msg = f"✅ **Batch Entry Complete!**\n\n"
        result_msg += f"✓ Successfully added: {success_count} transactions\n"
        
        if failed_lines:
            result_msg += f"❌ Failed to parse: {len(failed_lines)} lines\n\n"
            result_msg += "Failed lines:\n"
            for fl in failed_lines[:5]:
                result_msg += f"• {fl}\n"
        
        await update.message.reply_text(result_msg)
        context.user_data.clear()

def main():
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    logger.info("Starting PayLog AI Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
