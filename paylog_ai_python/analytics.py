import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict, Counter
import logging
import json

logger = logging.getLogger(__name__)

class ExpenseAnalytics:
    """Enhanced analytics with goal tracking, predictions, and smart insights"""
    
    @staticmethod
    def calculate_daily_average(transactions: List[Dict], days: int = 30) -> float:
        if not transactions:
            return 0.0
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_expenses = [
            float(t['amount']) for t in transactions
            if t['type'] == 'subtract' and 
            datetime.strptime(str(t['date']), '%d/%m/%Y') >= cutoff_date
        ]
        
        return sum(recent_expenses) / days if days > 0 else 0.0
    
    @staticmethod
    def calculate_category_average(transactions: List[Dict], category: str, days: int = 30) -> float:
        """Calculate average spending for a specific category"""
        if not transactions:
            return 0.0
        
        cutoff_date = datetime.now() - timedelta(days=days)
        category_expenses = [
            float(t['amount']) for t in transactions
            if t['type'] == 'subtract' and 
            t.get('category', 'other') == category and
            datetime.strptime(str(t['date']), '%d/%m/%Y') >= cutoff_date
        ]
        
        return sum(category_expenses) / max(len(category_expenses), 1)
    
    @staticmethod
    def get_category_breakdown(transactions: List[Dict], period_days: int = 30) -> Dict[str, float]:
        cutoff_date = datetime.now() - timedelta(days=period_days)
        category_totals = defaultdict(float)
        
        for t in transactions:
            try:
                if t['type'] == 'subtract':
                    trans_date = datetime.strptime(str(t['date']), '%d/%m/%Y')
                    if trans_date >= cutoff_date:
                        category = t.get('category', 'other') or 'other'
                        amount = float(t['amount'])
                        category_totals[category] += amount
            except:
                continue
        
        total = sum(category_totals.values())
        if total == 0:
            return {}
        
        return {cat: (amt/total)*100 for cat, amt in category_totals.items()}
    
    @staticmethod
    def get_category_totals(transactions: List[Dict], period_days: int = 30) -> Dict[str, float]:
        """Get absolute totals per category"""
        cutoff_date = datetime.now() - timedelta(days=period_days)
        category_totals = defaultdict(float)
        
        for t in transactions:
            try:
                if t['type'] == 'subtract':
                    trans_date = datetime.strptime(str(t['date']), '%d/%m/%Y')
                    if trans_date >= cutoff_date:
                        category = t.get('category', 'other') or 'other'
                        amount = float(t['amount'])
                        category_totals[category] += amount
            except:
                continue
        
        return dict(category_totals)
    
    @staticmethod
    def detect_trend(transactions: List[Dict], category: Optional[str] = None, weeks: int = 4) -> str:
        if len(transactions) < 2:
            return "Not enough data"
        
        now = datetime.now()
        week_totals = []
        
        for week_offset in range(weeks):
            week_start = now - timedelta(weeks=week_offset+1)
            week_end = now - timedelta(weeks=week_offset)
            
            week_total = 0
            for t in transactions:
                try:
                    trans_date = datetime.strptime(str(t['date']), '%d/%m/%Y')
                    if week_start <= trans_date < week_end and t['type'] == 'subtract':
                        t_category = t.get('category', 'other') or 'other'
                        if category is None or t_category == category:
                            week_total += float(t['amount'])
                except:
                    continue
            week_totals.append(week_total)
        
        if len(week_totals) < 2:
            return "stable"
        
        week_totals.reverse()
        
        recent_avg = sum(week_totals[-2:]) / 2 if len(week_totals) >= 2 else week_totals[-1]
        older_avg = sum(week_totals[:2]) / 2 if len(week_totals) >= 2 else week_totals[0]
        
        if older_avg == 0:
            return "increasing" if recent_avg > 0 else "stable"
        
        change = ((recent_avg - older_avg) / older_avg) * 100
        
        if change > 15:
            return f"increasing {abs(change):.0f}%"
        elif change < -15:
            return f"decreasing {abs(change):.0f}%"
        else:
            return "stable"
    
    @staticmethod
    def forecast_month_end(transactions: List[Dict]) -> Tuple[float, str]:
        import calendar
        
        now = datetime.now()
        month_start = now.replace(day=1)
        days_elapsed = (now - month_start).days + 1
        
        # Use calendar.monthrange for safe days-in-month calculation (handles all months including December)
        _, days_in_month = calendar.monthrange(now.year, now.month)
        
        month_expenses = sum(
            float(t['amount']) for t in transactions
            if t['type'] == 'subtract' and 
            datetime.strptime(str(t['date']), '%d/%m/%Y') >= month_start
        )
        
        daily_rate = month_expenses / days_elapsed if days_elapsed > 0 else 0
        forecast = daily_rate * days_in_month
        
        pace = "normal"
        if daily_rate > 2000:
            pace = "very high"
        elif daily_rate > 1000:
            pace = "high"
        elif daily_rate < 300:
            pace = "low"
        
        return forecast, pace
    
    @staticmethod
    def get_burn_rate(wallet_balance: float, transactions: List[Dict], days: int = 7) -> Tuple[float, int]:
        cutoff = datetime.now() - timedelta(days=days)
        
        wallet_expenses = sum(
            float(t['amount']) for t in transactions
            if t['type'] == 'subtract' and 
            t.get('wallet_type') == 'wallet' and
            datetime.strptime(str(t['date']), '%d/%m/%Y') >= cutoff
        )
        
        daily_burn = wallet_expenses / days if days > 0 else 0
        days_left = int(wallet_balance / daily_burn) if daily_burn > 0 else 999
        
        return daily_burn, days_left
    
    @staticmethod
    def get_frequent_transactions(transactions: List[Dict], limit: int = 10) -> List[Dict]:
        if not transactions:
            return []
        
        recent = transactions[-100:]
        
        transaction_patterns = []
        for t in recent:
            if t['type'] == 'subtract':
                amount = float(t['amount'])
                desc = str(t.get('description', '')).lower()
                category = t.get('category', 'other') or 'other'
                
                pattern = f"{desc}_{category}_{amount}"
                transaction_patterns.append({
                    'pattern': pattern,
                    'amount': amount,
                    'category': category,
                    'description': desc
                })
        
        pattern_counts = Counter(tp['pattern'] for tp in transaction_patterns)
        
        frequent = []
        seen_patterns = set()
        for tp in transaction_patterns:
            if tp['pattern'] in seen_patterns:
                continue
            if pattern_counts[tp['pattern']] >= 2:
                frequent.append({
                    'amount': tp['amount'],
                    'category': tp['category'],
                    'description': tp['description'],
                    'count': pattern_counts[tp['pattern']]
                })
                seen_patterns.add(tp['pattern'])
        
        return sorted(frequent, key=lambda x: x['count'], reverse=True)[:limit]
    
    @staticmethod
    def analyze_lending(lending_records: List[Dict]) -> Dict[str, Any]:
        if not lending_records:
            return {
                'total_lent': 0,
                'total_returned': 0,
                'pending': 0,
                'avg_amount': 0,
                'avg_return_days': 0,
                'pending_persons': []
            }
        
        total_lent = sum(float(r['amount']) for r in lending_records if r['status'] == 'lent')
        total_returned = sum(float(r['amount']) for r in lending_records if r['status'] == 'returned')
        pending = total_lent - total_returned
        
        amounts = [float(r['amount']) for r in lending_records]
        avg_amount = sum(amounts) / len(amounts) if amounts else 0
        
        return_times = []
        for r in lending_records:
            if r['status'] == 'returned' and r.get('return_date'):
                try:
                    lent_date = datetime.strptime(str(r['date']), '%d/%m/%Y')
                    return_date = datetime.strptime(str(r['return_date']), '%d/%m/%Y')
                    days = (return_date - lent_date).days
                    return_times.append(days)
                except:
                    continue
        
        avg_return_days = sum(return_times) / len(return_times) if return_times else 0
        
        pending_persons = []
        person_totals = defaultdict(float)
        for r in lending_records:
            if r['status'] == 'lent':
                person_totals[r['person']] += float(r['amount'])
        
        for person, amount in person_totals.items():
            if amount > 0:
                pending_persons.append({'person': person, 'amount': amount})
        
        return {
            'total_lent': total_lent,
            'total_returned': total_returned,
            'pending': pending,
            'avg_amount': avg_amount,
            'avg_return_days': avg_return_days,
            'pending_persons': sorted(pending_persons, key=lambda x: x['amount'], reverse=True)
        }
    
    # ========================================
    # WEEKLY/MONTHLY COMPARISONS
    # ========================================
    
    @staticmethod
    def compare_periods(transactions: List[Dict], period: str = 'week') -> Dict[str, Any]:
        """Compare current period with previous period"""
        now = datetime.now()
        
        if period == 'week':
            current_start = now - timedelta(days=7)
            previous_start = now - timedelta(days=14)
            previous_end = now - timedelta(days=7)
        elif period == 'month':
            current_start = now.replace(day=1)
            if now.month == 1:
                previous_start = now.replace(year=now.year-1, month=12, day=1)
            else:
                previous_start = now.replace(month=now.month-1, day=1)
            previous_end = current_start - timedelta(days=1)
        else:
            return {}
        
        current_expenses = 0
        previous_expenses = 0
        current_by_category = defaultdict(float)
        previous_by_category = defaultdict(float)
        
        for t in transactions:
            try:
                if t['type'] != 'subtract':
                    continue
                trans_date = datetime.strptime(str(t['date']), '%d/%m/%Y')
                amount = float(t['amount'])
                category = t.get('category', 'other') or 'other'
                
                if trans_date >= current_start:
                    current_expenses += amount
                    current_by_category[category] += amount
                elif previous_start <= trans_date < previous_end:
                    previous_expenses += amount
                    previous_by_category[category] += amount
            except:
                continue
        
        difference = current_expenses - previous_expenses
        change_percent = ((difference) / previous_expenses * 100) if previous_expenses > 0 else 0
        
        return {
            'current_total': current_expenses,
            'previous_total': previous_expenses,
            'difference': difference,
            'change_percent': change_percent,
            'current_by_category': dict(current_by_category),
            'previous_by_category': dict(previous_by_category),
            'period': period,
            'saved': difference < 0
        }
    
    # ========================================
    # GOAL TRACKING
    # ========================================
    
    @staticmethod
    def calculate_goal_progress(goals: List[Dict], current_savings: float, transactions: List[Dict] = None) -> List[Dict]:
        """Calculate progress for each goal"""
        results = []
        
        for goal in goals:
            target = goal.get('target', 0)
            goal_type = goal.get('type', 'savings')
            description = goal.get('description', 'Goal')
            deadline = goal.get('deadline')
            
            if target <= 0:
                continue
            
            if goal_type == 'savings':
                current = current_savings
            elif goal_type == 'spending_limit' and transactions:
                # Calculate current spending for the period
                current = sum(
                    float(t['amount']) for t in transactions
                    if t['type'] == 'subtract'
                )
            else:
                current = goal.get('current', 0)
            
            progress = (current / target) * 100 if target > 0 else 0
            remaining = target - current
            
            # Calculate days to deadline
            days_remaining = None
            on_track = True
            if deadline:
                try:
                    deadline_date = datetime.strptime(deadline, '%Y-%m-%d')
                    days_remaining = (deadline_date - datetime.now()).days
                    
                    # Check if on track
                    if days_remaining > 0 and goal_type == 'savings':
                        required_daily = remaining / days_remaining
                        # Estimate based on recent savings rate
                        on_track = progress >= (100 - (days_remaining / 30) * 100) if days_remaining < 30 else True
                except:
                    pass
            
            results.append({
                'description': description,
                'type': goal_type,
                'target': target,
                'current': current,
                'progress': min(progress, 100),
                'remaining': max(remaining, 0),
                'days_remaining': days_remaining,
                'on_track': on_track,
                'completed': progress >= 100
            })
        
        return results
    
    @staticmethod
    def suggest_daily_savings(goal_target: float, current_savings: float, deadline_days: int) -> float:
        """Calculate required daily savings to reach goal"""
        if deadline_days <= 0:
            return 0
        
        remaining = goal_target - current_savings
        if remaining <= 0:
            return 0
        
        return remaining / deadline_days
    
    # ========================================
    # BUDGET ANALYSIS
    # ========================================
    
    @staticmethod
    def analyze_budget(transactions: List[Dict], budgets: Dict[str, float], period_days: int = 30) -> Dict[str, Any]:
        """Analyze spending against budgets"""
        cutoff_date = datetime.now() - timedelta(days=period_days)
        
        category_spending = defaultdict(float)
        for t in transactions:
            try:
                if t['type'] == 'subtract':
                    trans_date = datetime.strptime(str(t['date']), '%d/%m/%Y')
                    if trans_date >= cutoff_date:
                        category = t.get('category', 'other') or 'other'
                        category_spending[category] += float(t['amount'])
            except:
                continue
        
        results = {}
        total_budget = sum(budgets.values())
        total_spent = sum(category_spending.values())
        
        for category, budget in budgets.items():
            spent = category_spending.get(category, 0)
            remaining = budget - spent
            percentage = (spent / budget * 100) if budget > 0 else 0
            
            if percentage >= 100:
                status = 'exceeded'
            elif percentage >= 90:
                status = 'critical'
            elif percentage >= 75:
                status = 'warning'
            else:
                status = 'good'
            
            results[category] = {
                'budget': budget,
                'spent': spent,
                'remaining': remaining,
                'percentage': percentage,
                'status': status
            }
        
        return {
            'categories': results,
            'total_budget': total_budget,
            'total_spent': total_spent,
            'total_remaining': total_budget - total_spent,
            'overall_percentage': (total_spent / total_budget * 100) if total_budget > 0 else 0
        }
    
    # ========================================
    # CONTEXT-AWARE HELPERS
    # ========================================
    
    @staticmethod
    def get_usual_amounts(transactions: List[Dict], limit: int = 50) -> Dict[str, float]:
        """Get usual spending amounts by category"""
        category_amounts = defaultdict(list)
        
        for t in transactions[-limit:]:
            if t['type'] == 'subtract':
                category = t.get('category', 'other') or 'other'
                category_amounts[category].append(float(t['amount']))
        
        return {
            cat: sum(amounts) / len(amounts)
            for cat, amounts in category_amounts.items()
            if amounts
        }
    
    @staticmethod
    def get_last_merchant(transactions: List[Dict]) -> Optional[str]:
        """Get the last used merchant"""
        for t in reversed(transactions):
            merchant = t.get('merchant', '')
            if merchant and merchant.strip():
                return merchant
        return None
    
    @staticmethod
    def get_frequent_merchants(transactions: List[Dict], limit: int = 5) -> List[Dict]:
        """Get frequently used merchants"""
        merchant_counts = Counter()
        merchant_amounts = defaultdict(list)
        
        for t in transactions:
            if t['type'] == 'subtract':
                merchant = t.get('merchant', '').strip()
                if merchant:
                    merchant_counts[merchant] += 1
                    merchant_amounts[merchant].append(float(t['amount']))
        
        result = []
        for merchant, count in merchant_counts.most_common(limit):
            amounts = merchant_amounts[merchant]
            result.append({
                'merchant': merchant,
                'count': count,
                'avg_amount': sum(amounts) / len(amounts),
                'total': sum(amounts)
            })
        
        return result
    
    # ========================================
    # PREDICTION HELPERS
    # ========================================
    
    @staticmethod
    def predict_runout_date(balance: float, transactions: List[Dict], days_history: int = 14) -> Dict[str, Any]:
        """Predict when balance will run out"""
        daily_burn, _ = ExpenseAnalytics.get_burn_rate(balance, transactions, days_history)
        
        if daily_burn <= 0:
            return {
                'days_left': 999,
                'runout_date': None,
                'daily_burn': 0,
                'message': 'No significant spending detected'
            }
        
        days_left = int(balance / daily_burn)
        runout_date = datetime.now() + timedelta(days=days_left)
        
        if days_left < 7:
            severity = 'critical'
        elif days_left < 14:
            severity = 'warning'
        elif days_left < 30:
            severity = 'moderate'
        else:
            severity = 'good'
        
        return {
            'days_left': days_left,
            'runout_date': runout_date.strftime('%Y-%m-%d'),
            'runout_date_formatted': runout_date.strftime('%b %d, %Y'),
            'daily_burn': daily_burn,
            'severity': severity
        }
    
    @staticmethod
    def get_income_expense_summary(transactions: List[Dict], period_days: int = 30) -> Dict[str, float]:
        """Get income vs expense summary"""
        cutoff_date = datetime.now() - timedelta(days=period_days)
        
        income = 0
        expenses = 0
        
        for t in transactions:
            try:
                trans_date = datetime.strptime(str(t['date']), '%d/%m/%Y')
                if trans_date >= cutoff_date:
                    amount = float(t['amount'])
                    if t['type'] == 'add':
                        income += amount
                    elif t['type'] == 'subtract':
                        expenses += amount
            except:
                continue
        
        savings = income - expenses
        savings_rate = (savings / income * 100) if income > 0 else 0
        
        return {
            'income': income,
            'expenses': expenses,
            'savings': savings,
            'savings_rate': savings_rate,
            'period_days': period_days
        }
