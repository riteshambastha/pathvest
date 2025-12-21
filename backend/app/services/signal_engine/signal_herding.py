"""
Signal C: Institutional Herding Signal - FR-3.1.C.9
Triggered when 1 Large Inst Buy AND 2+ Large Inst Followers
"""

from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from app.services.postgres_service import get_postgres_service


class HerdingSignal:
    """
    Institutional Herding Signal Generator
    
    Logic: Triggered if 1 Large Inst Buy AND 2+ Large Inst Followers
    
    This signal indicates herding behavior - when multiple qualified institutions
    increase positions in the same stock, suggesting broad institutional conviction.
    """
    
    DEFAULT_LEADER_BUY_THRESHOLD = 20_000_000  # $20M for leader
    DEFAULT_FOLLOWER_BUY_THRESHOLD = 10_000_000  # $10M for followers
    DEFAULT_MIN_FOLLOWERS = 2
    
    def __init__(self):
        """Initialize signal generator with lazy-loaded services"""
        self._postgres_service = None
    
    @property
    def postgres_service(self):
        """Lazy-load postgres service"""
        if self._postgres_service is None:
            self._postgres_service = get_postgres_service()
        return self._postgres_service
    
    def evaluate(
        self,
        leader_buy_value: float,
        num_followers: int,
        follower_total_value: float,
        min_leader_value: float = DEFAULT_LEADER_BUY_THRESHOLD,
        min_follower_value: float = DEFAULT_FOLLOWER_BUY_THRESHOLD,
        min_followers: int = DEFAULT_MIN_FOLLOWERS
    ) -> bool:
        """
        Evaluate if Institutional Herding signal is triggered (synchronous)
        
        Signal C Logic:
        - 1 large leader buy (> $20M default)
        - 2+ large followers (each > $10M default)
        
        Args:
            leader_buy_value: Value of leader's purchase
            num_followers: Number of following institutions
            follower_total_value: Total value of follower purchases
            min_leader_value: Minimum leader buy value
            min_follower_value: Minimum follower buy value
            min_followers: Minimum number of followers required
        
        Returns:
            True if signal is triggered
        """
        # Condition 1: Large leader buy
        has_leader = leader_buy_value >= min_leader_value
        
        # Condition 2: Enough followers
        has_followers = num_followers >= min_followers
        
        # Condition 3: Followers have substantial positions
        avg_follower_value = follower_total_value / num_followers if num_followers > 0 else 0
        followers_substantial = avg_follower_value >= min_follower_value
        
        return has_leader and has_followers and followers_substantial
    
    async def get_institutional_position_changes(
        self,
        cusip: str,
        ticker: str,
        qualified_investor_ciks: List[str],
        current_quarter_end: date
    ) -> List[Dict[str, Any]]:
        """
        Get all institutional position changes for a stock
        
        Args:
            cusip: Stock CUSIP
            ticker: Stock ticker
            qualified_investor_ciks: List of qualified investor CIKs
            current_quarter_end: Current quarter end date
        
        Returns:
            List of position changes with metrics
        """
        if not self.postgres_service.is_available():
            return []
        
        prev_quarter_end = current_quarter_end - timedelta(days=91)
        
        query = f"""
            WITH quarterly_positions AS (
                SELECT
                    f.cik,
                    i.name as institution_name,
                    f.period_end_date,
                    f.filing_date,
                    f.total_value as institution_aum_k,
                    h.shares_or_prn_amt as shares,
                    h.value as value_k,
                    ROW_NUMBER() OVER (
                        PARTITION BY f.cik, f.period_end_date 
                        ORDER BY f.filing_date DESC
                    ) as filing_rank
                FROM `{self.postgres_service._get_table_ref('sec_holdings_13f')}` h
                JOIN `{self.postgres_service._get_table_ref('sec_filings_13f')}` f
                    ON h.filing_id = f.filing_id
                JOIN `{self.postgres_service._get_table_ref('sec_institutions')}` i
                    ON f.cik = i.cik
                WHERE h.cusip = @cusip
                    AND f.cik IN UNNEST(@qualified_ciks)
                    AND f.period_end_date IN (@current_quarter_end, @prev_quarter_end)
                    AND h.shares_or_prn_amt > 0
            ),
            
            position_changes AS (
                SELECT
                    curr.cik,
                    curr.institution_name,
                    curr.filing_date,
                    curr.institution_aum_k,
                    curr.shares as current_shares,
                    curr.value_k as current_value_k,
                    IFNULL(prev.shares, 0) as prev_shares,
                    IFNULL(prev.value_k, 0) as prev_value_k,
                    (curr.shares - IFNULL(prev.shares, 0)) as share_change,
                    (curr.value_k - IFNULL(prev.value_k, 0)) as value_change_k,
                    SAFE_DIVIDE(
                        (curr.shares - IFNULL(prev.shares, 0)),
                        NULLIF(prev.shares, 0)
                    ) as share_change_pct,
                    SAFE_DIVIDE(
                        (curr.value_k - IFNULL(prev.value_k, 0)) * 1000,
                        NULLIF(curr.institution_aum_k * 1000, 0)
                    ) as buy_pct_of_aum
                FROM (
                    SELECT * FROM quarterly_positions 
                    WHERE period_end_date = @current_quarter_end AND filing_rank = 1
                ) curr
                LEFT JOIN (
                    SELECT * FROM quarterly_positions 
                    WHERE period_end_date = @prev_quarter_end AND filing_rank = 1
                ) prev
                    ON curr.cik = prev.cik
            )
            
            SELECT
                cik,
                institution_name,
                filing_date,
                institution_aum_k,
                current_shares,
                current_value_k,
                prev_shares,
                prev_value_k,
                share_change,
                value_change_k,
                (value_change_k * 1000) as value_change_dollars,
                share_change_pct,
                buy_pct_of_aum,
                CASE
                    WHEN prev_shares = 0 THEN 'new_position'
                    WHEN share_change > 0 THEN 'increased'
                    WHEN share_change < 0 THEN 'decreased'
                    ELSE 'unchanged'
                END as position_action
            FROM position_changes
            WHERE share_change > 0  -- Only increases
            ORDER BY value_change_k DESC
        """
        
        params = {
            "cusip": cusip,
            "current_quarter_end": current_quarter_end,
            "prev_quarter_end": prev_quarter_end,
            "qualified_ciks": qualified_investor_ciks
        }
        
        try:
            results = await self.postgres_service.execute_query(query, params)
            return results
        except Exception as e:
            print(f"Error getting position changes for {ticker}: {e}")
            return []
    
    async def identify_leader_and_followers(
        self,
        position_changes: List[Dict[str, Any]],
        leader_threshold: float = DEFAULT_LEADER_BUY_THRESHOLD,
        follower_threshold: float = DEFAULT_FOLLOWER_BUY_THRESHOLD
    ) -> Dict[str, Any]:
        """
        Identify the lead institution and followers in herding behavior
        
        Args:
            position_changes: List of institutional position changes
            leader_threshold: Minimum buy value for leader ($20M default)
            follower_threshold: Minimum buy value for followers ($10M default)
        
        Returns:
            Dict with leader and followers info
        """
        if not position_changes:
            return {"leader": None, "followers": []}
        
        # Sort by value change (largest first)
        sorted_changes = sorted(
            position_changes,
            key=lambda x: x.get("value_change_dollars", 0),
            reverse=True
        )
        
        # Identify leader (largest buyer above threshold)
        leader = None
        for change in sorted_changes:
            if change.get("value_change_dollars", 0) >= leader_threshold:
                leader = change
                break
        
        if not leader:
            return {"leader": None, "followers": []}
        
        # Identify followers (other buyers above follower threshold, excluding leader)
        leader_cik = leader.get("cik")
        followers = [
            change for change in sorted_changes
            if change.get("cik") != leader_cik
            and change.get("value_change_dollars", 0) >= follower_threshold
        ]
        
        return {
            "leader": leader,
            "followers": followers
        }
    
    async def calculate_herding_strength(
        self,
        position_changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate metrics for herding strength
        
        Args:
            position_changes: List of institutional position changes
        
        Returns:
            Dict with herding metrics
        """
        if not position_changes:
            return {
                "total_buyers": 0,
                "total_buying_value": 0,
                "avg_buy_size": 0,
                "new_positions": 0,
                "increased_positions": 0
            }
        
        total_buyers = len(position_changes)
        total_buying_value = sum(
            change.get("value_change_dollars", 0)
            for change in position_changes
        )
        avg_buy_size = total_buying_value / total_buyers if total_buyers > 0 else 0
        
        new_positions = sum(
            1 for change in position_changes
            if change.get("position_action") == "new_position"
        )
        
        increased_positions = sum(
            1 for change in position_changes
            if change.get("position_action") == "increased"
        )
        
        # Calculate share-weighted consensus
        total_share_increase = sum(
            change.get("share_change", 0)
            for change in position_changes
        )
        
        return {
            "total_buyers": total_buyers,
            "total_buying_value": total_buying_value,
            "avg_buy_size": avg_buy_size,
            "new_positions": new_positions,
            "increased_positions": increased_positions,
            "total_share_increase": total_share_increase,
            "avg_buy_pct_of_aum": sum(
                change.get("buy_pct_of_aum", 0)
                for change in position_changes
            ) / total_buyers if total_buyers > 0 else 0
        }
    
    async def check_signal(
        self,
        ticker: str,
        cusip: str,
        qualified_investor_ciks: List[str],
        current_quarter_end: date,
        filing_date: date,
        min_followers: int = DEFAULT_MIN_FOLLOWERS
    ) -> Optional[Dict[str, Any]]:
        """
        Check if Institutional Herding signal is triggered
        
        Args:
            ticker: Stock ticker
            cusip: Stock CUSIP
            qualified_investor_ciks: List of qualified investor CIKs
            current_quarter_end: Quarter end date
            filing_date: Filing date for PIT
            min_followers: Minimum number of followers required
        
        Returns:
            Signal dict if triggered, None otherwise
        """
        # Get all institutional position changes
        position_changes = await self.get_institutional_position_changes(
            cusip=cusip,
            ticker=ticker,
            qualified_investor_ciks=qualified_investor_ciks,
            current_quarter_end=current_quarter_end
        )
        
        if len(position_changes) < (min_followers + 1):
            return None  # Not enough institutions buying
        
        # Identify leader and followers
        herding_structure = await self.identify_leader_and_followers(position_changes)
        
        leader = herding_structure.get("leader")
        followers = herding_structure.get("followers", [])
        
        if not leader:
            return None  # No qualifying leader
        
        if len(followers) < min_followers:
            return None  # Not enough followers
        
        # Calculate herding strength metrics
        herding_metrics = await self.calculate_herding_strength(position_changes)
        
        # Determine conviction level based on herding strength
        conviction = "medium"
        if len(followers) >= 5 and herding_metrics["total_buying_value"] > 100_000_000:
            conviction = "high"
        elif len(followers) >= 3:
            conviction = "medium"
        else:
            conviction = "low"
        
        # Signal triggered!
        return {
            "signal_type": "institutional_herding",
            "ticker": ticker,
            "cusip": cusip,
            "signal_date": filing_date.isoformat(),
            "leader": {
                "cik": leader.get("cik"),
                "institution_name": leader.get("institution_name"),
                "buy_value": leader.get("value_change_dollars"),
                "share_change_pct": leader.get("share_change_pct"),
                "position_action": leader.get("position_action")
            },
            "followers_count": len(followers),
            "top_followers": [
                {
                    "cik": f.get("cik"),
                    "institution_name": f.get("institution_name"),
                    "buy_value": f.get("value_change_dollars"),
                    "share_change_pct": f.get("share_change_pct")
                }
                for f in followers[:5]  # Top 5 followers
            ],
            "herding_metrics": herding_metrics,
            "conviction_indicator": conviction
        }
    
    async def generate_signals(
        self,
        qualified_investors: List[Dict[str, Any]],
        sub_universe: List[Dict[str, Any]],
        current_quarter_end: date,
        filing_date: date
    ) -> List[Dict[str, Any]]:
        """
        Generate Institutional Herding signals for sub-universe
        
        Args:
            qualified_investors: List of qualified investors
            sub_universe: List of stocks in sub-universe
            current_quarter_end: Current quarter end date
            filing_date: Filing date for PIT
        
        Returns:
            List of triggered signals
        """
        signals = []
        
        investor_ciks = [inv.get("cik") for inv in qualified_investors]
        
        for stock in sub_universe:
            ticker = stock.get("ticker")
            cusip = stock.get("cusip")
            
            if not ticker or not cusip:
                continue
            
            signal = await self.check_signal(
                ticker=ticker,
                cusip=cusip,
                qualified_investor_ciks=investor_ciks,
                current_quarter_end=current_quarter_end,
                filing_date=filing_date
            )
            
            if signal:
                signals.append(signal)
        
        return signals


# Singleton instance
_herding_signal = None


def get_herding_signal() -> HerdingSignal:
    """Get or create Institutional Herding signal generator instance"""
    global _herding_signal
    if _herding_signal is None:
        _herding_signal = HerdingSignal()
    return _herding_signal

