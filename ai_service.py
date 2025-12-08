import os
import requests
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import re
import time
from collections import defaultdict

logger = logging.getLogger(__name__)

class PayLogAIService:
    """
    Multi-capability AI Service for PayLog
    Acts as multiple specialized agents:
    - Parser Agent: Extract transaction data from natural language
    - Analyst Agent: Generate insights and analytics
    - Advisor Agent: Give personalized financial advice
    - Query Agent: Answer natural language questions about finances
    """
    
    def __init__(self):
        self.google_ai_key = os.getenv('GOOGLE_AI_API_KEY')
        self.google_ai_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        
        self.groq_key = os.getenv('GROQ_API_KEY')
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.groq_model = "llama-3.1-8b-instant"
        
        self.openrouter_key = os.getenv('OPENROUTER_API_KEY')
        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        self.openrouter_model = "google/gemini-2.0-flash-exp:free"
        
        self.last_request_time = 0
        self.min_request_interval = 0.5
        
        self.active_provider = self._determine_provider()
        logger.info(f"🚀 PayLog AI Service initialized with provider: {self.active_provider}")
        
    def _determine_provider(self) -> str:
        if self.google_ai_key:
            logger.info("✅ Google AI Studio (Primary) detected")
            return "google"
        elif self.groq_key:
            logger.info("✅ Groq (Backup) detected")
            return "groq"
        elif self.openrouter_key:
            logger.info("⚠️ OpenRouter available")
            return "openrouter"
        else:
            logger.warning("❌ No AI API keys - using fallback parser")
            return "fallback"
    
    def _rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def _make_request_google(self, messages: List[Dict], temperature: float = 0.7) -> Optional[str]:
        try:
            self._rate_limit()
            prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
            url = f"{self.google_ai_url}?key={self.google_ai_key}"
            
            response = requests.post(
                url=url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": 2048,
                    }
                },
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'candidates' in result and len(result['candidates']) > 0:
                return result['candidates'][0]['content']['parts'][0]['text']
            return None
            
        except Exception as e:
            logger.error(f"Google AI request failed: {e}")
            return None
    
    def _make_request_groq(self, messages: List[Dict], temperature: float = 0.7) -> Optional[str]:
        try:
            self._rate_limit()
            response = requests.post(
                url=self.groq_url,
                headers={
                    "Authorization": f"Bearer {self.groq_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.groq_model,
                    "messages": messages,
                    "temperature": temperature,
                },
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"Groq request failed: {e}")
            return None
    
    def _make_request_openrouter(self, messages: List[Dict], temperature: float = 0.7) -> Optional[str]:
        try:
            self._rate_limit()
            response = requests.post(
                url=self.openrouter_url,
                headers={
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/paylog-ai",
                    "X-Title": "PayLog AI"
                },
                json={
                    "model": self.openrouter_model,
                    "messages": messages,
                    "temperature": temperature,
                },
                timeout=30
            )
            
            if response.status_code == 429:
                logger.warning("OpenRouter rate limit hit")
                return None
                
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"OpenRouter request failed: {e}")
            return None
    
    def _make_request(self, messages: List[Dict], temperature: float = 0.7) -> Optional[str]:
        providers = []
        if self.active_provider == "google":
            providers = [("google", self._make_request_google), ("groq", self._make_request_groq), ("openrouter", self._make_request_openrouter)]
        elif self.active_provider == "groq":
            providers = [("groq", self._make_request_groq), ("google", self._make_request_google), ("openrouter", self._make_request_openrouter)]
        else:
            providers = [("openrouter", self._make_request_openrouter), ("google", self._make_request_google), ("groq", self._make_request_groq)]
        
        for name, func in providers:
            if (name == "google" and self.google_ai_key) or \
               (name == "groq" and self.groq_key) or \
               (name == "openrouter" and self.openrouter_key):
                response = func(messages, temperature)
                if response:
                    return response
                logger.info(f"⚠️ {name} failed, trying next provider")
        
        logger.warning("❌ All AI providers failed")
        return None

    # ========================================
    # PARSER AGENT - Extract transaction data
    # ========================================
    
    def parse_natural_language(self, text: str, user_context: Dict = None) -> Dict[str, Any]:
        """Parse natural language with context awareness"""
        context_info = ""
        if user_context:
            if user_context.get('last_merchant'):
                context_info += f"\nUser's last merchant: {user_context['last_merchant']}"
            if user_context.get('last_category'):
                context_info += f"\nUser's last category: {user_context['last_category']}"
            if user_context.get('usual_amounts'):
                context_info += f"\nUser's usual amounts by category: {json.dumps(user_context['usual_amounts'])}"
            if user_context.get('frequent_transactions'):
                context_info += f"\nUser's frequent transactions: {json.dumps(user_context['frequent_transactions'][:5])}"

        prompt = f"""You are a Parser Agent for an expense tracking bot. Parse this transaction and extract structured data.

Transaction text: '{text}'
{context_info}

CONTEXT-AWARE RULES:
- "same place" or "same shop" → use the last merchant from context
- "usual amount" or "regular" → infer from user's typical spending in that category
- "morning coffee" or similar shortcuts → recognize as food category, ~₹50-100
- Relative dates: "yesterday", "last week", "2 days ago" → calculate actual date

Extract:
1. amount (numeric, if "usual amount" use category average from context)
2. category (groceries, food, transport, shopping, bills, entertainment, fuel, health, lending, income, transfer, other)
3. description (what was bought/paid for)
4. merchant (store/place name, use context if "same place")
5. time_reference (today, yesterday, X days ago, specific date)
6. transaction_type (expense, income, lend, borrow, transfer)
7. wallet_type (wallet, total, or infer from context)

Return ONLY a JSON object with these keys: amount, category, description, merchant, time_reference, transaction_type, wallet_type
Use empty string for missing values.

Example: {{"amount": "500", "category": "groceries", "description": "weekly groceries", "merchant": "DMart", "time_reference": "today", "transaction_type": "expense", "wallet_type": "wallet"}}"""

        messages = [{"role": "user", "content": prompt}]
        response = self._make_request(messages, temperature=0.2)
        
        if not response:
            return self._fallback_parse(text)
        
        try:
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return parsed
            return self._fallback_parse(text)
        except:
            return self._fallback_parse(text)
    
    def _fallback_parse(self, text: str) -> Dict[str, Any]:
        """Enhanced fallback parser"""
        amount_match = re.search(r'₹?\s*(\d+(?:\.\d+)?)', text)
        amount = amount_match.group(1) if amount_match else ""
        
        category_keywords = {
            "groceries": ["grocery", "groceries", "supermarket", "dmart", "reliance", "big bazaar", "more", "vegetables", "fruits"],
            "food": ["food", "lunch", "dinner", "breakfast", "meal", "restaurant", "cafe", "zomato", "swiggy", "burger", "pizza", "biryani", "coffee", "tea", "snacks"],
            "transport": ["transport", "uber", "ola", "metro", "bus", "auto", "taxi", "travel", "cab", "rapido", "rickshaw"],
            "fuel": ["fuel", "petrol", "diesel", "gas", "cng", "pump"],
            "shopping": ["shopping", "clothes", "amazon", "flipkart", "mall", "myntra", "ajio", "purchase", "buy"],
            "bills": ["bill", "electricity", "water", "internet", "mobile", "recharge", "broadband", "wifi", "rent", "emi"],
            "entertainment": ["movie", "entertainment", "netflix", "spotify", "prime", "hotstar", "game", "concert", "party"],
            "health": ["medicine", "doctor", "hospital", "pharmacy", "medical", "clinic", "apollo", "health", "gym"],
            "lending": ["lent", "lend", "gave", "borrowed", "loan"],
            "income": ["salary", "income", "received", "earned", "got paid", "freelance"]
        }
        
        text_lower = text.lower()
        category = "other"
        for cat, keywords in category_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                category = cat
                break
        
        merchant = ""
        for keyword in ["at", "from", "in", "@"]:
            if keyword in text_lower:
                parts = text_lower.split(keyword)
                if len(parts) > 1:
                    potential_merchant = parts[1].strip().split()[0] if parts[1].strip().split() else ""
                    if len(potential_merchant) > 2:
                        merchant = potential_merchant.title()
                    break
        
        transaction_type = "expense"
        if any(word in text_lower for word in ["received", "income", "salary", "got", "earned"]):
            transaction_type = "income"
        elif any(word in text_lower for word in ["lent", "gave to", "loan to"]):
            transaction_type = "lend"
        
        time_ref = "today"
        if "yesterday" in text_lower:
            time_ref = "yesterday"
        elif "last week" in text_lower:
            time_ref = "7 days ago"
        
        return {
            "amount": amount,
            "category": category,
            "description": text,
            "merchant": merchant,
            "time_reference": time_ref,
            "transaction_type": transaction_type,
            "wallet_type": "wallet"
        }

    # ========================================
    # ANALYST AGENT - Generate insights
    # ========================================
    
    def get_spending_insights(self, transactions_data: str, period: str = "month") -> str:
        """Generate comprehensive spending insights"""
        prompt = f"""You are an Analyst Agent for personal finance. Analyze these transactions and provide actionable insights.

Period: {period}
Transactions:
{transactions_data}

Provide a concise analysis covering:
1. 📊 Spending patterns and trends
2. 📈 Category breakdown with percentages
3. ⚠️ Any concerning patterns or overspending
4. 💡 One specific actionable recommendation

Keep response under 200 words. Use ₹ symbol. Be conversational and helpful."""

        messages = [{"role": "user", "content": prompt}]
        response = self._make_request(messages, temperature=0.7)
        return response or "Unable to generate insights. Your spending appears normal."
    
    def detect_anomaly(self, amount: float, category: str, historical_avg: float, category_avg: float = 0) -> Optional[str]:
        """Detect unusual transactions with detailed explanation"""
        alerts = []
        
        if historical_avg > 0 and amount > historical_avg * 5:
            multiplier = amount / historical_avg
            alerts.append(f"🔔 **Unusual Transaction Alert!**\n₹{amount:,.0f} for {category} is {multiplier:.1f}x your daily average of ₹{historical_avg:,.0f}")
        
        if category_avg > 0 and amount > category_avg * 3:
            multiplier = amount / category_avg
            alerts.append(f"⚠️ This {category} expense is {multiplier:.1f}x your typical {category} spending of ₹{category_avg:,.0f}")
        
        return "\n".join(alerts) if alerts else None
    
    def analyze_spending_trend(self, transactions: List[Dict], category: str = None) -> Dict[str, Any]:
        """Analyze spending trends over time"""
        if not transactions:
            return {"trend": "stable", "change_percent": 0, "message": "Not enough data"}
        
        now = datetime.now()
        
        this_week = []
        last_week = []
        this_month = []
        last_month = []
        
        for t in transactions:
            try:
                trans_date = datetime.strptime(str(t['date']), '%d/%m/%Y')
                if t['type'] != 'subtract':
                    continue
                if category and t.get('category', 'other') != category:
                    continue
                    
                amount = float(t['amount'])
                days_ago = (now - trans_date).days
                
                if days_ago <= 7:
                    this_week.append(amount)
                elif days_ago <= 14:
                    last_week.append(amount)
                    
                if days_ago <= 30:
                    this_month.append(amount)
                elif days_ago <= 60:
                    last_month.append(amount)
            except:
                continue
        
        result = {
            "this_week_total": sum(this_week),
            "last_week_total": sum(last_week),
            "this_month_total": sum(this_month),
            "last_month_total": sum(last_month),
            "trend": "stable",
            "change_percent": 0
        }
        
        if sum(last_week) > 0:
            change = ((sum(this_week) - sum(last_week)) / sum(last_week)) * 100
            result["change_percent"] = change
            if change > 20:
                result["trend"] = "increasing"
            elif change < -20:
                result["trend"] = "decreasing"
        
        return result

    # ========================================
    # ADVISOR AGENT - Financial advice
    # ========================================
    
    def get_financial_advice(self, user_data: Dict) -> str:
        """Generate personalized financial advice"""
        prompt = f"""You are a Financial Advisor Agent. Based on this user's financial data, provide personalized advice.

User Data:
- Monthly income: ₹{user_data.get('income', 0):,.0f}
- Monthly expenses: ₹{user_data.get('expenses', 0):,.0f}
- Current savings: ₹{user_data.get('savings', 0):,.0f}
- Top spending categories: {user_data.get('top_categories', [])}
- Spending trend: {user_data.get('trend', 'stable')}
- Financial goals: {user_data.get('goals', [])}

Provide:
1. One specific praise for good behavior (if any)
2. One specific concern to address
3. One actionable tip to improve finances

Keep response conversational, under 150 words. Use ₹ symbol."""

        messages = [{"role": "user", "content": prompt}]
        response = self._make_request(messages, temperature=0.7)
        return response or "Keep tracking your expenses and try to save at least 20% of your income!"
    
    def suggest_budget_cuts(self, transactions: List[Dict], target_savings: float = 0) -> str:
        """Suggest specific areas to cut spending"""
        category_totals = defaultdict(float)
        
        for t in transactions:
            if t.get('type') == 'subtract':
                try:
                    category = t.get('category', 'other') or 'other'
                    category_totals[category] += float(t['amount'])
                except:
                    continue
        
        sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        
        prompt = f"""You are a Budget Advisor. Suggest specific cuts based on this spending:

Category breakdown (monthly):
{chr(10).join([f"- {cat}: ₹{amt:,.0f}" for cat, amt in sorted_categories])}

Target savings: ₹{target_savings:,.0f} (if 0, suggest general improvements)

Provide 2-3 specific, actionable suggestions to reduce spending. Be realistic.
Example: "Cut ₹2000 from dining out by cooking 3 more meals at home per week"

Keep response under 100 words. Use ₹ symbol."""

        messages = [{"role": "user", "content": prompt}]
        response = self._make_request(messages, temperature=0.7)
        return response or "Consider reducing discretionary spending on entertainment and dining out."

    # ========================================
    # PREDICTOR - Forecasting & Alerts
    # ========================================
    
    def predict_money_runout(self, current_balance: float, daily_burn_rate: float, monthly_income: float = 0, income_date: int = 1) -> Dict[str, Any]:
        """Predict when money will run out"""
        if daily_burn_rate <= 0:
            return {
                "days_left": 999,
                "runout_date": None,
                "message": "Your spending rate is very low. Great job saving!"
            }
        
        days_left = int(current_balance / daily_burn_rate)
        runout_date = datetime.now() + timedelta(days=days_left)
        
        message = ""
        if days_left < 7:
            message = f"⚠️ **Critical Alert!** You'll run out of money in {days_left} days (by {runout_date.strftime('%b %d')})"
        elif days_left < 14:
            message = f"🔔 **Warning:** At current pace, money runs out by {runout_date.strftime('%b %d')} ({days_left} days)"
        elif days_left < 30:
            message = f"📊 At current spending, you have about {days_left} days of runway (until {runout_date.strftime('%b %d')})"
        else:
            message = f"✅ Good pace! You have {days_left}+ days of runway"
        
        return {
            "days_left": days_left,
            "runout_date": runout_date.strftime('%Y-%m-%d'),
            "message": message,
            "daily_burn_rate": daily_burn_rate
        }
    
    def check_budget_status(self, spent: float, budget: float, period: str = "month") -> Dict[str, Any]:
        """Check budget status and generate alerts"""
        if budget <= 0:
            return {"status": "no_budget", "message": "No budget set"}
        
        percentage = (spent / budget) * 100
        remaining = budget - spent
        
        status = "good"
        message = ""
        
        if percentage >= 100:
            status = "exceeded"
            message = f"🚨 **Budget Exceeded!** You've spent ₹{spent:,.0f} against a ₹{budget:,.0f} {period}ly budget (+₹{abs(remaining):,.0f} over)"
        elif percentage >= 90:
            status = "critical"
            message = f"⚠️ **Alert:** You're at {percentage:.0f}% of your {period}ly budget. Only ₹{remaining:,.0f} left!"
        elif percentage >= 80:
            status = "warning"
            message = f"🔔 Heads up! You've used {percentage:.0f}% of your {period}ly budget. ₹{remaining:,.0f} remaining."
        elif percentage >= 50:
            status = "moderate"
            message = f"📊 You're at {percentage:.0f}% of budget. ₹{remaining:,.0f} left for the {period}."
        else:
            status = "good"
            message = f"✅ Great! Only {percentage:.0f}% of budget used. ₹{remaining:,.0f} available."
        
        return {
            "status": status,
            "percentage": percentage,
            "spent": spent,
            "budget": budget,
            "remaining": remaining,
            "message": message
        }

    # ========================================
    # FINANCIAL HEALTH SCORE
    # ========================================
    
    def calculate_financial_health_score(self, data: Dict) -> Dict[str, Any]:
        """Calculate comprehensive financial health score (0-100)"""
        score = 50  # Base score
        factors = []
        
        # Factor 1: Savings Rate (max 25 points)
        income = data.get('income', 0)
        expenses = data.get('expenses', 0)
        if income > 0:
            savings_rate = ((income - expenses) / income) * 100
            if savings_rate >= 30:
                score += 25
                factors.append(("Savings Rate", "+25", f"Excellent! Saving {savings_rate:.0f}%"))
            elif savings_rate >= 20:
                score += 20
                factors.append(("Savings Rate", "+20", f"Good savings at {savings_rate:.0f}%"))
            elif savings_rate >= 10:
                score += 10
                factors.append(("Savings Rate", "+10", f"Moderate savings at {savings_rate:.0f}%"))
            elif savings_rate >= 0:
                score += 5
                factors.append(("Savings Rate", "+5", f"Low savings at {savings_rate:.0f}%"))
            else:
                score -= 10
                factors.append(("Savings Rate", "-10", f"Spending more than earning!"))
        
        # Factor 2: Budget Adherence (max 20 points)
        budget = data.get('budget', 0)
        if budget > 0:
            budget_usage = (expenses / budget) * 100
            if budget_usage <= 80:
                score += 20
                factors.append(("Budget", "+20", "Well under budget"))
            elif budget_usage <= 100:
                score += 10
                factors.append(("Budget", "+10", "Within budget"))
            else:
                score -= 15
                factors.append(("Budget", "-15", f"Over budget by {budget_usage - 100:.0f}%"))
        
        # Factor 3: Spending Trend (max 15 points)
        trend = data.get('trend', 'stable')
        if trend == 'decreasing':
            score += 15
            factors.append(("Trend", "+15", "Spending decreasing - great progress!"))
        elif trend == 'stable':
            score += 10
            factors.append(("Trend", "+10", "Stable spending pattern"))
        else:
            score -= 5
            factors.append(("Trend", "-5", "Spending is increasing"))
        
        # Factor 4: Emergency Fund (max 15 points)
        savings = data.get('savings', 0)
        monthly_expenses = expenses if expenses > 0 else 30000
        months_covered = savings / monthly_expenses if monthly_expenses > 0 else 0
        if months_covered >= 6:
            score += 15
            factors.append(("Emergency Fund", "+15", f"{months_covered:.1f} months of expenses saved"))
        elif months_covered >= 3:
            score += 10
            factors.append(("Emergency Fund", "+10", f"{months_covered:.1f} months of expenses saved"))
        elif months_covered >= 1:
            score += 5
            factors.append(("Emergency Fund", "+5", f"Only {months_covered:.1f} months saved"))
        else:
            score -= 5
            factors.append(("Emergency Fund", "-5", "Need to build emergency fund"))
        
        # Factor 5: Goal Progress (max 10 points)
        goals = data.get('goals', [])
        active_goals = [g for g in goals if not g.get('completed', False)]
        if active_goals:
            goal_progress = sum(g.get('progress', 0) for g in active_goals) / len(active_goals)
            if goal_progress >= 75:
                score += 10
                factors.append(("Goals", "+10", "Great progress on financial goals"))
            elif goal_progress >= 50:
                score += 5
                factors.append(("Goals", "+5", "Making progress on goals"))
            else:
                factors.append(("Goals", "0", "Goals need attention"))
        
        # Clamp score between 0 and 100
        score = max(0, min(100, score))
        
        # Generate message based on score
        if score >= 80:
            grade = "A"
            message = "🌟 Excellent financial health! Keep up the great work."
        elif score >= 60:
            grade = "B"
            message = "👍 Good financial health with room for improvement."
        elif score >= 40:
            grade = "C"
            message = "⚠️ Fair financial health. Focus on the areas below."
        else:
            grade = "D"
            message = "🚨 Financial health needs attention. Let's work on improvements."
        
        return {
            "score": score,
            "grade": grade,
            "message": message,
            "factors": factors,
            "timestamp": datetime.now().isoformat()
        }

    # ========================================
    # QUERY AGENT - Natural language Q&A
    # ========================================
    
    def answer_query(self, query: str, transactions: List[Dict], user_data: Dict = None) -> str:
        """Answer natural language questions about finances"""
        
        # Prepare transaction summary
        recent_trans = transactions[-50:] if transactions else []
        trans_summary = "\n".join([
            f"{t['date']}: {t['type']} ₹{t['amount']} - {t.get('description', '')} ({t.get('category', 'other')})"
            for t in recent_trans
        ])
        
        # Calculate some stats for context
        total_expenses = sum(float(t['amount']) for t in transactions if t.get('type') == 'subtract')
        total_income = sum(float(t['amount']) for t in transactions if t.get('type') == 'add')
        
        category_totals = defaultdict(float)
        for t in transactions:
            if t.get('type') == 'subtract':
                category_totals[t.get('category', 'other')] += float(t['amount'])
        
        user_context = ""
        if user_data:
            user_context = f"""
User Context:
- Total Balance: ₹{user_data.get('total_balance', 0):,.0f}
- Wallet Balance: ₹{user_data.get('wallet_balance', 0):,.0f}
- Monthly Budget: ₹{user_data.get('budget', 0):,.0f}
- Goals: {user_data.get('goals', [])}
"""
        
        prompt = f"""You are a Query Agent for personal finance. Answer the user's question based on their financial data.

User Question: "{query}"

Recent Transactions (last 50):
{trans_summary}

Summary Stats:
- Total Expenses: ₹{total_expenses:,.0f}
- Total Income: ₹{total_income:,.0f}
- Category Breakdown: {dict(category_totals)}
{user_context}

Rules:
1. Answer conversationally and helpfully
2. Use specific numbers from their data
3. If comparing periods, calculate accurately
4. Provide actionable insights when relevant
5. Use ₹ symbol for amounts
6. Keep response concise (under 150 words)

If the question cannot be answered from the data, say so politely and suggest what data is needed."""

        messages = [{"role": "user", "content": prompt}]
        response = self._make_request(messages, temperature=0.7)
        return response or "I couldn't analyze that query. Try asking about specific spending categories or time periods."

    # ========================================
    # SMART NOTIFICATIONS
    # ========================================
    
    def generate_weekly_summary(self, transactions: List[Dict], user_data: Dict = None) -> str:
        """Generate weekly spending summary"""
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)
        
        this_week = []
        last_week = []
        
        for t in transactions:
            try:
                trans_date = datetime.strptime(str(t['date']), '%d/%m/%Y')
                if t['type'] != 'subtract':
                    continue
                    
                amount = float(t['amount'])
                if trans_date >= week_ago:
                    this_week.append({'amount': amount, 'category': t.get('category', 'other')})
                elif trans_date >= two_weeks_ago:
                    last_week.append({'amount': amount, 'category': t.get('category', 'other')})
            except:
                continue
        
        this_week_total = sum(t['amount'] for t in this_week)
        last_week_total = sum(t['amount'] for t in last_week)
        
        # Category breakdown for this week
        category_totals = defaultdict(float)
        for t in this_week:
            category_totals[t['category']] += t['amount']
        
        top_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Calculate savings/difference
        difference = last_week_total - this_week_total
        
        summary = f"📊 **Weekly Summary**\n\n"
        summary += f"💰 This week: ₹{this_week_total:,.0f}\n"
        summary += f"📅 Last week: ₹{last_week_total:,.0f}\n\n"
        
        if difference > 0:
            summary += f"🎉 You saved ₹{difference:,.0f} compared to last week!\n\n"
        elif difference < 0:
            summary += f"📈 You spent ₹{abs(difference):,.0f} more than last week.\n\n"
        else:
            summary += f"➡️ Same spending as last week.\n\n"
        
        if top_categories:
            summary += "📂 **Top Categories:**\n"
            for cat, amt in top_categories:
                summary += f"  • {cat.title()}: ₹{amt:,.0f}\n"
        
        return summary
    
    def check_goal_progress(self, goals: List[Dict], current_savings: float) -> List[str]:
        """Check progress on financial goals and generate notifications"""
        notifications = []
        
        for goal in goals:
            if goal.get('completed', False):
                continue
                
            target = goal.get('target', 0)
            current = goal.get('current', current_savings)
            description = goal.get('description', 'Savings Goal')
            
            if target <= 0:
                continue
            
            progress = (current / target) * 100
            remaining = target - current
            
            if progress >= 100:
                notifications.append(f"🎉 **Goal Achieved!** You've reached your {description} goal of ₹{target:,.0f}!")
            elif progress >= 90:
                notifications.append(f"🔥 Almost there! Only ₹{remaining:,.0f} more to your {description} goal!")
            elif progress >= 75:
                notifications.append(f"💪 Great progress! {progress:.0f}% towards your {description} goal. ₹{remaining:,.0f} to go!")
            elif progress >= 50:
                notifications.append(f"📊 Halfway there! {progress:.0f}% to your {description} goal of ₹{target:,.0f}")
        
        return notifications

    # ========================================
    # HELPER METHODS
    # ========================================
    
    def detect_spending_spike(self, amount: float, daily_average: float, category: str) -> Optional[str]:
        """Detect if a transaction is significantly higher than average"""
        if daily_average > 0 and amount >= daily_average * 3:
            return f"⚠️ High spending alert! ₹{amount:,.0f} on {category} is {amount/daily_average:.1f}x your daily average of ₹{daily_average:,.0f}"
        return None
    
    def suggest_category(self, description: str, amount: float, historical_patterns: List[Dict]) -> str:
        """Suggest category based on description and history"""
        if not historical_patterns:
            return self._fallback_parse(description).get('category', 'other')
        
        patterns_text = "\n".join([f"- {p['desc']}: {p['cat']}" for p in historical_patterns[:10]])
        
        prompt = f"""Based on these past transactions, suggest the most likely category:

Past patterns:
{patterns_text}

New transaction:
Description: {description}
Amount: ₹{amount}

Return ONLY the category name (groceries, food, transport, shopping, bills, entertainment, fuel, health, other)"""

        messages = [{"role": "user", "content": prompt}]
        response = self._make_request(messages, temperature=0.3)
        
        if response:
            return response.strip().lower()
        return self._fallback_parse(description).get('category', 'other')
    
    def suggest_wallet_transfer(self, wallet_balance: float, total_balance: float, spending_pattern: str = "") -> Optional[str]:
        """Suggest wallet transfer when balance is low"""
        if wallet_balance < 500 and total_balance > 2000:
            suggested = min(5000, total_balance * 0.3)
            return f"💡 Your wallet is low (₹{wallet_balance:,.0f}). Consider transferring ₹{suggested:,.0f} from Total Stack."
        return None
    
    def analyze_lending_patterns(self, lending_data: str) -> str:
        """Analyze lending patterns and provide insights"""
        if not lending_data:
            return "No lending data available to analyze."
        
        prompt = f"""Analyze these lending records and provide insights:

{lending_data}

Provide:
1. Pattern observation (who borrows most, frequency)
2. Risk assessment (long outstanding loans)
3. One recommendation for better lending management

Keep response under 100 words. Be helpful and conversational."""

        messages = [{"role": "user", "content": prompt}]
        response = self._make_request(messages, temperature=0.7)
        return response or "Unable to analyze lending patterns at the moment."


# Alias for backward compatibility
GeminiAIService = PayLogAIService
