#!/usr/bin/env python3
"""
SEC-API.io Connectivity Verification Script
Purpose: Verify connectivity to SEC-API.io interface (FR-3.1.B.2)
Target: Query latest 13F-HR filing for Renaissance Technologies (CIK: 0001037389)
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
SEC_API_BASE_URL = "https://api.sec-api.io"
API_KEY = os.getenv("SEC_API_KEY")

# Renaissance Technologies details
CIK = "0001037389"
CIK_NO_ZEROS = "1037389"
FORM_TYPE = "13F-HR"


def verify_api_connectivity():
    """
    Verify SEC-API.io connectivity by querying the latest 13F-HR filing
    for Renaissance Technologies.
    """
    
    # Validate API key
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        print("❌ ERROR: SEC_API_KEY not configured in .env file")
        print("Please add your API key to the .env file:")
        print("SEC_API_KEY=your_actual_api_key_here")
        sys.exit(1)
    
    print("=" * 70)
    print("SEC-API.io Connectivity Verification")
    print("=" * 70)
    print(f"Target CIK: {CIK} (Renaissance Technologies)")
    print(f"Form Type: {FORM_TYPE}")
    print(f"API Endpoint: {SEC_API_BASE_URL}")
    print("=" * 70)
    print()
    
    # Construct the query (note: CIK without leading zeros)
    query_payload = {
        "query": {
            "query_string": {
                "query": f'cik:{CIK_NO_ZEROS} AND formType:"{FORM_TYPE}"'
            }
        },
        "from": "0",
        "size": "10",
        "sort": [{"filedAt": {"order": "desc"}}]
    }
    
    # Request headers
    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        print("🔄 Sending API request...")
        
        # Make the API request
        response = requests.post(
            f"{SEC_API_BASE_URL}",
            headers=headers,
            json=query_payload,
            timeout=30
        )
        
        # Check response status
        if response.status_code != 200:
            print(f"❌ API request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            sys.exit(1)
        
        # Parse the response
        data = response.json()
        
        # Check if we got results
        if not data.get("filings") or len(data["filings"]) == 0:
            print("❌ No filings found for the specified CIK and form type")
            sys.exit(1)
        
        # Extract the latest filing
        latest_filing = data["filings"][0]
        
        # Display results
        print("✅ API Connectivity Verified Successfully!")
        print()
        print("Latest 13F-HR Filing Details:")
        print("-" * 70)
        print(f"Filing Date (filedAt): {latest_filing.get('filedAt', 'N/A')}")
        print(f"Accession Number:      {latest_filing.get('accessionNo', 'N/A')}")
        print(f"Company Name:          {latest_filing.get('companyName', 'N/A')}")
        print(f"Form Type:             {latest_filing.get('formType', 'N/A')}")
        print(f"Period of Report:      {latest_filing.get('periodOfReport', 'N/A')}")
        print("-" * 70)
        print()
        print("✅ Point-in-Time data availability confirmed!")
        print("✅ FR-3.1.B.2 requirement satisfied!")
        
        return True
        
    except requests.exceptions.Timeout:
        print("❌ Request timeout: API took too long to respond")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Unable to reach SEC-API.io")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("❌ Invalid JSON response from API")
        print(f"Response: {response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    verify_api_connectivity()

