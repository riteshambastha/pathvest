"""Database operations for strategies and backtests"""
import json
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import ARRAY, JSON

# Import SEC service for institution name lookup
sys.path.insert(0, os.path.dirname(__file__))
try:
    from sec_edgar_service import sec_service
except ImportError:
    sec_service = None

# In-memory cache for institution names (CIK -> Name mapping)
_institution_name_cache = {}

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pathvest_local.db")

# Determine if we're using PostgreSQL or SQLite
is_postgres = DATABASE_URL.startswith("postgresql")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class
Base = declarative_base()

# Models
class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    strategy_config = Column(JSON if is_postgres else Text, nullable=False)
    selected_institutions = Column(ARRAY(String) if is_postgres else Text, nullable=True)
    status = Column(String(50), nullable=False, default="draft")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    backtests = relationship("Backtest", back_populates="strategy", cascade="all, delete-orphan")


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
    sec_filings_fetched = Column(Integer, nullable=True)  # Track SEC data usage
    stocks_analyzed = Column(ARRAY(String) if is_postgres else Text, nullable=True)
    real_market_data = Column(JSON if is_postgres else Text, nullable=True)
    institutional_signals = Column(JSON if is_postgres else Text, nullable=True)
    summary_metrics = Column(JSON if is_postgres else Text, nullable=True)
    equity_curve = Column(JSON if is_postgres else Text, nullable=True)
    trades = Column(JSON if is_postgres else Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    strategy = relationship("Strategy", back_populates="backtests")


# Helper functions
def get_institution_name(cik: str) -> str:
    """Get institution name with caching"""
    global _institution_name_cache
    
    # Check cache first
    if cik in _institution_name_cache:
        return _institution_name_cache[cik]
    
    # Fetch from SEC service
    if sec_service:
        try:
            inst_info = sec_service.get_institution_summary(cik)
            name = inst_info.get("name", cik)
            _institution_name_cache[cik] = name  # Cache it
            return name
        except:
            return cik
    return cik


def save_strategy(name: str, config: dict, selected_institutions: list = None) -> int:
    """Save a new strategy to the database"""
    db = SessionLocal()
    try:
        # For PostgreSQL: pass config as dict (will be stored as JSON)
        # For SQLite: convert to JSON string
        config_value = config if is_postgres else json.dumps(config)
        
        # For PostgreSQL: pass institutions as list (will be stored as ARRAY)
        # For SQLite: convert to JSON string
        institutions_value = (selected_institutions or []) if is_postgres else json.dumps(selected_institutions or [])
        
        strategy = Strategy(
            name=name,
            strategy_config=config_value,
            selected_institutions=institutions_value,
            status="active"
        )
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
        
        # ✅ Pre-warm cache: Fetch institution names in background
        if selected_institutions:
            for cik in selected_institutions:
                get_institution_name(cik)  # This will cache the names
        
        return strategy.id
    finally:
        db.close()


def save_backtest(backtest_id: str, strategy_id: int, config: dict) -> None:
    """Save a new backtest to the database"""
    db = SessionLocal()
    try:
        backtest = Backtest(
            backtest_id=backtest_id,
            strategy_id=strategy_id,
            status="running",
            start_date=config.get("backtest_period", {}).get("start_date"),
            end_date=config.get("backtest_period", {}).get("end_date"),
            initial_capital=config.get("initial_capital", 100000.0)
        )
        db.add(backtest)
        db.commit()
    finally:
        db.close()


def update_backtest_results(backtest_id: str, results: dict) -> None:
    """Update backtest with results"""
    db = SessionLocal()
    try:
        backtest = db.query(Backtest).filter(Backtest.backtest_id == backtest_id).first()
        if backtest:
            backtest.status = results.get("status", "completed")
            backtest.execution_time_seconds = results.get("execution_time_seconds")
            backtest.final_value = results.get("final_value")
            backtest.total_return = results.get("total_return")
            backtest.sharpe_ratio = results.get("sharpe_ratio")
            backtest.max_drawdown = results.get("max_drawdown")
            backtest.api_calls_made = results.get("api_calls_made")
            backtest.sec_filings_fetched = results.get("sec_filings_fetched")
            
            # For PostgreSQL: pass as native types (list/dict)
            # For SQLite: convert to JSON strings
            backtest.stocks_analyzed = results.get("stocks_analyzed", []) if is_postgres else json.dumps(results.get("stocks_analyzed", []))
            backtest.real_market_data = results.get("real_market_data", {}) if is_postgres else json.dumps(results.get("real_market_data", {}))
            backtest.institutional_signals = results.get("institutional_signals", {}) if is_postgres else json.dumps(results.get("institutional_signals", {}))
            backtest.summary_metrics = results.get("summary_metrics", {}) if is_postgres else json.dumps(results.get("summary_metrics", {}))
            backtest.equity_curve = results.get("equity_curve", {}) if is_postgres else json.dumps(results.get("equity_curve", {}))
            backtest.trades = results.get("trades", []) if is_postgres else json.dumps(results.get("trades", []))
            
            backtest.error_message = results.get("error_message")
            backtest.completed_at = datetime.utcnow() if backtest.status == "completed" else None
            db.commit()
    finally:
        db.close()


def get_all_strategies() -> list:
    """Get all strategies with their latest backtest (OPTIMIZED)"""
    db = SessionLocal()
    try:
        strategies = db.query(Strategy).order_by(desc(Strategy.created_at)).all()
        result = []
        
        for strategy in strategies:
            # Get latest backtest (already optimized with single query)
            latest_backtest = db.query(Backtest).filter(
                Backtest.strategy_id == strategy.id
            ).order_by(desc(Backtest.created_at)).first()
            
            # Convert CIKs to institution names using cache
            # For PostgreSQL: already a list, For SQLite: need to parse JSON
            institution_ciks = strategy.selected_institutions if is_postgres else json.loads(strategy.selected_institutions or "[]")
            institution_names = [get_institution_name(cik) for cik in (institution_ciks or [])]  # ✅ Uses cache!
            
            result.append({
                "id": strategy.id,
                "name": strategy.name,
                "description": strategy.description,
                "selected_institutions": institution_names,
                "status": strategy.status,
                "created_at": strategy.created_at.isoformat(),
                "backtests_count": len(strategy.backtests),
                "latest_backtest": {
                    "backtest_id": latest_backtest.backtest_id,
                    "status": latest_backtest.status,
                    "total_return": latest_backtest.total_return,
                    "sharpe_ratio": latest_backtest.sharpe_ratio,
                    "created_at": latest_backtest.created_at.isoformat()
                } if latest_backtest else None
            })
        return result
    finally:
        db.close()


def get_strategy(strategy_id: int) -> dict:
    """Get a specific strategy with all its backtests"""
    db = SessionLocal()
    try:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            return None
        
        # For PostgreSQL: already native types, For SQLite: need to parse JSON
        config = strategy.strategy_config if is_postgres else json.loads(strategy.strategy_config)
        institutions = strategy.selected_institutions if is_postgres else json.loads(strategy.selected_institutions or "[]")
        
        return {
            "id": strategy.id,
            "name": strategy.name,
            "description": strategy.description,
            "strategy_config": config,
            "selected_institutions": institutions or [],
            "status": strategy.status,
            "created_at": strategy.created_at.isoformat(),
            "updated_at": strategy.updated_at.isoformat(),
            "backtests": [
                {
                    "backtest_id": bt.backtest_id,
                    "status": bt.status,
                    "total_return": bt.total_return,
                    "sharpe_ratio": bt.sharpe_ratio,
                    "max_drawdown": bt.max_drawdown,
                    "created_at": bt.created_at.isoformat(),
                    "completed_at": bt.completed_at.isoformat() if bt.completed_at else None
                }
                for bt in strategy.backtests
            ]
        }
    finally:
        db.close()


def get_backtest(backtest_id: str) -> dict:
    """Get full backtest results"""
    db = SessionLocal()
    try:
        backtest = db.query(Backtest).filter(Backtest.backtest_id == backtest_id).first()
        if not backtest:
            return None
        
        # For PostgreSQL: already native types, For SQLite: need to parse JSON
        stocks_analyzed = backtest.stocks_analyzed if is_postgres else json.loads(backtest.stocks_analyzed or "[]")
        real_market_data = backtest.real_market_data if is_postgres else json.loads(backtest.real_market_data or "{}")
        institutional_signals = backtest.institutional_signals if is_postgres else json.loads(backtest.institutional_signals or "{}")
        summary_metrics = backtest.summary_metrics if is_postgres else json.loads(backtest.summary_metrics or "{}")
        equity_curve = backtest.equity_curve if is_postgres else json.loads(backtest.equity_curve or "{}")
        trades = backtest.trades if is_postgres else json.loads(backtest.trades or "[]")
        
        return {
            "backtest_id": backtest.backtest_id,
            "strategy_id": backtest.strategy_id,
            "status": backtest.status,
            "execution_time_seconds": backtest.execution_time_seconds,
            "start_date": backtest.start_date,
            "end_date": backtest.end_date,
            "initial_capital": backtest.initial_capital,
            "final_value": backtest.final_value,
            "total_return": backtest.total_return,
            "sharpe_ratio": backtest.sharpe_ratio,
            "max_drawdown": backtest.max_drawdown,
            "api_calls_made": backtest.api_calls_made,
            "sec_filings_fetched": backtest.sec_filings_fetched,
            "stocks_analyzed": stocks_analyzed or [],
            "real_market_data": real_market_data or {},
            "institutional_signals": institutional_signals or {},
            "summary_metrics": summary_metrics or {},
            "equity_curve": equity_curve or {},
            "trades": trades or [],
            "error_message": backtest.error_message,
            "created_at": backtest.created_at.isoformat(),
            "completed_at": backtest.completed_at.isoformat() if backtest.completed_at else None
        }
    finally:
        db.close()


def delete_strategy(strategy_id: int) -> bool:
    """
    Delete a strategy and all its associated backtests
    
    Args:
        strategy_id: Strategy ID to delete
    
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    db = SessionLocal()
    try:
        # Find the strategy
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        
        if not strategy:
            print(f"❌ Strategy {strategy_id} not found")
            return False
        
        strategy_name = strategy.name
        backtest_count = len(strategy.backtests)
        
        # Delete the strategy (cascades to backtests due to cascade="all, delete-orphan")
        db.delete(strategy)
        db.commit()
        
        print(f"✅ Deleted strategy '{strategy_name}' (ID: {strategy_id})")
        print(f"✅ Cascade deleted {backtest_count} associated backtests")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error deleting strategy {strategy_id}: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

