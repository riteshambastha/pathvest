"""
Attribution Analysis Module
Breaks down portfolio performance by signal type, sector, time period, etc.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict


class AttributionAnalyzer:
    """
    Attribution analyzer for portfolio performance
    
    Analyzes performance contribution by:
    1. Signal Type (Doubling Down, Insider Buying, Herding)
    2. Sector/Industry
    3. Time Period (yearly, quarterly, monthly)
    4. Individual stocks
    5. Long vs Short (if applicable)
    """
    
    def __init__(self):
        """Initialize attribution analyzer"""
        pass
    
    def analyze_attribution(
        self,
        trades: List[Dict],
        equity_curve: List[float],
        dates: List[str]
    ) -> Dict[str, Any]:
        """
        Perform comprehensive attribution analysis
        
        Args:
            trades: List of trade dictionaries
            equity_curve: Portfolio equity curve
            dates: Date strings
        
        Returns:
            Dict with attribution breakdowns
        """
        attribution = {}
        
        # By signal type
        attribution['by_signal_type'] = self._attribute_by_signal_type(trades)
        
        # By stock
        attribution['by_stock'] = self._attribute_by_stock(trades)
        
        # By time period
        attribution['by_time_period'] = self._attribute_by_time_period(trades)
        
        # By holding period bucket
        attribution['by_holding_period'] = self._attribute_by_holding_period(trades)
        
        # Win/Loss analysis
        attribution['win_loss_analysis'] = self._analyze_wins_losses(trades)
        
        return attribution
    
    # ==================== Signal Type Attribution ====================
    
    def _attribute_by_signal_type(self, trades: List[Dict]) -> Dict[str, Any]:
        """
        Break down performance by signal type
        
        Returns:
            Dict with metrics for each signal type
        """
        signal_stats = defaultdict(lambda: {
            'count': 0,
            'total_pnl': 0,
            'total_return': 0,
            'avg_pnl': 0,
            'avg_return': 0,
            'win_rate': 0,
            'avg_holding_days': 0
        })
        
        # Aggregate by signal type
        for trade in trades:
            signal_type = trade.get('signal_type', 'unknown')
            pnl = trade.get('pnl', 0)
            return_pct = trade.get('return_pct', 0)
            holding_days = trade.get('holding_period_days', 0)
            
            signal_stats[signal_type]['count'] += 1
            signal_stats[signal_type]['total_pnl'] += pnl
            signal_stats[signal_type]['total_return'] += return_pct
            
            if holding_days:
                signal_stats[signal_type]['avg_holding_days'] += holding_days
        
        # Calculate averages and win rates
        for signal_type, stats in signal_stats.items():
            count = stats['count']
            if count > 0:
                stats['avg_pnl'] = stats['total_pnl'] / count
                stats['avg_return'] = stats['total_return'] / count
                stats['avg_holding_days'] = stats['avg_holding_days'] / count
                
                # Win rate
                signal_trades = [t for t in trades if t.get('signal_type') == signal_type]
                wins = sum(1 for t in signal_trades if t.get('pnl', 0) > 0)
                stats['win_rate'] = wins / count if count > 0 else 0
        
        # Convert to regular dict for JSON serialization
        return dict(signal_stats)
    
    # ==================== Stock Attribution ====================
    
    def _attribute_by_stock(self, trades: List[Dict]) -> List[Dict[str, Any]]:
        """
        Break down performance by individual stock
        
        Returns:
            List of stock attribution dicts (sorted by total P&L)
        """
        stock_stats = defaultdict(lambda: {
            'ticker': '',
            'trades_count': 0,
            'total_pnl': 0,
            'total_return': 0,
            'avg_pnl': 0,
            'avg_return': 0,
            'win_rate': 0
        })
        
        # Aggregate by stock
        for trade in trades:
            ticker = trade.get('ticker', 'UNKNOWN')
            pnl = trade.get('pnl', 0)
            return_pct = trade.get('return_pct', 0)
            
            stock_stats[ticker]['ticker'] = ticker
            stock_stats[ticker]['trades_count'] += 1
            stock_stats[ticker]['total_pnl'] += pnl
            stock_stats[ticker]['total_return'] += return_pct
        
        # Calculate averages and win rates
        for ticker, stats in stock_stats.items():
            count = stats['trades_count']
            if count > 0:
                stats['avg_pnl'] = stats['total_pnl'] / count
                stats['avg_return'] = stats['total_return'] / count
                
                # Win rate
                stock_trades = [t for t in trades if t.get('ticker') == ticker]
                wins = sum(1 for t in stock_trades if t.get('pnl', 0) > 0)
                stats['win_rate'] = wins / count if count > 0 else 0
        
        # Convert to list and sort by total P&L
        stock_list = list(stock_stats.values())
        stock_list.sort(key=lambda x: x['total_pnl'], reverse=True)
        
        return stock_list
    
    # ==================== Time Period Attribution ====================
    
    def _attribute_by_time_period(self, trades: List[Dict]) -> Dict[str, Any]:
        """
        Break down performance by time period (yearly, quarterly, monthly)
        
        Returns:
            Dict with yearly, quarterly, monthly breakdowns
        """
        # Parse trade dates and group
        yearly_stats = defaultdict(lambda: {'pnl': 0, 'trades': 0, 'returns': []})
        quarterly_stats = defaultdict(lambda: {'pnl': 0, 'trades': 0, 'returns': []})
        monthly_stats = defaultdict(lambda: {'pnl': 0, 'trades': 0, 'returns': []})
        
        for trade in trades:
            exit_date_str = trade.get('exit_date')
            if not exit_date_str:
                continue
            
            try:
                exit_date = datetime.strptime(exit_date_str, '%Y-%m-%d')
                pnl = trade.get('pnl', 0)
                return_pct = trade.get('return_pct', 0)
                
                # Yearly
                year = exit_date.year
                yearly_stats[year]['pnl'] += pnl
                yearly_stats[year]['trades'] += 1
                if return_pct is not None:
                    yearly_stats[year]['returns'].append(return_pct)
                
                # Quarterly
                quarter = f"{year}Q{(exit_date.month - 1) // 3 + 1}"
                quarterly_stats[quarter]['pnl'] += pnl
                quarterly_stats[quarter]['trades'] += 1
                if return_pct is not None:
                    quarterly_stats[quarter]['returns'].append(return_pct)
                
                # Monthly
                month = f"{year}-{exit_date.month:02d}"
                monthly_stats[month]['pnl'] += pnl
                monthly_stats[month]['trades'] += 1
                if return_pct is not None:
                    monthly_stats[month]['returns'].append(return_pct)
            
            except:
                continue
        
        # Calculate summary stats
        def summarize_period(stats_dict):
            summary = []
            for period, data in sorted(stats_dict.items()):
                avg_return = np.mean(data['returns']) if data['returns'] else 0
                summary.append({
                    'period': str(period),
                    'total_pnl': data['pnl'],
                    'trades_count': data['trades'],
                    'avg_return': float(avg_return)
                })
            return summary
        
        return {
            'yearly': summarize_period(yearly_stats),
            'quarterly': summarize_period(quarterly_stats),
            'monthly': summarize_period(monthly_stats)
        }
    
    # ==================== Holding Period Attribution ====================
    
    def _attribute_by_holding_period(self, trades: List[Dict]) -> List[Dict[str, Any]]:
        """
        Break down performance by holding period buckets
        
        Returns:
            List of holding period bucket stats
        """
        # Define buckets (in days)
        buckets = [
            (0, 30, '0-30 days'),
            (31, 90, '31-90 days'),
            (91, 180, '91-180 days'),
            (181, 365, '181-365 days'),
            (366, 9999, '365+ days')
        ]
        
        bucket_stats = {name: {'count': 0, 'total_pnl': 0, 'total_return': 0, 'wins': 0}
                       for _, _, name in buckets}
        
        # Classify trades into buckets
        for trade in trades:
            holding_days = trade.get('holding_period_days', 0)
            if not holding_days:
                continue
            
            pnl = trade.get('pnl', 0)
            return_pct = trade.get('return_pct', 0)
            
            # Find appropriate bucket
            for min_days, max_days, bucket_name in buckets:
                if min_days <= holding_days <= max_days:
                    bucket_stats[bucket_name]['count'] += 1
                    bucket_stats[bucket_name]['total_pnl'] += pnl
                    bucket_stats[bucket_name]['total_return'] += return_pct
                    if pnl > 0:
                        bucket_stats[bucket_name]['wins'] += 1
                    break
        
        # Calculate averages and win rates
        result = []
        for _, _, bucket_name in buckets:
            stats = bucket_stats[bucket_name]
            count = stats['count']
            
            if count > 0:
                result.append({
                    'bucket': bucket_name,
                    'trades_count': count,
                    'total_pnl': stats['total_pnl'],
                    'avg_pnl': stats['total_pnl'] / count,
                    'avg_return': stats['total_return'] / count,
                    'win_rate': stats['wins'] / count
                })
            else:
                result.append({
                    'bucket': bucket_name,
                    'trades_count': 0,
                    'total_pnl': 0,
                    'avg_pnl': 0,
                    'avg_return': 0,
                    'win_rate': 0
                })
        
        return result
    
    # ==================== Win/Loss Analysis ====================
    
    def _analyze_wins_losses(self, trades: List[Dict]) -> Dict[str, Any]:
        """
        Analyze winning vs losing trades
        
        Returns:
            Dict with win/loss statistics
        """
        wins = [t for t in trades if t.get('pnl', 0) > 0]
        losses = [t for t in trades if t.get('pnl', 0) < 0]
        
        total_wins = sum(t.get('pnl', 0) for t in wins)
        total_losses = abs(sum(t.get('pnl', 0) for t in losses))
        
        analysis = {
            'total_trades': len(trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': len(wins) / len(trades) if trades else 0,
            'avg_win': total_wins / len(wins) if wins else 0,
            'avg_loss': -total_losses / len(losses) if losses else 0,
            'largest_win': max((t.get('pnl', 0) for t in wins), default=0),
            'largest_loss': min((t.get('pnl', 0) for t in losses), default=0),
            'profit_factor': total_wins / total_losses if total_losses > 0 else 0,
            'avg_win_return': np.mean([t.get('return_pct', 0) for t in wins]) if wins else 0,
            'avg_loss_return': np.mean([t.get('return_pct', 0) for t in losses]) if losses else 0
        }
        
        return analysis


# Singleton instance
_analyzer_instance = None


def get_attribution_analyzer() -> AttributionAnalyzer:
    """Get singleton AttributionAnalyzer instance"""
    global _analyzer_instance
    
    if _analyzer_instance is None:
        _analyzer_instance = AttributionAnalyzer()
    
    return _analyzer_instance

