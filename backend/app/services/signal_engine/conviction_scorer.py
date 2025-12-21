"""
Conviction Scorer - FR-3.1.C.10.1
Calculates conviction scores for ranking candidates
"""

from typing import List, Dict, Any, Tuple, Optional


class ConvictionScorer:
    """
    Conviction scoring and ranking for portfolio construction
    
    Composite Score Formula (FR-3.1.C.10.1):
    S_conviction = w1 * I_herding + w2 * I_insider
    
    Where:
    - I_herding: Normalized score (0-100) based on institutional herding strength
    - I_insider: Normalized score (0-100) based on insider buying confidence
    - w1, w2: User-configurable weights (Default: w1=0.6, w2=0.4)
    
    Tie-breaking: Lower market cap wins (higher growth potential)
    """
    
    DEFAULT_HERDING_WEIGHT = 0.6
    DEFAULT_INSIDER_WEIGHT = 0.4
    
    def __init__(
        self,
        herding_weight: float = DEFAULT_HERDING_WEIGHT,
        insider_weight: float = DEFAULT_INSIDER_WEIGHT
    ):
        """
        Initialize conviction scorer
        
        Args:
            herding_weight: Weight for institutional herding score
            insider_weight: Weight for insider confidence score
        """
        self.herding_weight = herding_weight
        self.insider_weight = insider_weight
    
    def calculate_herding_score(self, candidate: Dict[str, Any]) -> float:
        """
        Calculate institutional herding score (0-100)
        
        Based on:
        - Number of institutions buying
        - Total buying value
        - Share increase magnitude
        - Whether herding signal was triggered
        
        Args:
            candidate: Candidate dict with signal details
                Can be either:
                - Simple format: {num_institutions, net_share_increase, total_institutions}
                - Full format: {institutional_herding_details, signals_triggered, ...}
        
        Returns:
            Normalized herding score (0-100)
        """
        score = 0.0
        
        # Handle simple format (for testing)
        if "num_institutions" in candidate:
            num_inst = candidate.get("num_institutions", 0)
            net_increase = candidate.get("net_share_increase", 0)
            total_inst = candidate.get("total_institutions", 100)
            
            # Base score: percentage of institutions buying (scaled to 40 points max)
            pct_buying = (num_inst / total_inst * 100) if total_inst > 0 else 0
            base_score = min(pct_buying * 4, 40)  # 10% buying = 40 points
            
            # Bonus for number of institutions (up to 30 points)
            inst_bonus = min(num_inst * 6, 30)  # 5 institutions = 30 points
            
            # Bonus for share increase magnitude (up to 30 points)
            # Scale: 1M shares = 10, 5M = 25, 10M+ = 30
            increase_bonus = min(net_increase / 333_333, 30)
            
            score = base_score + inst_bonus + increase_bonus
            return min(score, 100.0)
        
        # Handle full format
        # Check if herding signal exists
        herding_details = candidate.get("institutional_herding_details")
        
        if herding_details:
            # Strong signal: herding detected
            base_score = 60  # Base score for triggering herding signal
            
            # Bonus for number of followers
            followers_count = herding_details.get("followers_count", 0)
            followers_bonus = min(followers_count * 5, 20)  # Max 20 points
            
            # Bonus for total buying value
            herding_metrics = herding_details.get("herding_metrics", {})
            total_buying = herding_metrics.get("total_buying_value", 0)
            
            # Scale: $50M = 10 points, $100M+ = 20 points
            buying_bonus = min((total_buying / 5_000_000), 20)  # Max 20 points
            
            score = base_score + followers_bonus + buying_bonus
        
        elif "institutional_herding" in candidate.get("signals_triggered", []):
            # Partial credit if mentioned but no details
            score = 50
        
        # Check transaction analysis from stock filter
        transaction_analysis = candidate.get("transaction_analysis", {})
        if transaction_analysis:
            num_buying_institutions = candidate.get("num_buying_institutions", 0)
            
            # Award points for institutional buying activity
            if num_buying_institutions > 0:
                score += min(num_buying_institutions * 3, 15)  # Max 15 points
        
        # Cap at 100
        return min(score, 100.0)
    
    def calculate_insider_score(self, candidate: Dict[str, Any]) -> float:
        """
        Calculate insider confidence score (0-100)
        
        Based on:
        - Number of C-level insiders buying
        - Total purchase value (90d aggregate)
        - Insider cluster strength
        - Whether insider buying signal was triggered
        
        Args:
            candidate: Candidate dict with signal details
                Can be either:
                - Simple format: {num_insiders, total_purchase_value, avg_purchase_size}
                - Full format: {insider_buying_details, insider_activity, ...}
        
        Returns:
            Normalized insider score (0-100)
        """
        score = 0.0
        
        # Handle simple format (for testing)
        if "num_insiders" in candidate or "total_purchase_value" in candidate:
            num_insiders = candidate.get("num_insiders", 0)
            total_value = candidate.get("total_purchase_value", 0)
            avg_size = candidate.get("avg_purchase_size", 0)
            
            # Base score: number of insiders (up to 40 points)
            # 3 insiders = 30 points
            insider_bonus = min(num_insiders * 10, 40)
            
            # Bonus for total purchase value (up to 40 points)
            # $100k = 10, $500k+ = 40
            value_bonus = min(total_value / 12_500, 40)
            
            # Bonus for average size (up to 20 points)
            # $100k avg = 15, $200k+ = 20
            avg_bonus = min(avg_size / 10_000, 20)
            
            score = insider_bonus + value_bonus + avg_bonus
            return min(score, 100.0)
        
        # Handle full format
        # Check if insider buying signal exists
        insider_details = candidate.get("insider_buying_details")
        
        if insider_details:
            # Strong signal: insider buying detected
            base_score = 60  # Base score for triggering insider signal
            
            # Bonus for number of insider buyers
            insider_buyers = insider_details.get("insider_buyers", 0)
            insider_bonus = min(insider_buyers * 8, 20)  # Max 20 points
            
            # Bonus for total insider value
            total_insider_value = insider_details.get("total_insider_buy_value", 0)
            
            # Scale: $200k = 10 points, $500k+ = 20 points
            value_bonus = min((total_insider_value / 25_000), 20)  # Max 20 points
            
            score = base_score + insider_bonus + value_bonus
        
        elif "insider_buying" in candidate.get("signals_triggered", []):
            # Partial credit
            score = 50
        
        # Check insider activity from insider filter
        insider_activity = candidate.get("insider_activity", {})
        if insider_activity:
            cluster = insider_activity.get("cluster")
            
            if cluster:
                # Cluster detected
                unique_insiders = cluster.get("unique_insiders", 0)
                aggregate_value = cluster.get("aggregate_value", 0)
                
                score += min(unique_insiders * 5, 15)  # Max 15 points
                score += min(aggregate_value / 50_000, 10)  # Max 10 points
        
        # Cap at 100
        return min(score, 100.0)
    
    def calculate_composite_score(
        self,
        herding_score: float,
        insider_score: float
    ) -> float:
        """
        Calculate composite conviction score from component scores
        
        Formula: S_conviction = w1 * I_herding + w2 * I_insider
        
        Args:
            herding_score: Herding score (0-100)
            insider_score: Insider score (0-100)
        
        Returns:
            Composite conviction score
        """
        return (self.herding_weight * herding_score + 
                self.insider_weight * insider_score)
    
    def calculate_conviction_score(
        self,
        candidate: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate composite conviction score
        
        Args:
            candidate: Candidate dict
        
        Returns:
            (conviction_score, component_scores)
        """
        # Calculate component scores
        herding_score = self.calculate_herding_score(candidate)
        insider_score = self.calculate_insider_score(candidate)
        
        # Calculate composite score
        conviction_score = (
            self.herding_weight * herding_score +
            self.insider_weight * insider_score
        )
        
        component_scores = {
            "herding_score": herding_score,
            "insider_score": insider_score,
            "herding_weight": self.herding_weight,
            "insider_weight": self.insider_weight
        }
        
        return conviction_score, component_scores
    
    def rank_candidates(
        self,
        candidates: List[Dict[str, Any]],
        tie_break_by_market_cap: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Rank candidates by conviction score with tie-breaking
        
        Tie-breaking logic (FR-3.1.C.10.1):
        If S_conviction is identical, prioritize lower market cap
        
        Args:
            candidates: List of candidates to rank
                Each candidate can have pre-calculated conviction_score or 
                component data for calculation
            tie_break_by_market_cap: Use market cap for tie-breaking
        
        Returns:
            Sorted list with ranking
        """
        # Calculate conviction scores for candidates that don't have them
        for candidate in candidates:
            if "conviction_score" not in candidate:
                conviction_score, components = self.calculate_conviction_score(candidate)
                candidate["conviction_score"] = conviction_score
                candidate["conviction_components"] = components
        
        # Helper to get market cap (support both field names)
        def get_market_cap(x):
            return x.get("market_cap", x.get("estimated_market_cap", float('inf')))
        
        # Sort by conviction score (descending) and market cap (ascending) for ties
        if tie_break_by_market_cap:
            sorted_candidates = sorted(
                candidates,
                key=lambda x: (
                    -x.get("conviction_score", 0),  # Higher score first
                    get_market_cap(x)  # Lower market cap for ties
                )
            )
        else:
            sorted_candidates = sorted(
                candidates,
                key=lambda x: -x.get("conviction_score", 0)
            )
        
        # Assign rank
        for i, candidate in enumerate(sorted_candidates, start=1):
            candidate["rank"] = i
        
        return sorted_candidates
    
    def select_top_candidates(
        self,
        ranked_candidates: List[Dict[str, Any]],
        max_count: int = 20,
        min_count: int = 5
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Select top N candidates for portfolio with Cash Drag Management (FR-3.1.C.10.3)
        
        Cash Drag Management Logic:
        If Count(Qualified Candidates) < 5: Portfolio = 100% Cash
        
        Rationale: A universe yielding only 1-4 signals indicates a "risk-off" 
        or "data error" environment; the strategy relies on diversification.
        
        Args:
            ranked_candidates: Ranked candidate list
            max_count: Maximum number to select (default: 20 per FR-3.1.C.4)
            min_count: Minimum candidates required (default: 5 per FR-3.1.C.10.3)
        
        Returns:
            Tuple of (selected_candidates, is_cash_mode)
            - selected_candidates: List of candidates (empty if cash mode)
            - is_cash_mode: True if portfolio should be 100% cash
        """
        # FR-3.1.C.10.3: Cash Drag Management
        if len(ranked_candidates) < min_count:
            print(f"⚠️ CASH DRAG MANAGEMENT: Only {len(ranked_candidates)} candidates (< {min_count} minimum)")
            print(f"   Portfolio will be 100% CASH per FR-3.1.C.10.3")
            return [], True
        
        return ranked_candidates[:max_count], False
    
    def check_cash_drag(
        self,
        candidates_count: int,
        min_count: int = 5
    ) -> bool:
        """
        Check if Cash Drag Management should be triggered (FR-3.1.C.10.3)
        
        Args:
            candidates_count: Number of qualified candidates
            min_count: Minimum required (default: 5)
            
        Returns:
            True if portfolio should go to 100% cash
        """
        return candidates_count < min_count
    
    def apply_rank_buffer(
        self,
        new_candidates: List[Dict[str, Any]],
        current_holdings: List[Dict[str, Any]],
        buffer: int = 5
    ) -> Dict[str, Any]:
        """
        Apply rank buffer to prevent excessive churn (FR-3.1.C.10.2)
        
        A new candidate enters portfolio only if:
        Rank(Candidate_new) < Rank(Holding_worst) - Buffer
        
        Args:
            new_candidates: New ranked candidates
            current_holdings: Current portfolio holdings
            buffer: Rank buffer (default: 5)
        
        Returns:
            Dict with entry decisions
        """
        if not current_holdings:
            # No current holdings, accept top candidates
            return {
                "entries": new_candidates,
                "exits": [],
                "holds": []
            }
        
        # Find worst holding rank
        worst_holding = max(
            current_holdings,
            key=lambda x: x.get("rank", 0)
        )
        worst_rank = worst_holding.get("rank", 0)
        
        entries = []
        holds = []
        exits = []
        
        # Check each new candidate
        for candidate in new_candidates:
            candidate_rank = candidate.get("rank", float('inf'))
            ticker = candidate.get("ticker")
            
            # Check if already held
            is_held = any(h.get("ticker") == ticker for h in current_holdings)
            
            if is_held:
                holds.append(candidate)
            elif candidate_rank < (worst_rank - buffer):
                # Qualifies for entry
                entries.append(candidate)
                
                # Mark worst holding for exit
                if worst_holding not in exits:
                    exits.append(worst_holding)
        
        return {
            "entries": entries,
            "exits": exits,
            "holds": holds
        }


# Singleton instance
_conviction_scorer = None


def get_conviction_scorer(
    herding_weight: float = ConvictionScorer.DEFAULT_HERDING_WEIGHT,
    insider_weight: float = ConvictionScorer.DEFAULT_INSIDER_WEIGHT
) -> ConvictionScorer:
    """Get or create conviction scorer instance"""
    global _conviction_scorer
    if _conviction_scorer is None:
        _conviction_scorer = ConvictionScorer(
            herding_weight=herding_weight,
            insider_weight=insider_weight
        )
    return _conviction_scorer

