"""
Portfolio Analyzer Module
Provides portfolio-level analysis, P&L tracking, and Greeks aggregation.
Fetches live data from API (get_holdings, get_positions) and performs calculations.
"""

import json
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from trading_analytics import (
    calculate_call_option_greek,
    calculate_put_option_greek,
    calculate_sharpe_ratio,
    calculate_win_rate
)


# ============================================================================
# PORTFOLIO ANALYTICS
# ============================================================================

def get_portfolio_metrics(holdings: List[Dict], positions: List[Dict]) -> Dict:
    """Get aggregate portfolio metrics"""
    if not holdings and not positions:
        return {"error": "No holdings or positions"}

    total_value = 0
    total_invested = 0

    # Process holdings
    holding_count = 0
    if holdings:
        holding_count = len(holdings)
        for holding in holdings:
            total_value += holding.get("value", 0)
            total_invested += holding.get("cost_price", 0) * holding.get("quantity", 0)

    # Process positions
    position_count = 0
    position_pnl = 0
    if positions:
        position_count = len(positions)
        for pos in positions:
            position_pnl += pos.get("pnl", 0)

    total_pnl = (total_value - total_invested) + position_pnl

    return {
        "total_portfolio_value": round(total_value, 2),
        "total_invested": round(total_invested, 2),
        "total_pnl": round(total_pnl, 2),
        "pnl_percent": round((total_pnl / total_invested * 100) if total_invested > 0 else 0, 2),
        "holding_count": holding_count,
        "position_count": position_count,
        "total_positions": holding_count + position_count
    }


def calculate_portfolio_pnl(holdings: List[Dict], current_prices: Dict) -> Dict:
    """
    Calculate P&L breakdown by position and sector

    Args:
        holdings: List of {security_id, symbol, quantity, cost_price, sector}
        current_prices: {security_id: current_price}
    """
    if not holdings:
        return {"error": "No holdings"}

    pnl_data = []
    sector_pnl = {}
    total_realized = 0
    total_unrealized = 0

    for holding in holdings:
        security_id = holding.get("security_id", "")
        symbol = holding.get("symbol", "")
        quantity = holding.get("quantity", 0)
        cost_price = holding.get("cost_price", 0)
        sector = holding.get("sector", "Other")

        current_price = current_prices.get(security_id, cost_price)
        pnl = (current_price - cost_price) * quantity

        pnl_data.append({
            "symbol": symbol,
            "quantity": quantity,
            "cost_price": round(cost_price, 2),
            "current_price": round(current_price, 2),
            "pnl": round(pnl, 2),
            "pnl_percent": round((pnl / (cost_price * quantity) * 100) if cost_price > 0 else 0, 2),
            "sector": sector
        })

        total_unrealized += pnl

        # Aggregate by sector
        if sector not in sector_pnl:
            sector_pnl[sector] = 0
        sector_pnl[sector] += pnl

    sector_breakdown = [
        {"sector": s, "pnl": round(p, 2)} for s, p in sorted(sector_pnl.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "position_pnl": pnl_data,
        "sector_pnl": sector_breakdown,
        "total_realized": round(total_realized, 2),
        "total_unrealized": round(total_unrealized, 2),
        "total_pnl": round(total_realized + total_unrealized, 2)
    }


def calculate_concentration_risk(holdings: List[Dict]) -> Dict:
    """Calculate position concentration risk"""
    if not holdings:
        return {"error": "No holdings"}

    total_value = sum(h.get("value", 0) for h in holdings)

    if total_value == 0:
        return {"error": "Zero portfolio value"}

    concentrations = []
    for holding in holdings:
        value = holding.get("value", 0)
        pct = (value / total_value * 100) if total_value > 0 else 0
        concentrations.append({
            "symbol": holding.get("symbol", ""),
            "value_percent": round(pct, 2)
        })

    concentrations.sort(key=lambda x: x["value_percent"], reverse=True)

    # Risk assessment
    top_3_pct = sum(c["value_percent"] for c in concentrations[:3])
    risk_level = "High" if top_3_pct > 50 else "Medium" if top_3_pct > 30 else "Low"

    return {
        "concentration_by_position": concentrations,
        "top_3_concentration": round(top_3_pct, 2),
        "risk_level": risk_level,
        "recommendation": "Reduce top positions" if risk_level == "High" else "Monitor concentration"
    }


def get_sector_allocation(holdings: List[Dict]) -> Dict:
    """Get portfolio allocation by sector"""
    if not holdings:
        return {"error": "No holdings"}

    sector_value = {}
    total_value = 0

    for holding in holdings:
        sector = holding.get("sector", "Other")
        value = holding.get("value", 0)

        if sector not in sector_value:
            sector_value[sector] = 0
        sector_value[sector] += value
        total_value += value

    allocation = [
        {
            "sector": s,
            "value": round(v, 2),
            "percent": round((v / total_value * 100) if total_value > 0 else 0, 2)
        }
        for s, v in sorted(sector_value.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "sector_allocation": allocation,
        "total_portfolio_value": round(total_value, 2),
        "sectors_count": len(allocation)
    }


def get_expiry_analysis(positions: List[Dict]) -> Dict:
    """Analyze option positions by expiry date"""
    if not positions:
        return {"error": "No positions"}

    expiry_positions = {}

    for position in positions:
        symbol = position.get("symbol", "")
        expiry = position.get("expiry_date", "Unknown")
        pnl = position.get("pnl", 0)

        if expiry not in expiry_positions:
            expiry_positions[expiry] = {"positions": [], "total_pnl": 0, "count": 0}

        expiry_positions[expiry]["positions"].append({
            "symbol": symbol,
            "pnl": round(pnl, 2)
        })
        expiry_positions[expiry]["total_pnl"] += pnl
        expiry_positions[expiry]["count"] += 1

    expiry_summary = [
        {
            "expiry": e,
            "position_count": info["count"],
            "total_pnl": round(info["total_pnl"], 2),
            "positions": info["positions"]
        }
        for e, info in sorted(expiry_positions.items())
    ]

    return {
        "expiry_analysis": expiry_summary,
        "positions_by_expiry": len(expiry_summary)
    }


def get_greeks_summary(positions: List[Dict], current_prices: Dict) -> Dict:
    """
    Aggregate portfolio Greeks exposure
    Requires positions with option metadata (strike, expiry, type, etc.)
    """
    if not positions:
        return {"error": "No positions"}

    total_delta = 0
    total_gamma = 0
    total_theta = 0
    total_vega = 0
    total_rho = 0

    option_count = 0

    # Risk-free rate (0.06 = 6% annual)
    r = 0.06
    T_base = 1  # Placeholder, ideally calculate from expiry date

    for position in positions:
        symbol = position.get("symbol", "")
        option_type = position.get("option_type", "").upper()

        # Skip non-option positions
        if option_type not in ["CE", "PE", "CALL", "PUT"]:
            continue

        try:
            S = current_prices.get(position.get("security_id", ""), position.get("entry_price", 0))
            K = position.get("strike", 0)
            T = position.get("days_to_expiry", 1) / 365.0
            sigma = position.get("volatility", 0.30)  # Default 30% if not available
            quantity = position.get("quantity", 1)

            is_call = option_type in ["CE", "CALL"]

            if is_call:
                delta = calculate_call_option_greek(S, K, T, r, sigma, "delta") * quantity
                gamma = calculate_call_option_greek(S, K, T, r, sigma, "gamma") * quantity
                theta = calculate_call_option_greek(S, K, T, r, sigma, "theta") * quantity
                vega = calculate_call_option_greek(S, K, T, r, sigma, "vega") * quantity
                rho = calculate_call_option_greek(S, K, T, r, sigma, "rho") * quantity
            else:
                delta = calculate_put_option_greek(S, K, T, r, sigma, "delta") * quantity
                gamma = calculate_put_option_greek(S, K, T, r, sigma, "gamma") * quantity
                theta = calculate_put_option_greek(S, K, T, r, sigma, "theta") * quantity
                vega = calculate_put_option_greek(S, K, T, r, sigma, "vega") * quantity
                rho = calculate_put_option_greek(S, K, T, r, sigma, "rho") * quantity

            total_delta += delta
            total_gamma += gamma
            total_theta += theta
            total_vega += vega
            total_rho += rho

            option_count += 1
        except Exception as e:
            # Skip positions with missing data
            continue

    return {
        "portfolio_greeks": {
            "delta": round(total_delta, 4),
            "gamma": round(total_gamma, 6),
            "theta": round(total_theta, 4),
            "vega": round(total_vega, 4),
            "rho": round(total_rho, 4)
        },
        "option_count": option_count,
        "delta_interpretation": "Bullish" if total_delta > 0 else "Bearish" if total_delta < 0 else "Neutral",
        "theta_interpretation": "Profitable" if total_theta > 0 else "Losing time value",
        "gamma_risk": "High" if abs(total_gamma) > 0.1 else "Moderate" if abs(total_gamma) > 0.05 else "Low"
    }


# ============================================================================
# RISK MONITORING
# ============================================================================

def check_portfolio_limits(holdings: List[Dict], positions: List[Dict], margins: Dict) -> Dict:
    """
    Check if portfolio exceeds risk limits:
    - Max concentration: 30% per position
    - Max margin usage: 75%
    - Max Greeks exposure (from greeks_summary)
    """
    warnings = []
    alerts = []

    # Check concentration
    total_value = sum(h.get("value", 0) for h in holdings)
    if total_value > 0:
        for holding in holdings:
            pct = (holding.get("value", 0) / total_value * 100)
            if pct > 30:
                warnings.append(f"Position {holding.get('symbol', '')} concentration: {pct:.1f}% (exceeds 30% limit)")
            if pct > 50:
                alerts.append(f"CRITICAL: {holding.get('symbol', '')} concentration: {pct:.1f}%")

    # Check margin
    if margins:
        margin_used = margins.get("margin_used", 0)
        margin_available = margins.get("margin_available", 0)
        total_margin = margin_used + margin_available

        if total_margin > 0:
            margin_pct = (margin_used / total_margin * 100)
            if margin_pct > 75:
                warnings.append(f"Margin usage: {margin_pct:.1f}% (exceeds 75% limit)")
            if margin_pct > 90:
                alerts.append(f"CRITICAL: Margin usage: {margin_pct:.1f}%")

    return {
        "status": "critical" if alerts else "warning" if warnings else "ok",
        "warnings": warnings,
        "alerts": alerts,
        "total_warnings": len(warnings),
        "total_alerts": len(alerts)
    }
