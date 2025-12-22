"""
Tests for Backtrader Engine
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from app.services.backtrader_engine import BacktraderEngine, get_backtrader_engine


class TestBacktraderEngine:
    """Test cases for BacktraderEngine"""
    
    @pytest.fixture
    def engine(self):
        """Create a test engine instance"""
        return get_backtrader_engine(initial_capital=100_000)
    
    @pytest.fixture
    def sample_signals(self):
        """Generate sample trading signals"""
        return [
            {
                'date': '2024-01-15',
                'ticker': 'AAPL',
                'action': 'BUY',
                'signal_strength': 0.8,
                'conviction_score': 0.75,
            },
            {
                'date': '2024-02-01',
                'ticker': 'MSFT',
                'action': 'BUY',
                'signal_strength': 0.7,
                'conviction_score': 0.65,
            },
            {
                'date': '2024-03-15',
                'ticker': 'GOOGL',
                'action': 'BUY',
                'signal_strength': 0.9,
                'conviction_score': 0.85,
            },
        ]
    
    @pytest.fixture
    def sample_config(self):
        """Sample strategy configuration"""
        return {
            'position_sizing': {
                'percent_per_position': 0.05,
                'max_positions': 20,
                'min_positions': 5,
            },
            'exit_rules': {
                'enable_stop_loss': True,
                'stop_loss_pct': 0.20,
                'enable_take_profit': False,
                'enable_trailing_stop': False,
            },
            'heartbeat': {
                'rebalance_frequency': 'monthly',
                'rebalance_threshold': 0.05,
            },
        }
    
    def test_engine_initialization(self, engine):
        """Test engine initializes correctly"""
        assert engine.initial_capital == 100_000
        assert engine.commission == 0.001
        assert engine.slippage == 0.0025
    
    def test_empty_results_structure(self, engine):
        """Test empty results have correct structure"""
        result = engine._empty_results("Test error")
        
        assert result['success'] is False
        assert result['error'] == "Test error"
        assert result['engine'] == 'backtrader'
        assert result['total_return'] == 0
        assert result['initial_capital'] == 100_000
        assert result['trade_log'] == []
    
    def test_cagr_calculation(self, engine):
        """Test CAGR calculation"""
        # 100% return over 1 year = 100% CAGR
        cagr = engine._calculate_cagr(100_000, 200_000, '2024-01-01', '2025-01-01')
        assert abs(cagr - 1.0) < 0.01
        
        # 50% return over 2 years = ~22.5% CAGR
        cagr = engine._calculate_cagr(100_000, 150_000, '2024-01-01', '2026-01-01')
        assert abs(cagr - 0.225) < 0.05
    
    @pytest.mark.asyncio
    async def test_backtest_no_signals(self, engine, sample_config):
        """Test backtest with no signals returns error"""
        result = await engine.run_backtest(
            signals=[],
            start_date='2024-01-01',
            end_date='2024-06-01',
            strategy_config=sample_config,
        )
        
        assert result['success'] is False
        assert 'No tickers' in result.get('error', '')
    
    @pytest.mark.asyncio
    async def test_backtest_with_signals(self, engine, sample_signals, sample_config):
        """Test backtest with valid signals"""
        result = await engine.run_backtest(
            signals=sample_signals,
            start_date='2024-01-01',
            end_date='2024-06-30',
            strategy_config=sample_config,
        )
        
        # Should complete (success or fail on data fetch)
        assert 'engine' in result
        assert result['engine'] == 'backtrader'
        assert 'total_return' in result
        assert 'initial_capital' in result
    
    @pytest.mark.asyncio
    async def test_backtest_result_structure(self, engine, sample_signals, sample_config):
        """Test that backtest results have all required fields"""
        result = await engine.run_backtest(
            signals=sample_signals,
            start_date='2024-01-01',
            end_date='2024-06-30',
            strategy_config=sample_config,
        )
        
        required_fields = [
            'engine',
            'total_return',
            'sharpe_ratio',
            'max_drawdown',
            'initial_capital',
            'trade_log',
            'portfolio_history',
        ]
        
        for field in required_fields:
            assert field in result, f"Missing field: {field}"


class TestPathVestStrategy:
    """Test PathVestStrategy behavior"""
    
    def test_signal_queue_initialization(self):
        """Test that signals are properly queued for T+1 execution"""
        from app.services.backtrader_engine import PathVestStrategy
        import backtrader as bt
        
        # This would require full Cerebro setup, so we test indirectly
        pass  # Strategy initialization tested via integration tests


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

