"""
Backtest Orchestrator
Integrates SEC data, historical prices, and backtest engine
Supports both Custom Engine and LEAN Engine
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import os

# Import services with error handling
try:
    from app.services.historical_backtest_engine import HistoricalBacktestEngine
except ImportError as e:
    print(f"⚠️ Could not import HistoricalBacktestEngine: {e}")
    HistoricalBacktestEngine = None

try:
    from app.services.sec_edgar_service import SECEdgarService
except ImportError as e:
    print(f"⚠️ Could not import SECEdgarService: {e}")
    SECEdgarService = None

try:
    from app.services.alphavantage_service import AlphaVantageService
except ImportError as e:
    print(f"⚠️ Could not import AlphaVantageService: {e}")
    AlphaVantageService = None

# LEANAdapter is optional
try:
    from app.services.lean_adapter import LEANAdapter
    LEAN_ADAPTER_AVAILABLE = True
except ImportError:
    LEAN_ADAPTER_AVAILABLE = False
    LEANAdapter = None

# BacktraderEngine is optional
try:
    from app.services.backtrader_engine import BacktraderEngine, get_backtrader_engine
    BACKTRADER_AVAILABLE = True
except ImportError:
    BACKTRADER_AVAILABLE = False
    BacktraderEngine = None
    get_backtrader_engine = None


class BacktestOrchestrator:
    """
    Orchestrates the full backtesting process:
    1. Fetch SEC filing signals from PostgreSQL database
    2. Fetch historical prices for relevant stocks from AlphaVantage
    3. Run backtest simulation
    4. Return performance metrics
    """
    
    def __init__(self):
        # Initialize services
        if SECEdgarService is None or AlphaVantageService is None:
            raise ImportError("Required services (SEC or AlphaVantage) not available")
        
        self.sec_service = SECEdgarService()
        self.alphavantage_service = AlphaVantageService()
        print("✅ Backtest Orchestrator initialized with real data services")
    
    async def run_strategy_backtest(
        self,
        start_date: str,
        end_date: str,
        selected_institutions: List[str],
        strategy_config: Dict,
        progress_callback: Optional[callable] = None
    ) -> Dict:
        """
        Run a complete backtest for a given strategy
        Supports both Custom Engine and LEAN Engine
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            selected_institutions: List of institution CIKs
            strategy_config: Full strategy configuration (includes engine_type)
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict with backtest results and metrics
        """
        
        # Determine which engine to use
        engine_type = strategy_config.get('engine_type', 'custom')
        
        print(f"\n{'='*60}")
        print(f"🎯 Backtest Engine: {engine_type.upper()}")
        print(f"{'='*60}\n")
        
        def update_progress(message: str, percent: int, details: List[str] = None, progress_data: Dict = None):
            if progress_callback:
                progress_callback(message, percent, details or [], progress_data)
            print(f"📍 [{percent}%] {message}")
            if details:
                for detail in details:
                    print(f"    • {detail}")
        
        try:
            # Step 1: Fetch SEC signals from PostgreSQL
            print(f"🔍 DEBUG: About to fetch SEC signals")
            print(f"🔍 DEBUG: selected_institutions = {selected_institutions}")
            print(f"🔍 DEBUG: selected_institutions type = {type(selected_institutions)}")
            print(f"🔍 DEBUG: len(selected_institutions) = {len(selected_institutions) if selected_institutions else 0}")

            institutions_msg = f"{len(selected_institutions)} institutions selected" if selected_institutions else "❌ NO INSTITUTIONS SELECTED - This will cause backtest to fail!"
            update_progress("Analyzing institutional holdings from SEC data...", 10, [
                institutions_msg,
                f"Date range: {start_date} to {end_date}",
                f"CIKs: {', '.join(selected_institutions[:3]) + ('...' if len(selected_institutions or []) > 3 else '') if selected_institutions else 'NONE'}",
                "📊 Scanning 13F filings for buy/sell signals"
            ])
            signals = await self.fetch_sec_signals(
                start_date, 
                end_date, 
                selected_institutions,
                strategy_config
            )

            print(f"🔍 DEBUG: fetch_sec_signals returned {len(signals) if signals else 0} signals")

            # Log signal summary for debugging
            if signals:
                tickers_found = set(s.get('ticker') for s in signals)
                institutions_found = set(s.get('institution_cik') for s in signals)
                print(f"🔍 DEBUG: Signals from {len(institutions_found)} institutions, {len(tickers_found)} tickers")
                print(f"🔍 DEBUG: Sample signal: {signals[0] if signals else 'None'}")
            
            if not signals:
                update_progress("No signals found", 100, [
                    "⚠️ No institutional activity found for selected criteria",
                    "Try: Expand date range or select more institutions"
                ])
                return {
                    'error': 'No signals found for the given criteria',
                    'total_return': 0,
                    'sharpe_ratio': 0,
                    'max_drawdown': 0
                }
            
            if len(signals) > 0:
                update_progress(f"✅ Found {len(signals)} trading signals from SEC data!", 30, [
                    f"📈 Signals ready for backtesting",
                    f"Date range covers institutional activity",
                    f"Next: Fetching historical stock prices"
                ])
            else:
                update_progress("❌ No trading signals found in SEC data", 30, [
                    f"⚠️ No institutional activity detected",
                    f"Try: Expand date range or select more institutions",
                    f"Check: Are institutions selected in Step 2?"
                ])
            
            # Step 2: Get unique CUSIPs from signals (use CUSIP as ticker for now)
            cusips = list(set([s['cusip'] for s in signals]))  # cusip field contains CUSIP
            print(f"🔍 Found {len(cusips)} unique CUSIPs in signals: {cusips[:5]}...")

            # Comprehensive CUSIP to ticker mapping for major stocks
            # Covers S&P 500, NASDAQ 100, and popular institutional holdings (300+ stocks)
            cusip_to_ticker_map = {
                # ============== MEGA CAP TECH (Top 10 by Market Cap) ==============
                '037833100': 'AAPL',   # Apple Inc.
                '594918104': 'MSFT',   # Microsoft Corporation
                '67066G104': 'NVDA',   # NVIDIA Corporation
                '02079K305': 'GOOGL',  # Alphabet Inc. Class A
                '02079K107': 'GOOG',   # Alphabet Inc. Class C
                '023135106': 'AMZN',   # Amazon.com Inc.
                '30303M102': 'META',   # Meta Platforms Inc.
                '88160R101': 'TSLA',   # Tesla Inc.
                '06738E204': 'BRK.B',  # Berkshire Hathaway Inc. Class B
                '084670207': 'BRK.A',  # Berkshire Hathaway Inc. Class A
                
                # ============== FINANCIALS ==============
                '46625H100': 'JPM',    # JPMorgan Chase & Co.
                '92826C839': 'V',      # Visa Inc.
                '57636Q104': 'MA',     # Mastercard Inc.
                '172967424': 'C',      # Citigroup Inc.
                '060505104': 'BAC',    # Bank of America Corp.
                '38141G104': 'GS',     # Goldman Sachs Group Inc.
                '617446448': 'MS',     # Morgan Stanley
                '902973304': 'USB',    # U.S. Bancorp
                '949746101': 'WFC',    # Wells Fargo & Company
                '084670702': 'BLK',    # BlackRock Inc.
                '808513105': 'SCHW',   # Charles Schwab Corp.
                '00206R102': 'T',      # AT&T Inc.
                '035242103': 'AXP',    # American Express Company
                '19416Q104': 'COF',    # Capital One Financial
                '404119102': 'HIG',    # Hartford Financial Services
                '717081103': 'PFG',    # Principal Financial Group
                '758750103': 'RJF',    # Raymond James Financial
                
                # ============== HEALTHCARE ==============
                '478160104': 'JNJ',    # Johnson & Johnson
                '91324P102': 'UNH',    # UnitedHealth Group
                '72919P200': 'LLY',    # Eli Lilly and Company
                '670100205': 'NVO',    # Novo Nordisk A/S
                '02209S103': 'ABBV',   # AbbVie Inc.
                '717081103': 'PFE',    # Pfizer Inc.
                '58933Y105': 'MRK',    # Merck & Co. Inc.
                '742935100': 'TMO',    # Thermo Fisher Scientific
                '00287Y109': 'ABBV',   # AbbVie Inc.
                '031162100': 'AMGN',   # Amgen Inc.
                '00846U101': 'GILD',   # Gilead Sciences Inc.
                '075887109': 'BIIB',   # Biogen Inc.
                '743315103': 'CVS',    # CVS Health Corporation
                '127036109': 'CAH',    # Cardinal Health Inc.
                '571903202': 'MCD',    # McDonald's Corporation
                '25179M103': 'DHR',    # Danaher Corporation
                '09062X103': 'REGN',   # Regeneron Pharmaceuticals
                '91913Y100': 'VRTX',   # Vertex Pharmaceuticals
                '460867106': 'ISRG',   # Intuitive Surgical
                '119889108': 'BMY',    # Bristol-Myers Squibb
                
                # ============== CONSUMER / RETAIL ==============
                '931142103': 'WMT',    # Walmart Inc.
                '191216100': 'KO',     # The Coca-Cola Company
                '713448108': 'PEP',    # PepsiCo Inc.
                '22160K105': 'COST',   # Costco Wholesale Corporation
                '579780206': 'MDLZ',   # Mondelez International
                '742718109': 'QCOM',   # QUALCOMM Inc.
                '742580103': 'PG',     # Procter & Gamble Co.
                '437076102': 'HD',     # The Home Depot Inc.
                '501044101': 'KMB',    # Kimberly-Clark Corporation
                '168088102': 'CHD',    # Church & Dwight Co. Inc.
                '166764100': 'CVX',    # Chevron Corporation
                '126650100': 'CVX',    # Chevron Corporation
                '902494103': 'TGT',    # Target Corporation
                '552953101': 'MAR',    # Marriott International
                '441131103': 'HLT',    # Hilton Worldwide Holdings
                '254687106': 'DIS',    # The Walt Disney Company
                '609207105': 'MNST',   # Monster Beverage Corporation
                '617446448': 'NKE',    # Nike Inc.
                '780259107': 'SBUX',   # Starbucks Corporation
                '218352102': 'CMG',    # Chipotle Mexican Grill
                '293561104': 'YUM',    # Yum! Brands Inc.
                '548661107': 'LOW',    # Lowe's Companies Inc.
                '67011P100': 'ORLY',   # O'Reilly Automotive Inc.
                
                # ============== TECHNOLOGY / SEMICONDUCTORS ==============
                '460146103': 'INTC',   # Intel Corporation
                '00724F101': 'AMD',    # Advanced Micro Devices
                '001055102': 'ACN',    # Accenture plc
                '87612E106': 'TXN',    # Texas Instruments Inc.
                '098659109': 'AVGO',   # Broadcom Inc.
                '00790C107': 'ADBE',   # Adobe Inc.
                '79466L302': 'CRM',    # Salesforce Inc.
                '67103H107': 'ORCL',   # Oracle Corporation
                '459200101': 'IBM',    # International Business Machines
                '17275R102': 'CSCO',   # Cisco Systems Inc.
                '64110L106': 'NFLX',   # Netflix Inc.
                '494368103': 'KLAC',   # KLA Corporation
                '532457108': 'LRCX',   # Lam Research Corporation
                '007903107': 'AMAT',   # Applied Materials Inc.
                '457030104': 'CDNS',   # Cadence Design Systems
                '858119100': 'SNPS',   # Synopsys Inc.
                '03662Q105': 'MU',     # Micron Technology Inc.
                '464287200': 'ARM',    # Arm Holdings plc
                '69608A108': 'PLTR',   # Palantir Technologies Inc.
                '770700102': 'HOOD',   # Robinhood Markets Inc.
                '81762P102': 'NOW',    # ServiceNow Inc.
                '88579Y101': 'MMM',    # 3M Company
                '902104108': 'UBER',   # Uber Technologies Inc.
                '90353T100': 'UBER',   # Uber Technologies Inc. (alt CUSIP)
                '55087P104': 'LYFT',   # Lyft Inc.
                '79468M107': 'SQ',     # Block Inc. (Square)
                '87918A105': 'TEAM',   # Atlassian Corporation
                '29786A106': 'DDOG',   # Datadog Inc.
                '83088M102': 'SNOW',   # Snowflake Inc.
                '26856L103': 'ESTC',   # Elastic N.V.
                '49271V100': 'KEYS',   # Keysight Technologies
                '78468R101': 'STX',    # Seagate Technology
                '88160R101': 'WDC',    # Western Digital Corporation
                
                # ============== ENERGY ==============
                '30231G102': 'XOM',    # Exxon Mobil Corporation
                '20825C104': 'COP',    # ConocoPhillips
                '171340102': 'SLB',    # Schlumberger N.V.
                '337738108': 'FANG',   # Diamondback Energy
                '71654V101': 'PXD',    # Pioneer Natural Resources
                '29251P107': 'OXY',    # Occidental Petroleum
                '374166104': 'HAL',    # Halliburton Company
                '651290107': 'NEE',    # NextEra Energy Inc.
                '278865100': 'DUK',    # Duke Energy Corporation
                '84857L101': 'SO',     # Southern Company
                '253868103': 'ED',     # Consolidated Edison
                '00104H105': 'AEP',    # American Electric Power
                '92857H109': 'VLO',    # Valero Energy Corporation
                '759509102': 'PSX',    # Phillips 66
                '608671108': 'EOG',    # EOG Resources Inc.
                
                # ============== INDUSTRIALS ==============
                '097023105': 'BA',     # The Boeing Company
                '149123101': 'CAT',    # Caterpillar Inc.
                '369550108': 'GE',     # General Electric Company
                '443320106': 'HON',    # Honeywell International
                '482480100': 'RTX',    # RTX Corporation
                '549271104': 'LMT',    # Lockheed Martin Corporation
                '639057101': 'GD',     # General Dynamics Corporation
                '693475105': 'NOC',    # Northrop Grumman Corporation
                '589331107': 'MMM',    # 3M Company
                '427866108': 'EMR',    # Emerson Electric Co.
                '228368106': 'CNI',    # Canadian National Railway
                '742680103': 'UNP',    # Union Pacific Corporation
                '249906108': 'DE',     # Deere & Company
                '353015103': 'FDX',    # FedEx Corporation
                '911312106': 'UPS',    # United Parcel Service
                '00828C109': 'NSC',    # Norfolk Southern Corporation
                '12503M108': 'DAL',    # Delta Air Lines Inc.
                '847215100': 'LUV',    # Southwest Airlines Co.
                '02376R102': 'AAL',    # American Airlines Group
                '910047109': 'UAL',    # United Airlines Holdings
                
                # ============== COMMUNICATIONS ==============
                '92343E102': 'VZ',     # Verizon Communications
                '00206R102': 'T',      # AT&T Inc.
                '872590104': 'TMUS',   # T-Mobile US Inc.
                '17275R102': 'CSCO',   # Cisco Systems Inc.
                '25470M109': 'DISH',   # DISH Network Corporation
                '165167107': 'CHTR',   # Charter Communications
                '194368107': 'CMCSA',  # Comcast Corporation
                '353514102': 'FOX',    # Fox Corporation Class B
                '353527105': 'FOXA',   # Fox Corporation Class A
                '92332F100': 'VIA',    # Viacom Inc. (now Paramount)
                '69318G106': 'PARA',   # Paramount Global
                
                # ============== REAL ESTATE ==============
                '03938L108': 'ARE',    # Alexandria Real Estate
                '05348J108': 'O',      # Realty Income Corporation
                '126117100': 'PLD',    # Prologis Inc.
                '277461109': 'AMT',    # American Tower Corporation
                '29444U700': 'EQIX',   # Equinix Inc.
                '79709T106': 'PSA',    # Public Storage
                '843318109': 'SPG',    # Simon Property Group
                '812348108': 'AVB',    # AvalonBay Communities
                '30063P105': 'EXR',    # Extra Space Storage
                '253868103': 'DLR',    # Digital Realty Trust
                
                # ============== MATERIALS ==============
                '549271104': 'LIN',    # Linde plc
                '037225103': 'APD',    # Air Products and Chemicals
                '828810100': 'SHW',    # Sherwin-Williams Company
                '260003108': 'DD',     # DuPont de Nemours
                '231021106': 'ECL',    # Ecolab Inc.
                '647742104': 'NEM',    # Newmont Corporation
                '345370860': 'FCX',    # Freeport-McMoRan Inc.
                '694550108': 'NUE',    # Nucor Corporation
                '371901109': 'CTVA',   # Corteva Inc.
                '168892405': 'CF',     # CF Industries Holdings
                
                # ============== ETFs ==============
                '78378X107': 'SPY',    # SPDR S&P 500 ETF Trust
                '464287465': 'QQQ',    # Invesco QQQ Trust
                '922908363': 'VTI',    # Vanguard Total Stock Market ETF
                '922908785': 'VOO',    # Vanguard S&P 500 ETF
                '464287622': 'IWM',    # iShares Russell 2000 ETF
                '46428R109': 'IWF',    # iShares Russell 1000 Growth ETF
                '46428R208': 'IWD',    # iShares Russell 1000 Value ETF
                '464287747': 'DIA',    # SPDR Dow Jones Industrial Average ETF
                '78464A870': 'GLD',    # SPDR Gold Shares
                '46138E669': 'EEM',    # iShares MSCI Emerging Markets ETF
                
                # ============== ADDITIONAL POPULAR STOCKS ==============
                '879868100': 'TJX',    # TJX Companies Inc.
                '67091P105': 'PANW',   # Palo Alto Networks
                '22788C105': 'CRWD',   # CrowdStrike Holdings
                '98421M106': 'WDAY',   # Workday Inc.
                '90353P109': 'TTD',    # The Trade Desk Inc.
                '74340W103': 'PYPL',   # PayPal Holdings Inc.
                '98954M101': 'ZS',     # Zscaler Inc.
                '629377106': 'NDAQ',   # Nasdaq Inc.
                '09260D107': 'BKNG',   # Booking Holdings Inc.
                '053015103': 'ABNB',   # Airbnb Inc.
                '780259206': 'SPOT',   # Spotify Technology S.A.
                '33616C101': 'FISV',   # Fiserv Inc.
                '36467W109': 'FIS',    # Fidelity National Information
                '37045V100': 'GPN',    # Global Payments Inc.
                '02079K387': 'GOOG',   # Alphabet Inc. (alt)
                '73757R101': 'STZ',    # Constellation Brands
                '171340102': 'SLB',    # Schlumberger N.V.
                '79530K109': 'ZM',     # Zoom Video Communications
                '872540109': 'TWLO',   # Twilio Inc.
                '876892101': 'TRMB',   # Trimble Inc.
                '29274F104': 'ENPH',   # Enphase Energy Inc.
                '837649128': 'SEDG',   # SolarEdge Technologies
                '171798101': 'CIEN',   # Ciena Corporation
                '74587V107': 'QRVO',   # Qorvo Inc.
                '860630102': 'SWKS',   # Skyworks Solutions
                '29260G107': 'SQ',     # Block Inc. (alt)
                '85571B105': 'STLA',   # Stellantis N.V.
                '345370105': 'F',      # Ford Motor Company
                '370442105': 'GM',     # General Motors Company
                '86959K105': 'RIVN',   # Rivian Automotive
                '55616P104': 'LCID',   # Lucid Group Inc.
                '91680M107': 'UPST',   # Upstart Holdings
                '04269E107': 'AFRM',   # Affirm Holdings
                '78397Q107': 'ROKU',   # Roku Inc.
                '85208M102': 'SHOP',   # Shopify Inc.
                '87936R202': 'TDOC',   # Teladoc Health
                '98978V103': 'Z',      # Zillow Group Inc.
                '98978L204': 'ZG',     # Zillow Group Inc. Class A
                '82968B103': 'SNAP',   # Snap Inc.
                '01609W102': 'PINS',   # Pinterest Inc.
                '90184L102': 'TWTR',   # Twitter Inc. (now X)
                '78440X101': 'SE',     # Sea Limited
                '552081110': 'MDB',    # MongoDB Inc.
                '293726100': 'NET',    # Cloudflare Inc.
                '29188C106': 'BILL',   # Bill.com Holdings
                '40171V100': 'GTLB',   # GitLab Inc.
                '88025T102': 'SOFI',   # SoFi Technologies
                '89417E109': 'COIN',   # Coinbase Global Inc.
                '13342B105': 'HOOD',   # Robinhood Markets (alt)
                '91818X108': 'VALE',   # Vale S.A.
                '670346105': 'ODFL',   # Old Dominion Freight Line
                '539830109': 'MCHP',   # Microchip Technology
                '571748102': 'ON',     # ON Semiconductor
                '00971T101': 'ALGN',   # Align Technology
                '460599106': 'IDXX',   # IDEXX Laboratories
                '232723107': 'DXCM',   # Dexcom Inc.
                '81725T100': 'HOLX',   # Hologic Inc.
                '009158106': 'AIR',    # AAR Corp.
                '872565100': 'TXT',    # Textron Inc.
                '437076102': 'HWM',    # Howmet Aerospace
                '62955J103': 'MRNA',   # Moderna Inc.
                '075508107': 'BNTX',   # BioNTech SE
                '594918104': 'MSFT',   # Microsoft Corporation
            }
            
            # Try to extract ticker from company name for common patterns
            def infer_ticker_from_name(name: str) -> str:
                """Try to infer ticker symbol from company name (200+ patterns)"""
                if not name:
                    return None
                name_upper = name.upper()
                # Comprehensive name to ticker mappings (sorted by specificity)
                name_patterns = {
                    # Mega Cap Tech
                    'APPLE': 'AAPL', 'MICROSOFT': 'MSFT', 'AMAZON': 'AMZN', 'AMAZON.COM': 'AMZN',
                    'GOOGLE': 'GOOGL', 'ALPHABET': 'GOOGL', 'META PLATFORMS': 'META', 'META ': 'META',
                    'FACEBOOK': 'META', 'NVIDIA': 'NVDA', 'TESLA': 'TSLA', 'BERKSHIRE': 'BRK.B',
                    # Financials
                    'JPMORGAN': 'JPM', 'JP MORGAN': 'JPM', 'BANK OF AMERICA': 'BAC', 'CITIGROUP': 'C',
                    'GOLDMAN SACHS': 'GS', 'MORGAN STANLEY': 'MS', 'WELLS FARGO': 'WFC',
                    'VISA': 'V', 'MASTERCARD': 'MA', 'AMERICAN EXPRESS': 'AXP', 'BLACKROCK': 'BLK',
                    'CAPITAL ONE': 'COF', 'CHARLES SCHWAB': 'SCHW', 'PAYPAL': 'PYPL',
                    # Healthcare
                    'UNITEDHEALTH': 'UNH', 'JOHNSON & JOHNSON': 'JNJ', 'JOHNSON AND JOHNSON': 'JNJ',
                    'ELI LILLY': 'LLY', 'NOVO NORDISK': 'NVO', 'NOVO-NORDISK': 'NVO',
                    'ABBVIE': 'ABBV', 'PFIZER': 'PFE', 'MERCK': 'MRK', 'THERMO FISHER': 'TMO',
                    'AMGEN': 'AMGN', 'GILEAD': 'GILD', 'BIOGEN': 'BIIB', 'REGENERON': 'REGN',
                    'VERTEX': 'VRTX', 'MODERNA': 'MRNA', 'BIONTECH': 'BNTX', 'CVS': 'CVS',
                    'INTUITIVE SURGICAL': 'ISRG', 'BRISTOL-MYERS': 'BMY', 'BRISTOL MYERS': 'BMY',
                    # Consumer
                    'WALMART': 'WMT', 'WAL-MART': 'WMT', 'COCA-COLA': 'KO', 'COCA COLA': 'KO', 'COKE': 'KO',
                    'PEPSICO': 'PEP', 'PEPSI': 'PEP', 'COSTCO': 'COST', 'PROCTER & GAMBLE': 'PG',
                    'PROCTER AND GAMBLE': 'PG', 'HOME DEPOT': 'HD', 'LOWES': 'LOW', "LOWE'S": 'LOW',
                    'TARGET': 'TGT', 'DISNEY': 'DIS', 'WALT DISNEY': 'DIS', 'NIKE': 'NKE',
                    'STARBUCKS': 'SBUX', 'MCDONALD': 'MCD', "MCDONALD'S": 'MCD', 'CHIPOTLE': 'CMG',
                    'YUM BRANDS': 'YUM', 'YUM!': 'YUM', 'NETFLIX': 'NFLX', 'MONDELEZ': 'MDLZ',
                    'MARRIOTT': 'MAR', 'HILTON': 'HLT', 'MONSTER BEVERAGE': 'MNST',
                    # Technology
                    'INTEL': 'INTC', 'AMD': 'AMD', 'ADVANCED MICRO': 'AMD', 'QUALCOMM': 'QCOM',
                    'BROADCOM': 'AVGO', 'TEXAS INSTRUMENTS': 'TXN', 'MICRON': 'MU', 'APPLIED MATERIALS': 'AMAT',
                    'LAM RESEARCH': 'LRCX', 'KLA': 'KLAC', 'CADENCE': 'CDNS', 'SYNOPSYS': 'SNPS',
                    'ADOBE': 'ADBE', 'SALESFORCE': 'CRM', 'ORACLE': 'ORCL', 'IBM': 'IBM',
                    'CISCO': 'CSCO', 'ACCENTURE': 'ACN', 'SERVICENOW': 'NOW', 'SNOWFLAKE': 'SNOW',
                    'DATADOG': 'DDOG', 'CROWDSTRIKE': 'CRWD', 'PALO ALTO': 'PANW', 'ZSCALER': 'ZS',
                    'WORKDAY': 'WDAY', 'SPLUNK': 'SPLK', 'ATLASSIAN': 'TEAM', 'MONGODB': 'MDB',
                    'CLOUDFLARE': 'NET', 'TWILIO': 'TWLO', 'ZOOM': 'ZM', 'DOCUSIGN': 'DOCU',
                    # Transport/Mobility
                    'UBER': 'UBER', 'LYFT': 'LYFT', 'AIRBNB': 'ABNB', 'BOOKING': 'BKNG', 'DOORDASH': 'DASH',
                    'DELTA AIR': 'DAL', 'SOUTHWEST AIR': 'LUV', 'AMERICAN AIR': 'AAL', 'UNITED AIR': 'UAL',
                    'UNION PACIFIC': 'UNP', 'FEDEX': 'FDX', 'UPS': 'UPS', 'UNITED PARCEL': 'UPS',
                    'OLD DOMINION': 'ODFL',
                    # Industrial
                    'BOEING': 'BA', 'CATERPILLAR': 'CAT', 'GENERAL ELECTRIC': 'GE', 'HONEYWELL': 'HON',
                    'LOCKHEED MARTIN': 'LMT', 'RAYTHEON': 'RTX', 'RTX': 'RTX', 'NORTHROP GRUMMAN': 'NOC',
                    'GENERAL DYNAMICS': 'GD', '3M': 'MMM', 'EMERSON': 'EMR', 'DEERE': 'DE', 'JOHN DEERE': 'DE',
                    # Energy
                    'EXXON': 'XOM', 'EXXON MOBIL': 'XOM', 'CHEVRON': 'CVX', 'CONOCOPHILLIPS': 'COP',
                    'SCHLUMBERGER': 'SLB', 'EOG RESOURCES': 'EOG', 'PIONEER NATURAL': 'PXD',
                    'OCCIDENTAL': 'OXY', 'HALLIBURTON': 'HAL', 'VALERO': 'VLO', 'PHILLIPS 66': 'PSX',
                    'NEXTERA': 'NEE', 'DUKE ENERGY': 'DUK', 'SOUTHERN CO': 'SO',
                    # Communications
                    'VERIZON': 'VZ', 'AT&T': 'T', 'T-MOBILE': 'TMUS', 'COMCAST': 'CMCSA',
                    'CHARTER COMM': 'CHTR', 'DISH NETWORK': 'DISH', 'PARAMOUNT': 'PARA',
                    # Fintech/Payments
                    'BLOCK': 'SQ', 'SQUARE': 'SQ', 'FISERV': 'FISV', 'GLOBAL PAYMENTS': 'GPN',
                    'FIDELITY NATIONAL': 'FIS', 'COINBASE': 'COIN', 'ROBINHOOD': 'HOOD', 'SOFI': 'SOFI',
                    'AFFIRM': 'AFRM', 'UPSTART': 'UPST',
                    # Automotive
                    'FORD': 'F', 'FORD MOTOR': 'F', 'GENERAL MOTORS': 'GM', 'RIVIAN': 'RIVN', 'LUCID': 'LCID',
                    # Social/Entertainment
                    'SPOTIFY': 'SPOT', 'SNAP': 'SNAP', 'PINTEREST': 'PINS', 'TWITTER': 'TWTR',
                    'ROKU': 'ROKU', 'ROBLOX': 'RBLX', 'ELECTRONIC ARTS': 'EA', 'ACTIVISION': 'ATVI',
                    'TAKE-TWO': 'TTWO', 'SEA LIMITED': 'SE', 'SEA LTD': 'SE',
                    # Real Estate
                    'AMERICAN TOWER': 'AMT', 'CROWN CASTLE': 'CCI', 'PROLOGIS': 'PLD', 'EQUINIX': 'EQIX',
                    'DIGITAL REALTY': 'DLR', 'PUBLIC STORAGE': 'PSA', 'SIMON PROPERTY': 'SPG',
                    'REALTY INCOME': 'O',
                    # Materials
                    'LINDE': 'LIN', 'AIR PRODUCTS': 'APD', 'SHERWIN-WILLIAMS': 'SHW', 'DUPONT': 'DD',
                    'NEWMONT': 'NEM', 'FREEPORT': 'FCX', 'NUCOR': 'NUE',
                    # E-commerce/Retail Tech
                    'SHOPIFY': 'SHOP', 'ETSY': 'ETSY', 'EBAY': 'EBAY', 'WAYFAIR': 'W',
                    'TRADE DESK': 'TTD', 'ZILLOW': 'Z',
                    # Biotech/Medical Devices
                    'DEXCOM': 'DXCM', 'ALIGN TECHNOLOGY': 'ALGN', 'IDEXX': 'IDXX', 'HOLOGIC': 'HOLX',
                    'TELADOC': 'TDOC', 'PALANTIR': 'PLTR',
                    # Semiconductors (additional)
                    'ARM HOLDINGS': 'ARM', 'ARM ': 'ARM', 'ON SEMICONDUCTOR': 'ON', 'MICROCHIP': 'MCHP',
                    'SKYWORKS': 'SWKS', 'QORVO': 'QRVO',
                    # Clean Energy
                    'ENPHASE': 'ENPH', 'SOLAREDGE': 'SEDG', 'FIRST SOLAR': 'FSLR',
                }
                for pattern, ticker in name_patterns.items():
                    if pattern in name_upper:
                        return ticker
                return None

            # Map CUSIPs to tickers with better fallback
            mapped_tickers = []
            unmapped_cusips = []
            for i, cusip in enumerate(cusips):
                if cusip in cusip_to_ticker_map:
                    ticker = cusip_to_ticker_map[cusip]
                else:
                    # Try to find the company name from signals
                    company_name = None
                    for s in signals:
                        if s.get('cusip') == cusip and s.get('name'):
                            company_name = s['name']
                            break
                    
                    inferred = infer_ticker_from_name(company_name) if company_name else None
                    if inferred:
                        ticker = inferred
                        print(f"✅ Inferred ticker from name: {company_name} -> {ticker}")
                    else:
                        # Skip unmapped CUSIPs for price fetching
                        unmapped_cusips.append((cusip, company_name))
                        ticker = None
                        
                if ticker:
                    mapped_tickers.append(ticker)
                    if i < 10:
                        print(f"🔍 Mapped {cusip} -> {ticker}")
            
            if unmapped_cusips:
                print(f"⚠️ {len(unmapped_cusips)} CUSIPs could not be mapped to tickers (skipped):")
                for cusip, name in unmapped_cusips[:5]:
                    print(f"   - {cusip}: {name or 'Unknown'}")

            # Build CUSIP to ticker lookup (only for successfully mapped)
            cusip_to_ticker_lookup = {}
            for i, cusip in enumerate(cusips):
                if cusip in cusip_to_ticker_map:
                    cusip_to_ticker_lookup[cusip] = cusip_to_ticker_map[cusip]
                else:
                    # Check if we inferred a ticker for this CUSIP
                    for s in signals:
                        if s.get('cusip') == cusip and s.get('name'):
                            inferred = infer_ticker_from_name(s['name'])
                            if inferred:
                                cusip_to_ticker_lookup[cusip] = inferred
                            break
            
            # Update signals with actual tickers (only if mapped)
            for signal in signals:
                if signal['cusip'] in cusip_to_ticker_lookup:
                    signal['ticker'] = cusip_to_ticker_lookup[signal['cusip']]
                else:
                    signal['ticker'] = None  # Mark as unmapped
            
            # Filter out signals without valid tickers and get unique tickers
            valid_signals = [s for s in signals if s.get('ticker')]
            tickers = list(set([s['ticker'] for s in valid_signals]))
            
            print(f"📊 {len(valid_signals)}/{len(signals)} signals have mappable tickers")
            print(f"📊 Unique tickers to fetch: {tickers[:10]}{'...' if len(tickers) > 10 else ''}")
            print(f"📊 Successfully processed {len(signals)} signals for {len(tickers)} tickers: {tickers[:5]}...")
            if len(tickers) > 0:
                update_progress(f"📊 Fetching real market data for {len(tickers)} stocks...", 40, [
                    f"Using AlphaVantage API (5 calls/minute limit)",
                    f"Stocks: {', '.join(tickers[:5])}{'...' if len(tickers) > 5 else ''}",
                    f"Estimated: {len(tickers) * 12 // 60}min {len(tickers) * 12 % 60}s",
                    "💰 Real prices ensure accurate backtest results"
                ])
            else:
                update_progress("❌ No stocks to analyze - no signals generated", 40, [
                    f"⚠️ Cannot fetch prices without trading signals",
                    f"Go back to Step 2 and select institutions",
                    f"This usually means SEC data query failed"
            ])
            
            # Step 3: Fetch historical prices (with rate limiting)
            prices_fetched = []
            prices_failed = []
            fetch_start_time = time.time()  # Track when fetching started for ETA calculation
            
            def price_progress_callback(ticker, idx, total, success=True):
                status = "✅" if success else "⚠️"
                if success:
                    prices_fetched.append(ticker)
                else:
                    prices_failed.append(ticker)
                    
                progress_percent = 40 + int((idx/total) * 40)
                
                # Calculate ETA based on elapsed time
                elapsed = time.time() - fetch_start_time
                avg_per_stock = elapsed / max(idx, 1)
                remaining = total - idx
                eta_seconds = remaining * avg_per_stock
                
                # Get friendly break suggestion
                if eta_seconds > 300:
                    break_emoji, break_suggestion = '🚶', 'Take a short walk!'
                elif eta_seconds > 180:
                    break_emoji, break_suggestion = '🍵', 'Time for chai!'
                elif eta_seconds > 120:
                    break_emoji, break_suggestion = '☕', 'Perfect for a coffee!'
                elif eta_seconds > 60:
                    break_emoji, break_suggestion = '🍬', 'Quick snack break?'
                else:
                    break_emoji, break_suggestion = '⚡', 'Almost there!'
                
                # Build detailed progress data
                progress_data = {
                    'processed': idx,
                    'total': total,
                    'completed': len(prices_fetched),
                    'failed': len(prices_failed),
                    'current_ticker': ticker,
                    'failed_tickers': prices_failed[-5:],  # Last 5 failed
                    'success_rate': (len(prices_fetched) / max(idx, 1)) * 100,
                    'eta_seconds': eta_seconds,
                    'eta_message': f"{break_emoji} {break_suggestion}",
                    'stage': 'fetching_data',
                    'break_suggestion': break_suggestion,
                    'break_emoji': break_emoji,
                }

                update_progress(
                    f"📈 Market Data: {idx}/{total} stocks processed",
                    progress_percent,
                    [
                        f"✅ Completed: {len(prices_fetched)} stocks",
                        f"❌ Failed: {len(prices_failed)} stocks",
                        f"🎯 Current: {ticker} ({status})",
                        f"⏱️ Progress: {progress_percent}% complete"
                    ] + ([f"⚠️ Check ALPHAVANTAGE_API_KEY if many failures"] if len(prices_failed) > 3 else []),
                    progress_data
                )
            
            historical_prices = await self.fetch_historical_prices_batch(
                tickers, 
                start_date, 
                end_date,
                price_progress_callback
            )
            
            if not historical_prices:
                print("❌ No price data available - AlphaVantage API key required")
                update_progress("Price data unavailable", 100, [
                    "❌ No price data fetched",
                    "⚠️ ALPHAVANTAGE_API_KEY environment variable required",
                    "📋 Get your free API key from: https://www.alphavantage.co/support/#api-key",
                    f"Attempted to fetch: {len(tickers)} tickers"
                ])
                # Even on API error, preserve signal information so user knows signals were found
                return {
                    'error': 'AlphaVantage API key required for real price data. Signals were generated but price data is unavailable.',
                    'total_return': 0,
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'sec_filings_fetched': len(signals),  # Preserve signal count
                    'stocks_analyzed': tickers,  # Preserve tickers
                    'signals': signals  # Preserve the actual signals
                }
            
            update_progress(f"Price data ready: {len(historical_prices)}/{len(tickers)} stocks", 80, [
                f"✅ Successfully fetched: {len(prices_fetched)} stocks",
                f"⚠️ Failed: {len(prices_failed)} stocks" if prices_failed else "✅ All stocks fetched successfully",
                f"Moving to portfolio simulation..."
            ])
            
            update_progress("Running portfolio simulation...", 85)
            
            # Step 4: Run backtest with selected engine
            if engine_type == 'lean':
                # Use LEAN Engine
                print(f"📍 Using LEAN Engine (QuantConnect)")
                lean_adapter = LEANAdapter()
                
                # Prepare LEAN-compatible config
                lean_config = {
                    'start_date': start_date,
                    'end_date': end_date,
                    'initial_capital': strategy_config.get('initial_capital', 100000)
                }
                
                # Run LEAN backtest
                lean_results = lean_adapter.run_full_backtest(signals, lean_config)
                
                if lean_results is None or 'error' in lean_results:
                    # LEAN failed, fallback to custom engine
                    print(f"⚠️  LEAN engine failed, falling back to Custom Engine")
                    update_progress("LEAN failed, using Custom Engine...", 85)
                    
                    # Extract exit configuration
                    exit_rules = strategy_config.get('exit_rules', {})
                    exit_config = {
                        'enable_stop_loss': True,
                        'enable_take_profit': exit_rules.get('take_profit_enabled', True),
                        'enable_trailing_stop': exit_rules.get('trailing_stop_enabled', True),
                        'stop_loss_pct': exit_rules.get('trailing_stop_pct', 0.10),
                        'take_profit_pct': exit_rules.get('take_profit_pct', 0.30),
                        'trailing_stop_pct': exit_rules.get('trailing_stop_pct', 0.15)
                    }
                    
                    engine = HistoricalBacktestEngine(
                        initial_capital=strategy_config.get('initial_capital', 100000),
                        exit_config=exit_config
                    )
                    raw_results = engine.run_backtest(signals, historical_prices, start_date, end_date)
                    
                    # Wrap metrics under 'summary' key
                    results = {
                        'engine': 'custom (fallback from LEAN)',
                        'summary': {k: v for k, v in raw_results.items() if k not in ['portfolio_history', 'dates', 'trades', 'initial_capital', 'final_value', 'total_trades']},
                        'equity_curve': {
                            'dates': raw_results.get('dates', []),
                            'portfolio_values': raw_results.get('portfolio_history', []),
                            'benchmark_values': []
                        },
                        'trades': raw_results.get('trades', []),
                        'initial_capital': raw_results.get('initial_capital', 100000),
                        'final_value': raw_results.get('final_value', 100000),
                        'execution_time_seconds': 0,
                        'api_calls_made': len(tickers) * 2,
                        'sec_filings_fetched': len(signals),
                        'stocks_analyzed': tickers
                    }
                else:
                    print(f"✅ LEAN backtest completed successfully")
                    results = lean_results
                    results['engine'] = 'LEAN'
            
            else:
                # Use Custom Engine (default)
                print(f"📍 Using Custom Engine (PathVest)")
                print(f"🔍 Signals type: {type(signals)}, length: {len(signals) if signals else 0}")
                print(f"🔍 Historical prices type: {type(historical_prices)}")
                if historical_prices:
                    sample_ticker = list(historical_prices.keys())[0]
                    print(f"🔍 Sample price data for {sample_ticker}: {type(historical_prices[sample_ticker])}")

                # Extract exit configuration from strategy
                exit_rules = strategy_config.get('exit_rules', {})
                exit_config = {
                    'enable_stop_loss': exit_rules.get('trailing_stop_enabled', True),  # Use trailing stop as stop-loss toggle
                    'enable_take_profit': exit_rules.get('take_profit_enabled', True),
                    'enable_trailing_stop': exit_rules.get('trailing_stop_enabled', True),
                    'stop_loss_pct': exit_rules.get('trailing_stop_pct', 0.10),  # Default 10%
                    'take_profit_pct': exit_rules.get('take_profit_pct', 0.30),  # Default 30%
                    'trailing_stop_pct': exit_rules.get('trailing_stop_pct', 0.15)  # Default 15%
                }
                print(f"🛑 Exit config: Stop-Loss={exit_config['stop_loss_pct']*100:.0f}% | Take-Profit={exit_config['take_profit_pct']*100:.0f}% | Trailing-Stop={exit_config['trailing_stop_pct']*100:.0f}%")

                # Extract rebalancing configuration from strategy
                risk_management = strategy_config.get('risk_management') or {}
                heartbeat = strategy_config.get('heartbeat') or {}
                rebalance_frequency = heartbeat.get('rebalance_frequency') or risk_management.get('rebalancing_frequency', 'monthly')
                rebalance_config = {
                    'frequency': rebalance_frequency,
                    'drift_threshold': risk_management.get('drift_threshold', 0.05),  # 5% drift threshold
                    'target_weight': 0.05,  # Fixed 5% per SRS
                    'min_positions': strategy_config.get('min_positions', 5),
                    'max_positions': strategy_config.get('max_positions', 20)
                }
                print(f"⚖️ Rebalance config: Frequency={rebalance_config['frequency'].upper()} | Drift={rebalance_config['drift_threshold']*100:.0f}%")

                # Choose engine based on engine_type
                if engine_type == 'backtrader' and BACKTRADER_AVAILABLE:
                    print("🔧 Using Backtrader Engine")
                    
                    # Create a progress callback wrapper for Backtrader
                    async def bt_progress_callback(progress_data: Dict):
                        """Forward Backtrader progress to the main progress callback."""
                        if progress_callback:
                            # Extract relevant data from Backtrader's progress
                            stage = progress_data.get('stage', 'processing')
                            message = progress_data.get('message', 'Processing...')
                            percent = progress_data.get('percent', 50)
                            eta_seconds = progress_data.get('eta_seconds')
                            eta_message = progress_data.get('eta_message')
                            
                            # Create friendly message with ETA if available
                            full_message = message
                            if eta_message:
                                full_message = f"{message}\n{eta_message}"
                            
                            # Include extra details for frontend
                            details = [full_message]
                            if progress_data.get('current_ticker'):
                                details.append(f"📈 Currently fetching: {progress_data['current_ticker']}")
                            if progress_data.get('failed'):
                                details.append(f"⚠️ {progress_data['failed']} tickers skipped (data unavailable)")
                            
                            try:
                                progress_callback({
                                    'percent': percent,
                                    'message': message,
                                    'stage': stage,
                                    'eta_seconds': eta_seconds,
                                    'eta_message': eta_message,
                                    'details': details,
                                    'processed': progress_data.get('processed', 0),
                                    'total': progress_data.get('total', len(tickers)),
                                    'completed': progress_data.get('completed', 0),
                                    'failed': progress_data.get('failed', 0),
                                    'current_ticker': progress_data.get('current_ticker'),
                                    'failed_tickers': progress_data.get('failed_tickers', []),
                                })
                            except Exception as e:
                                print(f"⚠️ Progress callback error: {e}")
                    
                    bt_engine = get_backtrader_engine(
                        initial_capital=strategy_config.get('initial_capital', 100000),
                        benchmark_ticker=strategy_config.get('benchmark', 'SPY'),
                        commission=0.001,
                        slippage=0.0025,
                        progress_callback=bt_progress_callback,
                    )
                    raw_results = await bt_engine.run_backtest(
                        signals=signals,
                        start_date=start_date,
                        end_date=end_date,
                        strategy_config=strategy_config,
                        price_data=historical_prices,
                        progress_callback=bt_progress_callback,
                    )
                    
                    # Backtrader engine now returns comprehensive results directly
                    # Just pass through with minor additions
                    results = raw_results.copy()
                    results['sec_filings_fetched'] = len(signals)
                    results['api_calls_made'] = len(tickers) + 1  # tickers + benchmark
                    
                    # Ensure monthly_returns and yearly_returns are present
                    if 'monthly_returns' not in results:
                        results['monthly_returns'] = []
                    if 'yearly_returns' not in results:
                        results['yearly_returns'] = []
                else:
                    # Use custom HistoricalBacktestEngine (default)
                    if engine_type == 'backtrader' and not BACKTRADER_AVAILABLE:
                        print("⚠️ Backtrader not available, falling back to custom engine")
                    
                    print("🔧 Using Custom Historical Backtest Engine")
                    engine = HistoricalBacktestEngine(
                        initial_capital=strategy_config.get('initial_capital', 100000),
                        exit_config=exit_config,
                        rebalance_config=rebalance_config
                    )
                    raw_results = engine.run_backtest(signals, historical_prices, start_date, end_date)
                    
                    # Wrap metrics under 'summary' key for API schema compatibility
                    results = {
                        'engine': 'custom',
                        'summary': {k: v for k, v in raw_results.items() if k not in ['portfolio_history', 'dates', 'trades', 'initial_capital', 'final_value', 'total_trades']},
                        'equity_curve': {
                            'dates': raw_results.get('dates', []),
                            'portfolio_values': raw_results.get('portfolio_history', []),
                            'benchmark_values': []  # Benchmark not implemented yet
                        },
                        'trades': raw_results.get('trades', []),
                        'initial_capital': raw_results.get('initial_capital', 100000),
                        'final_value': raw_results.get('final_value', 100000),
                        'execution_time_seconds': 0,  # Will be calculated by API
                        'api_calls_made': len(tickers) * 2,  # Rough estimate
                        'sec_filings_fetched': len(signals),
                        'stocks_analyzed': tickers
                    }
            
            update_progress("Backtest complete!", 100)
            
            # Step 5: Add additional context
            results['signals'] = signals
            results['tickers'] = tickers
            results['institutions'] = selected_institutions
            results['start_date'] = start_date
            results['end_date'] = end_date

            # Debug: Log what we're returning
            print(f"🔍 Orchestrator returning results:")
            print(f"   sec_filings_fetched: {results.get('sec_filings_fetched', 'MISSING')}")
            print(f"   signals count: {len(signals)}")
            print(f"   results keys: {list(results.keys())}")
            
            return results
            
        except Exception as e:
            print(f"❌ Backtest error: {e}")
            import traceback
            traceback.print_exc()
            # Even on error, preserve the signal count so user knows signals were found
            return {
                'error': str(e),
                'total_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'sec_filings_fetched': len(signals),  # Preserve signal count
                'stocks_analyzed': tickers,
                'signals': signals  # Include the signals themselves
            }
    
    async def fetch_sec_signals(
        self,
        start_date: str,
        end_date: str,
        selected_institutions: List[str],
        strategy_config: Dict
    ) -> List[Dict]:
        """
        Fetch SEC filing-based trading signals from PostgreSQL database
        
        Signal generation logic:
        - Doubling Down: Institution increases position by 50%+
        - New Position: Institution enters a new position (top holdings)
        """
        from app.services.strategy_db import SessionLocal
        from sqlalchemy import text
        
        if not selected_institutions:
            print("⚠️  No institutions selected, returning empty signals")
            print(f"❌ ERROR: selected_institutions is empty or None: {selected_institutions}")
            return []

        if not isinstance(selected_institutions, list):
            print(f"❌ ERROR: selected_institutions is not a list: {type(selected_institutions)}")
            return []

        # Validate institution format (should be CIK strings)
        invalid_institutions = [inst for inst in selected_institutions if not isinstance(inst, str) or not inst.strip()]
        if invalid_institutions:
            print(f"⚠️  WARNING: Found invalid institution identifiers: {invalid_institutions}")

        valid_institutions = [inst.strip() for inst in selected_institutions if isinstance(inst, str) and inst.strip()]
        if len(valid_institutions) != len(selected_institutions):
            print(f"⚠️  Filtered institutions: {len(selected_institutions)} -> {len(valid_institutions)}")
            selected_institutions = valid_institutions
        
        # Normalize CIKs: Remove leading zeros to match database format
        # Frontend sends '0001037389', database has '1037389'
        normalized_ciks = [cik.lstrip('0') or '0' for cik in selected_institutions]
        print(f"🔍 Normalized CIKs: {selected_institutions} -> {normalized_ciks}")
        selected_institutions = normalized_ciks
        
        signals = []
        db = SessionLocal()
        
        try:
            print(f"\n🔍 Fetching SEC signals from database...")
            print(f"   Institutions: {selected_institutions[:3]}... ({len(selected_institutions)} total)")
            print(f"   Date range: {start_date} to {end_date}")
            
            # Query holdings from database for selected institutions
            # Using ticker if available, otherwise CUSIP
            # Build dynamic IN clause for CIKs
            cik_placeholders = ', '.join([f":cik_{i}" for i in range(len(selected_institutions))])
            query_str = f"""
                SELECT 
                    COALESCE(NULLIF(h.ticker, ''), h.cusip) as ticker,
                    h.cusip,
                    i.cik,
                    f.filing_date as filing_date,
                    h.value as market_value,
                    h.shares_or_prn_amt as shares_held,
                    h.name_of_issuer
                FROM holdings h
                JOIN filings f ON h.filing_id = f.id
                JOIN institutions i ON f.institution_id = i.id
                WHERE i.cik IN ({cik_placeholders})
                    AND f.filing_date >= :start_date
                    AND f.filing_date <= :end_date
                    AND h.cusip IS NOT NULL
                    AND h.cusip != ''
                ORDER BY f.filing_date, h.value DESC
                LIMIT 50000
            """
            query = text(query_str)
            
            # Build parameters dict with individual CIK placeholders
            params = {
                "start_date": start_date,
                "end_date": end_date
            }
            for i, cik in enumerate(selected_institutions):
                params[f"cik_{i}"] = cik
            
            print(f"🔍 DEBUG: Executing database query with params:")
            print(f"   ciks: {selected_institutions}")
            print(f"   start_date: {start_date}")
            print(f"   end_date: {end_date}")
            
            result = db.execute(query, params)
            
            rows = result.fetchall()
            print(f"🔍 DEBUG: Database query returned {len(rows)} rows")

            if len(rows) == 0:
                print("⚠️  WARNING: No holdings data found in database!")
                print("   Possible issues:")
                print("   - SEC data not loaded into database")
                print("   - Date range too narrow")
                print("   - Institution CIKs not matching database records")
                return []

            # Group holdings by ticker and cik to detect position changes
            holdings_by_position = {}

            try:
                print(f"🔍 Processing {len(rows)} rows into position groups...")
                print(f"🔍 Result type: {type(result)}")
                print(f"🔍 First row type: {type(rows[0]) if rows else 'No rows'}")

                if rows:
                    first_row = rows[0]
                    print(f"🔍 First row sample: {first_row}")
                    print(f"🔍 Row has keys method: {hasattr(first_row, 'keys')}")

                for i, row in enumerate(rows):
                    try:
                        # Handle both tuple and Row objects
                        if hasattr(row, 'keys'):
                            # SQLAlchemy Row object
                            ticker = row.ticker
                            cik = row.cik
                            filing_date = row.filing_date
                            shares_held = row.shares_held
                            market_value = row.market_value
                            name = getattr(row, 'name_of_issuer', None)
                        else:
                            # Tuple format: (ticker, cusip, cik, filing_date, market_value, shares_held, name_of_issuer)
                            ticker = row[0]  # ticker (CUSIP)
                            cik = row[2]     # cik
                            filing_date = row[3]  # filing_date
                            market_value = row[4] # market_value
                            shares_held = row[5]  # shares_held
                            name = row[6] if len(row) > 6 else None

                        key = (ticker, cik)
                        if key not in holdings_by_position:
                            holdings_by_position[key] = []

                        holdings_by_position[key].append({
                            'date': filing_date.strftime('%Y-%m-%d') if hasattr(filing_date, 'strftime') else str(filing_date),
                            'ticker': ticker,
                            'cik': cik,
                            'shares': float(shares_held or 0),
                            'value': float(market_value or 0),
                            'name': name
                        })

                        if i < 3:
                            print(f"🔍 Processed row {i+1}: {key} - {shares_held} shares on {filing_date}")

                    except Exception as e:
                        print(f"❌ Error processing row {i}: {e}")
                        print(f"❌ Row data: {row}")
                        break

            except Exception as e:
                print(f"❌ Error in row processing loop: {e}")
                import traceback
                traceback.print_exc()

            print(f"🔍 Created {len(holdings_by_position)} position groups")
            
            # Analyze position changes to generate signals
            print(f"🔍 Analyzing {len(holdings_by_position)} position groups for signals...")

            signals_generated = 0
            total_positions_checked = 0

            for (cusip, cik), holdings in holdings_by_position.items():
                holdings = sorted(holdings, key=lambda x: x['date'])
                total_positions_checked += 1

                # Debug: show first few positions
                if total_positions_checked <= 3:
                    print(f"🔍 Position {total_positions_checked}: {cusip} (CIK: {cik}) - {len(holdings)} filings")
                    for i, h in enumerate(holdings[:2]):
                        print(f"   Filing {i+1}: {h['date']} - {h['shares']} shares, ${h['value']:,.0f} value")

                # Skip if no holdings data
                if not holdings:
                    continue

                # Check if shares are positive
                positive_shares = [h for h in holdings if h['shares'] > 0]
                if not positive_shares:
                    if total_positions_checked <= 3:
                        print(f"   ⚠️  No positive share holdings for {cusip}")
                    continue
                
                # Get company name from any holding record
                company_name = next((h.get('name') for h in holdings if h.get('name')), None)
                
                for i in range(len(holdings)):
                    current = holdings[i]
                    
                    if i == 0:
                        # First filing - new position
                        if current['shares'] > 0:
                            signals.append({
                                'date': current['date'],
                                'ticker': cusip,  # Will be mapped to ticker later
                                'cusip': cusip,
                                'name': company_name,  # Include company name for ticker inference
                                'action': 'BUY',
                                'signal_type': 'NEW_POSITION',
                                'signal_strength': 1.0,
                                'institution_cik': cik,
                                'shares_change': int(current['shares'])
                            })
                            signals_generated += 1
                            print(f"✅ Generated NEW_POSITION signal for {cusip} ({company_name}) - shares: {current['shares']}")
                        else:
                            if total_positions_checked <= 3:
                                print(f"   ⚠️  Skipping NEW_POSITION for {cusip} - shares: {current['shares']} (not > 0)")
                    else:
                        previous = holdings[i-1]
                        
                        if previous['shares'] > 0:
                            change_pct = (current['shares'] - previous['shares']) / previous['shares']
                            
                            # Doubling down - increased position by 50%+
                            if change_pct >= 0.5:
                                signals.append({
                                    'date': current['date'],
                                    'ticker': cusip,  # Will be mapped to ticker later
                                    'cusip': cusip,
                                    'name': company_name,  # Include company name for ticker inference
                                    'action': 'BUY',
                                    'signal_type': 'DOUBLING_DOWN',
                                    'signal_strength': min(change_pct, 1.0),
                                    'institution_cik': cik,
                                    'shares_change': int(current['shares'] - previous['shares'])
                                })
                                signals_generated += 1
                                print(f"✅ Generated DOUBLING_DOWN signal for {cusip} ({company_name}) - {change_pct:.1%}")
                            # Reducing - decreased position by 50%+
                            elif change_pct <= -0.5:
                                signals.append({
                                    'date': current['date'],
                                    'ticker': cusip,  # Will be mapped to ticker later
                                    'cusip': cusip,
                                    'name': company_name,  # Include company name for ticker inference
                                    'action': 'SELL',
                                    'signal_type': 'REDUCING',
                                    'signal_strength': min(abs(change_pct), 1.0),
                                    'institution_cik': cik,
                                    'shares_change': int(current['shares'] - previous['shares'])
                                })
                                signals_generated += 1
                                print(f"✅ Generated REDUCING signal for {cusip} ({company_name}) - {change_pct:.1%}")
                            else:
                                if total_positions_checked <= 3:
                                    print(f"   ⏭️  Change {change_pct:.1%} for {cusip} - not significant enough")
                        else:
                            if total_positions_checked <= 3:
                                print(f"   ⚠️  Previous shares for {cusip}: {previous['shares']} (not > 0)")

                # Allow processing all positions for full backtest
            
            print(f"✅ Found {len(signals)} trading signals from {len(holdings_by_position)} positions")

            # Log signal breakdown
            signal_types = {}
            for signal in signals:
                sig_type = signal.get('signal_type', 'UNKNOWN')
                signal_types[sig_type] = signal_types.get(sig_type, 0) + 1

            print(f"📊 Signal breakdown: {signal_types}")

            if len(signals) == 0:
                print("❌ ERROR: No signals generated!")
                print(f"   Holdings by position keys: {list(holdings_by_position.keys())[:5]}")
                if holdings_by_position:
                    sample_key = list(holdings_by_position.keys())[0]
                    print(f"   Sample holdings for {sample_key}: {holdings_by_position[sample_key]}")
            
        except Exception as e:
            print(f"❌ Error fetching SEC signals: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()
        
        return signals
    
    async def fetch_historical_prices_batch(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical prices for multiple tickers with PARALLEL processing
        Uses semaphore to respect AlphaVantage rate limit (5 calls/min)
        
        Improvements:
        - Parallel fetching (5 stocks at once)
        - Much faster than sequential
        - Respects API rate limits
        """
        
        from .historical_backtest_engine import HistoricalBacktestEngine
        import asyncio
        
        engine = HistoricalBacktestEngine()
        historical_prices = {}
        
        # Rate limit: AlphaVantage free tier = 1 request/second, 25/day
        # Use semaphore of 1 to serialize requests
        semaphore = asyncio.Semaphore(1)
        
        async def fetch_one_ticker(ticker, idx):
            """Fetch a single ticker with semaphore and rate limiting"""
            async with semaphore:
                try:
                    # Wait 1.5 seconds between requests to avoid rate limits
                    if idx > 0:
                        await asyncio.sleep(1.5)
                    
                    df = await engine.fetch_historical_prices(ticker, start_date, end_date)
                    if not df.empty:
                        historical_prices[ticker] = df
                        print(f"   ✅ {ticker}: {len(df)} days")
                        
                        if progress_callback:
                            progress_callback(
                                ticker, 
                                idx, 
                                len(tickers),
                                success=True
                            )
                    else:
                        print(f"   ⚠️  {ticker}: No data returned")
                        if progress_callback:
                            progress_callback(
                                ticker, 
                                idx, 
                                len(tickers),
                                success=True
                            )
                    
                    # Rate limiting: Wait 12 seconds between each fetch (5 calls/min)
                    await asyncio.sleep(12)
                    
                except Exception as e:
                    error_msg = str(e)[:100]
                    print(f"   ❌ {ticker}: {error_msg}")
                    
                    # Check if it's an API key error
                    if 'API' in error_msg.upper() or 'KEY' in error_msg.upper() or '401' in error_msg or '403' in error_msg:
                        print(f"   ⚠️  ALPHAVANTAGE_API_KEY may be invalid or missing!")
                    
                    if progress_callback:
                        progress_callback(
                            ticker, 
                            idx, 
                            len(tickers),
                            success=False
                        )
        
        # Fetch all tickers in parallel (but limited by semaphore)
        tasks = [fetch_one_ticker(ticker, idx) for idx, ticker in enumerate(tickers, 1)]
        await asyncio.gather(*tasks)
        
        print(f"✅ Fetched prices for {len(historical_prices)}/{len(tickers)} stocks")
        return historical_prices

