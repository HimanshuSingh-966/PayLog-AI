import json
import os
from typing import Dict, Any, Optional, List
from collections import defaultdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class UserPreferences:
    """Enhanced user preferences with goals, budgets, and context memory"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.prefs_file = f"user_prefs_{user_id}.json"
        self.data = self._load_prefs()
    
    def _load_prefs(self) -> Dict:
        if os.path.exists(self.prefs_file):
            try:
                with open(self.prefs_file, 'r') as f:
                    data = json.load(f)
                    # Ensure all required keys exist
                    return self._ensure_defaults(data)
            except:
                logger.error(f"Failed to load preferences for user {self.user_id}")
        
        return self._get_default_prefs()
    
    def _get_default_prefs(self) -> Dict:
        return {
            'aliases': {},
            'frequent_transactions': [],
            'spending_limits': {},
            'budgets': {
                'monthly': {},
                'weekly': {},
                'daily': {}
            },
            'goals': [],
            'alert_settings': {
                'spike_multiplier': 3,
                'weekly_summary': True,
                'monthly_warning': True,
                'budget_alerts': True,
                'goal_reminders': True,
                'anomaly_detection': True
            },
            'context': {
                'last_category': '',
                'last_amount': 0,
                'last_wallet': 'wallet',
                'last_merchant': '',
                'last_description': '',
                'last_transaction_time': ''
            },
            'transaction_history': [],
            'usual_amounts': {},
            'income': {
                'monthly': 0,
                'income_date': 1,
                'sources': []
            },
            'financial_health': {
                'score': 50,
                'last_calculated': '',
                'history': []
            },
            'notifications': {
                'last_weekly_summary': '',
                'last_monthly_summary': '',
                'pending': []
            }
        }
    
    def _ensure_defaults(self, data: Dict) -> Dict:
        """Ensure all required keys exist in loaded data"""
        defaults = self._get_default_prefs()
        for key, value in defaults.items():
            if key not in data:
                data[key] = value
            elif isinstance(value, dict):
                for subkey, subvalue in value.items():
                    if subkey not in data[key]:
                        data[key][subkey] = subvalue
        return data
    
    def _save_prefs(self):
        try:
            with open(self.prefs_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")
    
    # ========================================
    # ALIASES
    # ========================================
    
    def add_alias(self, shortcut: str, full_text: str):
        self.data['aliases'][shortcut.lower()] = full_text.lower()
        self._save_prefs()
    
    def get_alias(self, shortcut: str) -> Optional[str]:
        return self.data['aliases'].get(shortcut.lower())
    
    def get_all_aliases(self) -> Dict[str, str]:
        return self.data['aliases']
    
    def remove_alias(self, shortcut: str) -> bool:
        if shortcut.lower() in self.data['aliases']:
            del self.data['aliases'][shortcut.lower()]
            self._save_prefs()
            return True
        return False
    
    # ========================================
    # BUDGETS
    # ========================================
    
    def set_budget(self, category: str, amount: float, period: str = 'monthly'):
        """Set budget for a category"""
        if period not in self.data['budgets']:
            self.data['budgets'][period] = {}
        self.data['budgets'][period][category.lower()] = amount
        self._save_prefs()
    
    def get_budget(self, category: str, period: str = 'monthly') -> float:
        """Get budget for a category"""
        return self.data['budgets'].get(period, {}).get(category.lower(), 0)
    
    def get_all_budgets(self, period: str = 'monthly') -> Dict[str, float]:
        """Get all budgets for a period"""
        return self.data['budgets'].get(period, {})
    
    def get_total_budget(self, period: str = 'monthly') -> float:
        """Get total budget for a period"""
        return sum(self.data['budgets'].get(period, {}).values())
    
    def remove_budget(self, category: str, period: str = 'monthly') -> bool:
        if category.lower() in self.data['budgets'].get(period, {}):
            del self.data['budgets'][period][category.lower()]
            self._save_prefs()
            return True
        return False
    
    # ========================================
    # SPENDING LIMITS (legacy compatibility)
    # ========================================
    
    def set_spending_limit(self, category: str, limit: float, period: str = 'daily'):
        if 'spending_limits' not in self.data:
            self.data['spending_limits'] = {}
        self.data['spending_limits'][category] = {
            'limit': limit,
            'period': period
        }
        self._save_prefs()
    
    def get_spending_limit(self, category: str) -> Optional[Dict]:
        return self.data.get('spending_limits', {}).get(category)
    
    # ========================================
    # GOALS
    # ========================================
    
    def add_goal(self, goal_type: str, target: float, description: str, 
                 deadline: Optional[str] = None, current: float = 0) -> str:
        """Add a new financial goal"""
        goal_id = f"goal_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        goal = {
            'id': goal_id,
            'type': goal_type,  # 'savings', 'spending_limit', 'debt_payoff', 'investment'
            'target': target,
            'current': current,
            'description': description,
            'deadline': deadline,
            'created': datetime.now().strftime('%Y-%m-%d'),
            'completed': False,
            'completed_date': None,
            'milestones': [],
            'notes': []
        }
        if 'goals' not in self.data:
            self.data['goals'] = []
        self.data['goals'].append(goal)
        self._save_prefs()
        return goal_id
    
    def update_goal_progress(self, goal_id: str, current: float) -> bool:
        """Update progress on a goal"""
        for goal in self.data.get('goals', []):
            if goal.get('id') == goal_id:
                goal['current'] = current
                if current >= goal.get('target', 0):
                    goal['completed'] = True
                    goal['completed_date'] = datetime.now().strftime('%Y-%m-%d')
                self._save_prefs()
                return True
        return False
    
    def get_active_goals(self) -> List[Dict]:
        """Get all active (non-completed) goals"""
        return [g for g in self.data.get('goals', []) if not g.get('completed', False)]
    
    def get_all_goals(self) -> List[Dict]:
        """Get all goals"""
        return self.data.get('goals', [])
    
    def get_goal_by_id(self, goal_id: str) -> Optional[Dict]:
        """Get a specific goal by ID"""
        for goal in self.data.get('goals', []):
            if goal.get('id') == goal_id:
                return goal
        return None
    
    def delete_goal(self, goal_id: str) -> bool:
        """Delete a goal"""
        goals = self.data.get('goals', [])
        for i, goal in enumerate(goals):
            if goal.get('id') == goal_id:
                del goals[i]
                self._save_prefs()
                return True
        return False
    
    def add_goal_milestone(self, goal_id: str, milestone: str, target_date: str = None):
        """Add a milestone to a goal"""
        for goal in self.data.get('goals', []):
            if goal.get('id') == goal_id:
                goal['milestones'].append({
                    'description': milestone,
                    'target_date': target_date,
                    'achieved': False,
                    'achieved_date': None
                })
                self._save_prefs()
                return True
        return False
    
    # ========================================
    # CONTEXT MEMORY
    # ========================================
    
    def update_context(self, category: Optional[str] = None, amount: Optional[float] = None, 
                       wallet: Optional[str] = None, merchant: Optional[str] = None,
                       description: Optional[str] = None):
        """Update transaction context for context-aware parsing"""
        if category:
            self.data['context']['last_category'] = category
        if amount:
            self.data['context']['last_amount'] = amount
        if wallet:
            self.data['context']['last_wallet'] = wallet
        if merchant:
            self.data['context']['last_merchant'] = merchant
        if description:
            self.data['context']['last_description'] = description
        
        self.data['context']['last_transaction_time'] = datetime.now().isoformat()
        self._save_prefs()
    
    def get_context(self) -> Dict:
        """Get current context for parsing"""
        return self.data.get('context', {})
    
    def get_full_context(self) -> Dict:
        """Get full context including usual amounts and history"""
        return {
            **self.get_context(),
            'usual_amounts': self.get_usual_amounts(),
            'frequent_transactions': self.get_frequent_patterns()[:5],
            'last_merchants': self._get_recent_merchants()
        }
    
    def _get_recent_merchants(self, limit: int = 5) -> List[str]:
        """Get recently used merchants"""
        merchants = []
        for t in reversed(self.data.get('transaction_history', [])):
            if t.get('merchant') and t['merchant'] not in merchants:
                merchants.append(t['merchant'])
                if len(merchants) >= limit:
                    break
        return merchants
    
    # ========================================
    # TRANSACTION HISTORY & PATTERNS
    # ========================================
    
    def add_to_history(self, description: str, category: str, amount: float, 
                       merchant: str = '', wallet: str = 'wallet'):
        """Add transaction to history for pattern learning"""
        if 'transaction_history' not in self.data:
            self.data['transaction_history'] = []
        
        self.data['transaction_history'].append({
            'desc': description,
            'cat': category,
            'amt': amount,
            'merchant': merchant,
            'wallet': wallet,
            'time': datetime.now().isoformat()
        })
        
        # Keep only last 200 transactions
        if len(self.data['transaction_history']) > 200:
            self.data['transaction_history'] = self.data['transaction_history'][-200:]
        
        # Update usual amounts
        self._update_usual_amount(category, amount)
        
        self._save_prefs()
    
    def _update_usual_amount(self, category: str, amount: float):
        """Update usual amount for a category"""
        if 'usual_amounts' not in self.data:
            self.data['usual_amounts'] = {}
        
        if category not in self.data['usual_amounts']:
            self.data['usual_amounts'][category] = {
                'amounts': [amount],
                'average': amount
            }
        else:
            amounts = self.data['usual_amounts'][category]['amounts']
            amounts.append(amount)
            # Keep last 20 amounts
            if len(amounts) > 20:
                amounts = amounts[-20:]
            self.data['usual_amounts'][category] = {
                'amounts': amounts,
                'average': sum(amounts) / len(amounts)
            }
    
    def get_usual_amounts(self) -> Dict[str, float]:
        """Get usual amounts per category"""
        return {
            cat: data.get('average', 0) 
            for cat, data in self.data.get('usual_amounts', {}).items()
        }
    
    def get_usual_amount(self, category: str) -> float:
        """Get usual amount for a specific category"""
        return self.data.get('usual_amounts', {}).get(category, {}).get('average', 0)
    
    def get_history_patterns(self) -> List[Dict]:
        """Get transaction history for pattern matching"""
        return self.data.get('transaction_history', [])
    
    def get_frequent_patterns(self, limit: int = 10) -> List[Dict]:
        """Get frequent transaction patterns"""
        from collections import Counter
        
        history = self.data.get('transaction_history', [])
        if not history:
            return []
        
        patterns = Counter()
        pattern_details = {}
        
        for t in history:
            key = f"{t.get('desc', '')[:30]}_{t.get('cat', '')}_{int(t.get('amt', 0))}"
            patterns[key] += 1
            pattern_details[key] = {
                'description': t.get('desc', ''),
                'category': t.get('cat', ''),
                'amount': t.get('amt', 0),
                'merchant': t.get('merchant', '')
            }
        
        result = []
        for key, count in patterns.most_common(limit):
            if count >= 2:
                result.append({
                    **pattern_details[key],
                    'count': count
                })
        
        return result
    
    # ========================================
    # INCOME MANAGEMENT
    # ========================================
    
    def set_income(self, monthly_income: float, income_date: int = 1):
        """Set monthly income and income date"""
        self.data['income']['monthly'] = monthly_income
        self.data['income']['income_date'] = income_date
        self._save_prefs()
    
    def get_income(self) -> Dict:
        """Get income information"""
        return self.data.get('income', {'monthly': 0, 'income_date': 1})
    
    def add_income_source(self, source: str, amount: float, frequency: str = 'monthly'):
        """Add an income source"""
        self.data['income']['sources'].append({
            'source': source,
            'amount': amount,
            'frequency': frequency
        })
        self._save_prefs()
    
    # ========================================
    # ALERT SETTINGS
    # ========================================
    
    def toggle_alert(self, alert_type: str, enabled: bool):
        if 'alert_settings' not in self.data:
            self.data['alert_settings'] = {}
        self.data['alert_settings'][alert_type] = enabled
        self._save_prefs()
    
    def get_alert_settings(self) -> Dict:
        return self.data.get('alert_settings', {
            'spike_multiplier': 3,
            'weekly_summary': True,
            'monthly_warning': True,
            'budget_alerts': True,
            'goal_reminders': True,
            'anomaly_detection': True
        })
    
    def set_spike_multiplier(self, multiplier: float):
        """Set the multiplier for spending spike detection"""
        self.data['alert_settings']['spike_multiplier'] = multiplier
        self._save_prefs()
    
    # ========================================
    # FINANCIAL HEALTH TRACKING
    # ========================================
    
    def update_health_score(self, score: int, factors: List = None):
        """Update financial health score"""
        self.data['financial_health']['score'] = score
        self.data['financial_health']['last_calculated'] = datetime.now().isoformat()
        
        # Keep history of scores
        self.data['financial_health']['history'].append({
            'score': score,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'factors': factors or []
        })
        
        # Keep only last 30 days of history
        if len(self.data['financial_health']['history']) > 30:
            self.data['financial_health']['history'] = self.data['financial_health']['history'][-30:]
        
        self._save_prefs()
    
    def get_health_score(self) -> Dict:
        """Get current financial health score"""
        return self.data.get('financial_health', {'score': 50})
    
    def get_health_history(self) -> List[Dict]:
        """Get financial health score history"""
        return self.data.get('financial_health', {}).get('history', [])
    
    def get_health_trend(self) -> str:
        """Get trend of financial health score"""
        history = self.get_health_history()
        if len(history) < 2:
            return 'stable'
        
        recent = history[-1]['score']
        previous = history[-2]['score']
        
        if recent > previous + 5:
            return 'improving'
        elif recent < previous - 5:
            return 'declining'
        return 'stable'
    
    # ========================================
    # NOTIFICATIONS
    # ========================================
    
    def add_notification(self, message: str, notification_type: str = 'info'):
        """Add a pending notification"""
        self.data['notifications']['pending'].append({
            'message': message,
            'type': notification_type,
            'timestamp': datetime.now().isoformat(),
            'read': False
        })
        self._save_prefs()
    
    def get_pending_notifications(self) -> List[Dict]:
        """Get unread notifications"""
        return [n for n in self.data['notifications']['pending'] if not n.get('read', False)]
    
    def mark_notifications_read(self):
        """Mark all notifications as read"""
        for n in self.data['notifications']['pending']:
            n['read'] = True
        self._save_prefs()
    
    def clear_old_notifications(self, days: int = 7):
        """Clear notifications older than X days"""
        cutoff = datetime.now() - timedelta(days=days)
        self.data['notifications']['pending'] = [
            n for n in self.data['notifications']['pending']
            if datetime.fromisoformat(n['timestamp']) >= cutoff
        ]
        self._save_prefs()
    
    def update_summary_timestamp(self, summary_type: str = 'weekly'):
        """Update when last summary was sent"""
        key = f'last_{summary_type}_summary'
        self.data['notifications'][key] = datetime.now().isoformat()
        self._save_prefs()
    
    def should_send_summary(self, summary_type: str = 'weekly') -> bool:
        """Check if it's time to send a summary"""
        key = f'last_{summary_type}_summary'
        last_sent = self.data['notifications'].get(key, '')
        
        if not last_sent:
            return True
        
        try:
            last_time = datetime.fromisoformat(last_sent)
            if summary_type == 'weekly':
                return (datetime.now() - last_time).days >= 7
            elif summary_type == 'monthly':
                return (datetime.now() - last_time).days >= 30
            elif summary_type == 'daily':
                return (datetime.now() - last_time).days >= 1
        except:
            return True
        
        return False
