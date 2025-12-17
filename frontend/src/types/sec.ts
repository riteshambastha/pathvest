/**
 * SEC Data TypeScript Interfaces
 */

export interface Institution {
  id: number
  cik: string
  name: string
  description?: string
  is_popular: boolean
  created_at: string
  updated_at: string
}

export interface Filing {
  id: number
  accessionNo: string
  cik: string
  companyName: string
  formType: string
  filedAt: string
  periodOfReport?: string
  linkToTxt?: string
  linkToHtml?: string
  linkToFilingDetails?: string
  totalHoldings?: number
  totalValue?: number
}

export interface Holding {
  id: number
  nameOfIssuer: string
  cusip: string
  ticker?: string
  value: number // in thousands
  valueUsd: number // actual dollar value
  sharesOrPrnAmt?: number
  sharesOrPrnAmtType?: string
  percentage: number
}

export interface FilingSearchParams {
  cik?: string
  formType?: string
  fromDate?: string
  toDate?: string
  size?: number
  forceRefresh?: boolean
}

export interface FilingSearchResponse {
  total: number
  filings: Filing[]
  cached: boolean
}

export interface FilingHoldingsResponse {
  filing_id: number
  accession_no: string
  total_holdings: number
  total_value: number
  holdings: Holding[]
}
