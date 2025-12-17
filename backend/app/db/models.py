"""SQLAlchemy models for strategies and backtests"""
import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    strategy_config = Column(Text, nullable=False)  # JSON as TEXT for SQLite
    selected_institutions = Column(Text, nullable=True)  # JSON array as TEXT
    status = Column(String(50), nullable=False, default="draft")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    backtests = relationship("Backtest", back_populates="strategy", cascade="all, delete-orphan")

    def get_config(self):
        """Deserialize strategy_config from JSON string"""
        return json.loads(self.strategy_config) if self.strategy_config else {}
    
    def set_config(self, config):
        """Serialize strategy_config to JSON string"""
        self.strategy_config = json.dumps(config)
    
    def get_institutions(self):
        """Deserialize selected_institutions from JSON string"""
        return json.loads(self.selected_institutions) if self.selected_institutions else []
    
    def set_institutions(self, institutions):
        """Serialize selected_institutions to JSON string"""
        self.selected_institutions = json.dumps(institutions)


class Backtest(Base):
    __tablename__ = "backtests"

    id = Column(Integer, primary_key=True, index=True)
    backtest_id = Column(String(50), nullable=False, unique=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False, default="running")
    execution_time_seconds = Column(Float, nullable=True)
    start_date = Column(String(20), nullable=True)
    end_date = Column(String(20), nullable=True)
    initial_capital = Column(Float, nullable=True)
    final_value = Column(Float, nullable=True)
    total_return = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    api_calls_made = Column(Integer, nullable=True)
    stocks_analyzed = Column(Text, nullable=True)  # JSON array as TEXT
    real_market_data = Column(Text, nullable=True)  # JSON as TEXT
    institutional_signals = Column(Text, nullable=True)  # JSON as TEXT
    summary_metrics = Column(Text, nullable=True)  # JSON as TEXT
    equity_curve = Column(Text, nullable=True)  # JSON as TEXT
    trades = Column(Text, nullable=True)  # JSON as TEXT
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    strategy = relationship("Strategy", back_populates="backtests")

    def get_stocks(self):
        """Deserialize stocks_analyzed from JSON string"""
        return json.loads(self.stocks_analyzed) if self.stocks_analyzed else []
    
    def set_stocks(self, stocks):
        """Serialize stocks_analyzed to JSON string"""
        self.stocks_analyzed = json.dumps(stocks)
    
    def get_market_data(self):
        """Deserialize real_market_data from JSON string"""
        return json.loads(self.real_market_data) if self.real_market_data else {}
    
    def set_market_data(self, data):
        """Serialize real_market_data to JSON string"""
        self.real_market_data = json.dumps(data)
    
    def get_signals(self):
        """Deserialize institutional_signals from JSON string"""
        return json.loads(self.institutional_signals) if self.institutional_signals else {}
    
    def set_signals(self, signals):
        """Serialize institutional_signals to JSON string"""
        self.institutional_signals = json.dumps(signals)
    
    def get_summary(self):
        """Deserialize summary_metrics from JSON string"""
        return json.loads(self.summary_metrics) if self.summary_metrics else {}
    
    def set_summary(self, summary):
        """Serialize summary_metrics to JSON string"""
        self.summary_metrics = json.dumps(summary)
    
    def get_curve(self):
        """Deserialize equity_curve from JSON string"""
        return json.loads(self.equity_curve) if self.equity_curve else {}
    
    def set_curve(self, curve):
        """Serialize equity_curve to JSON string"""
        self.equity_curve = json.dumps(curve)
    
    def get_trades(self):
        """Deserialize trades from JSON string"""
        return json.loads(self.trades) if self.trades else []
    
    def set_trades(self, trades):
        """Serialize trades to JSON string"""
        self.trades = json.dumps(trades)

