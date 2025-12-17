"""
Mock SEC Data Provider for Development/Testing
Generates synthetic 13F and Form 4 data to avoid API consumption
"""

import random
import string
from typing import List, Dict, Any
from datetime import date, datetime, timedelta
from faker import Faker

fake = Faker()


class MockSECProvider:
    """Mock provider for SEC filing data"""
    
    # Sample institutional investors
    MOCK_INSTITUTIONS = [
        {"name": "Mock Capital Management", "cik": "0001234567", "aum": 5_000_000_000},
        {"name": "Test Investment Partners", "cik": "0001234568", "aum": 3_500_000_000},
        {"name": "Demo Asset Advisors", "cik": "0001234569", "aum": 2_800_000_000},
        {"name": "Sample Hedge Fund", "cik": "0001234570", "aum": 4_200_000_000},
        {"name": "Placeholder Investments", "cik": "0001234571", "aum": 1_900_000_000},
    ]
    
    # Sample stocks
    MOCK_STOCKS = [
        {"ticker": "MOCK", "cusip": "123456789", "name": "Mock Corp", "price": 150.0, "market_cap": 5_000_000_000},
        {"ticker": "TEST", "cusip": "234567890", "name": "Test Inc", "price": 85.50, "market_cap": 4_200_000_000},
        {"ticker": "DEMO", "cusip": "345678901", "name": "Demo Technologies", "price": 220.75, "market_cap": 7_500_000_000},
        {"ticker": "SMPL", "cusip": "456789012", "name": "Sample Industries", "price": 42.30, "market_cap": 3_100_000_000},
        {"ticker": "PLCH", "cusip": "567890123", "name": "Placeholder Systems", "price": 178.25, "market_cap": 6_800_000_000},
    ]
    
    # C-Level titles
    C_LEVEL_TITLES = [
        "Chief Executive Officer",
        "Chief Financial Officer",
        "Chief Operating Officer",
        "Chief Technology Officer",
        "President",
        "Chairman"
    ]
    
    # Transaction codes
    TRANSACTION_CODES = {
        'P': 0.4,  # Purchase - 40% probability
        'S': 0.3,  # Sale - 30% probability
        'A': 0.2,  # Award - 20% probability
        'M': 0.1   # Exercise - 10% probability
    }
    
    def __init__(self, seed: int = 42):
        """Initialize mock provider with seed for reproducibility"""
        random.seed(seed)
        fake.seed_instance(seed)
    
    def generate_13f_filing(
        self,
        institution_index: int = 0,
        period_end_date: date = None,
        num_holdings: int = None
    ) -> Dict[str, Any]:
        """
        Generate a mock 13F filing
        
        Args:
            institution_index: Index into MOCK_INSTITUTIONS (0-4)
            period_end_date: Quarter end date (defaults to recent quarter)
            num_holdings: Number of holdings (random if None)
        
        Returns:
            Dict with filing data and holdings
        """
        if period_end_date is None:
            # Default to most recent quarter end
            today = date.today()
            quarter = (today.month - 1) // 3
            period_end_date = date(today.year, (quarter * 3) + 3, 1) - timedelta(days=1)
        
        # Filing date is 45 days after period end (typical 13F timing)
        filing_date = period_end_date + timedelta(days=45)
        
        institution = self.MOCK_INSTITUTIONS[institution_index % len(self.MOCK_INSTITUTIONS)]
        
        # Random number of holdings between 10-30
        if num_holdings is None:
            num_holdings = random.randint(10, 30)
        
        # Generate holdings
        holdings = []
        total_value = 0
        
        for i in range(num_holdings):
            stock = random.choice(self.MOCK_STOCKS)
            shares = random.randint(10_000, 1_000_000)
            value = (shares * stock["price"]) / 1000  # in thousands
            total_value += value
            
            holdings.append({
                "cusip": stock["cusip"],
                "ticker": stock["ticker"],
                "name_of_issuer": stock["name"],
                "value": round(value, 2),
                "shares_or_prn_amt": shares,
                "shares_or_prn_amt_type": "SH",
                "investment_discretion": random.choice(["SOLE", "SHARED"]),
                "voting_authority_sole": shares if random.random() > 0.3 else 0,
                "voting_authority_shared": 0 if shares else shares,
                "voting_authority_none": 0
            })
        
        filing = {
            "filing_id": f"mock_13f_{institution['cik']}_{period_end_date.isoformat()}",
            "cik": institution["cik"],
            "institution_name": institution["name"],
            "filing_date": filing_date.isoformat(),
            "period_end_date": period_end_date.isoformat(),
            "accession_number": f"0001234567-23-{random.randint(100000, 999999)}",
            "form_type": "13F-HR",
            "total_value": round(total_value, 2),
            "holdings_count": len(holdings),
            "holdings": holdings
        }
        
        return filing
    
    def generate_historical_13f_filings(
        self,
        institution_index: int = 0,
        start_date: date = None,
        end_date: date = None,
        quarters: int = 8
    ) -> List[Dict[str, Any]]:
        """
        Generate historical 13F filings for multiple quarters
        
        Args:
            institution_index: Index into MOCK_INSTITUTIONS
            start_date: Start date (defaults to 2 years ago)
            end_date: End date (defaults to today)
            quarters: Number of quarters to generate
        
        Returns:
            List of filing dicts
        """
        if end_date is None:
            end_date = date.today()
        
        if start_date is None:
            start_date = end_date - timedelta(days=quarters * 90)
        
        filings = []
        
        # Generate quarterly filings
        current_date = end_date
        for _ in range(quarters):
            # Find previous quarter end
            quarter = (current_date.month - 1) // 3
            quarter_end = date(current_date.year, (quarter * 3) + 3, 1) - timedelta(days=1)
            
            if quarter_end < start_date:
                break
            
            filing = self.generate_13f_filing(institution_index, quarter_end)
            filings.append(filing)
            
            # Move to previous quarter
            current_date = quarter_end - timedelta(days=1)
        
        filings.reverse()  # Chronological order
        return filings
    
    def generate_form4_transaction(
        self,
        ticker: str = None,
        transaction_date: date = None,
        is_purchase: bool = None
    ) -> Dict[str, Any]:
        """
        Generate a mock Form 4 insider transaction
        
        Args:
            ticker: Stock ticker (random if None)
            transaction_date: Date of transaction (recent if None)
            is_purchase: True for purchase, False for sale, None for random
        
        Returns:
            Dict with Form 4 transaction data
        """
        if ticker is None:
            stock = random.choice(self.MOCK_STOCKS)
            ticker = stock["ticker"]
        else:
            stock = next((s for s in self.MOCK_STOCKS if s["ticker"] == ticker), self.MOCK_STOCKS[0])
        
        if transaction_date is None:
            transaction_date = date.today() - timedelta(days=random.randint(1, 90))
        
        # Filing date is 2 days after transaction (required by SEC)
        filing_date = transaction_date + timedelta(days=2)
        
        # Generate transaction code
        if is_purchase is not None:
            transaction_code = 'P' if is_purchase else 'S'
        else:
            transaction_code = random.choices(
                list(self.TRANSACTION_CODES.keys()),
                weights=list(self.TRANSACTION_CODES.values())
            )[0]
        
        acquired_disposed_code = 'A' if transaction_code in ['P', 'A', 'M'] else 'D'
        
        # Generate shares and price with some noise
        shares = random.randint(1_000, 50_000)
        price = stock["price"] * random.uniform(0.95, 1.05)
        
        # Generate insider details
        is_officer = random.random() > 0.3
        officer_title = random.choice(self.C_LEVEL_TITLES) if is_officer else None
        
        transaction = {
            "transaction_id": f"mock_form4_{fake.uuid4()}",
            "accession_number": f"0001234567-23-{random.randint(100000, 999999)}",
            "filing_date": filing_date.isoformat(),
            "issuer_cik": f"000{random.randint(1000000, 9999999)}",
            "issuer_name": stock["name"],
            "ticker": ticker,
            "reporting_owner_name": fake.name(),
            "reporting_owner_cik": f"000{random.randint(1000000, 9999999)}",
            "is_director": random.random() > 0.5 if not is_officer else False,
            "is_officer": is_officer,
            "officer_title": officer_title,
            "is_ten_percent_owner": random.random() > 0.9,
            "transaction_code": transaction_code,
            "transaction_date": transaction_date.isoformat(),
            "deemed_execution_date": None,
            "shares": shares,
            "price_per_share": round(price, 2),
            "acquired_disposed_code": acquired_disposed_code,
            "ownership_nature": "direct",
            "is_10b51_plan": False
        }
        
        return transaction
    
    def generate_insider_buying_cluster(
        self,
        ticker: str = None,
        base_date: date = None,
        num_insiders: int = 3,
        total_value_min: float = 200_000
    ) -> List[Dict[str, Any]]:
        """
        Generate a cluster of insider purchases (for testing insider signal)
        
        Args:
            ticker: Stock ticker
            base_date: Base date for cluster (within 30 days)
            num_insiders: Number of unique insiders
            total_value_min: Minimum total purchase value
        
        Returns:
            List of Form 4 transactions
        """
        if ticker is None:
            ticker = random.choice(self.MOCK_STOCKS)["ticker"]
        
        if base_date is None:
            base_date = date.today() - timedelta(days=15)
        
        transactions = []
        total_value = 0
        
        for _ in range(num_insiders):
            # Transaction within 30 days of base date
            txn_date = base_date + timedelta(days=random.randint(0, 30))
            
            txn = self.generate_form4_transaction(
                ticker=ticker,
                transaction_date=txn_date,
                is_purchase=True
            )
            
            # Ensure it's a C-level officer
            txn["is_officer"] = True
            txn["officer_title"] = random.choice(self.C_LEVEL_TITLES)
            
            # Adjust shares to meet minimum value
            stock = next(s for s in self.MOCK_STOCKS if s["ticker"] == ticker)
            if total_value < total_value_min:
                needed_value = (total_value_min - total_value) / num_insiders
                txn["shares"] = int(needed_value / stock["price"]) + random.randint(100, 1000)
                total_value += txn["shares"] * stock["price"]
            
            transactions.append(txn)
        
        return transactions


# Singleton instance
_mock_sec_provider = None


def get_mock_sec_provider() -> MockSECProvider:
    """Get or create mock SEC provider instance"""
    global _mock_sec_provider
    if _mock_sec_provider is None:
        _mock_sec_provider = MockSECProvider()
    return _mock_sec_provider

