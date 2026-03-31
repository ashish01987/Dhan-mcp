"""
Trading Analytics Module
Provides technical analysis indicators, Greeks calculation, and risk management functions
for intraday trading workflows.
"""

import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import fsolve


# ============================================================================
# TECHNICAL ANALYSIS FUNCTIONS
# ============================================================================

def calculate_sma(prices: List[float], period: int) -> Dict:
    """Calculate Simple Moving Average"""
    if len(prices) < period:
        return {"error": f"Need at least {period} prices, got {len(prices)}"}

    prices_array = np.array(prices)
    sma = np.mean(prices_array[-period:])

    return {
        "sma": round(float(sma), 2),
        "period": period,
        "current_price": round(float(prices[-1]), 2),
        "distance_from_sma": round(float(prices[-1] - sma), 2),
        "distance_percent": round(float((prices[-1] - sma) / sma * 100), 2)
    }


def calculate_ema(prices: List[float], period: int) -> Dict:
    """Calculate Exponential Moving Average"""
    if len(prices) < period:
        return {"error": f"Need at least {period} prices, got {len(prices)}"}

    prices_array = np.array(prices, dtype=float)
    multiplier = 2 / (period + 1)

    # Initialize EMA with SMA
    ema = np.mean(prices_array[:period])

    # Calculate EMA for remaining prices
    for price in prices_array[period:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))

    return {
        "ema": round(float(ema), 2),
        "period": period,
        "current_price": round(float(prices[-1]), 2),
        "distance_from_ema": round(float(prices[-1] - ema), 2),
        "distance_percent": round(float((prices[-1] - ema) / ema * 100), 2)
    }


def calculate_rsi(prices: List[float], period: int = 14) -> Dict:
    """Calculate Relative Strength Index (RSI)"""
    if len(prices) < period + 1:
        return {"error": f"Need at least {period + 1} prices for RSI, got {len(prices)}"}

    prices_array = np.array(prices, dtype=float)
    deltas = np.diff(prices_array)

    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])

    if avg_loss == 0:
        rsi = 100 if avg_gain > 0 else 50
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    # Signal: overbought >70, oversold <30
    signal = "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral"

    return {
        "rsi": round(float(rsi), 2),
        "period": period,
        "signal": signal,
        "current_price": round(float(prices[-1]), 2)
    }


def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
    """Calculate MACD (Moving Average Convergence Divergence)"""
    if len(prices) < slow + signal:
        return {"error": f"Need at least {slow + signal} prices for MACD, got {len(prices)}"}

    prices_array = np.array(prices, dtype=float)

    # Calculate EMAs
    ema_fast = prices_array.copy()
    ema_slow = prices_array.copy()

    fast_mult = 2 / (fast + 1)
    slow_mult = 2 / (slow + 1)

    for i in range(1, len(prices_array)):
        ema_fast[i] = (prices_array[i] * fast_mult) + (ema_fast[i-1] * (1 - fast_mult))
        ema_slow[i] = (prices_array[i] * slow_mult) + (ema_slow[i-1] * (1 - slow_mult))

    # MACD line
    macd_line = ema_fast - ema_slow

    # Signal line
    signal_line = np.zeros_like(macd_line)
    signal_mult = 2 / (signal + 1)
    signal_line[slow-1] = np.mean(macd_line[:slow])
    for i in range(slow, len(macd_line)):
        signal_line[i] = (macd_line[i] * signal_mult) + (signal_line[i-1] * (1 - signal_mult))

    # Histogram
    histogram = macd_line - signal_line

    # Signal: bullish if MACD > signal, bearish if MACD < signal
    signal_text = "bullish" if macd_line[-1] > signal_line[-1] else "bearish"

    return {
        "macd": round(float(macd_line[-1]), 4),
        "signal_line": round(float(signal_line[-1]), 4),
        "histogram": round(float(histogram[-1]), 4),
        "signal": signal_text,
        "current_price": round(float(prices[-1]), 2)
    }


def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2) -> Dict:
    """Calculate Bollinger Bands"""
    if len(prices) < period:
        return {"error": f"Need at least {period} prices, got {len(prices)}"}

    prices_array = np.array(prices, dtype=float)
    sma = np.mean(prices_array[-period:])
    std = np.std(prices_array[-period:])

    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)

    current_price = float(prices[-1])
    position = "above" if current_price > upper_band else "below" if current_price < lower_band else "middle"

    return {
        "upper_band": round(float(upper_band), 2),
        "middle_band": round(float(sma), 2),
        "lower_band": round(float(lower_band), 2),
        "current_price": round(current_price, 2),
        "position": position,
        "width_percent": round(float((upper_band - lower_band) / sma * 100), 2)
    }


def calculate_atr(high: List[float], low: List[float], close: List[float], period: int = 14) -> Dict:
    """Calculate Average True Range (ATR) for volatility"""
    if len(high) < period or len(low) < period or len(close) < period:
        return {"error": f"Need at least {period} OHLC values"}

    high_array = np.array(high, dtype=float)
    low_array = np.array(low, dtype=float)
    close_array = np.array(close, dtype=float)

    # True Range
    tr1 = high_array - low_array
    tr2 = np.abs(high_array - np.append(close_array[0], close_array[:-1]))
    tr3 = np.abs(low_array - np.append(close_array[0], close_array[:-1]))

    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    atr = np.mean(tr[-period:])

    return {
        "atr": round(float(atr), 2),
        "atr_percent": round(float(atr / close_array[-1] * 100), 2),
        "period": period,
        "current_price": round(float(close_array[-1]), 2)
    }


def calculate_support_resistance(prices: List[float], period: int = 20) -> Dict:
    """Calculate support and resistance levels"""
    if len(prices) < period:
        return {"error": f"Need at least {period} prices, got {len(prices)}"}

    prices_array = np.array(prices[-period:], dtype=float)

    support = float(np.min(prices_array))
    resistance = float(np.max(prices_array))
    current_price = float(prices[-1])

    return {
        "support": round(support, 2),
        "resistance": round(resistance, 2),
        "current_price": round(current_price, 2),
        "distance_to_support": round(current_price - support, 2),
        "distance_to_resistance": round(resistance - current_price, 2),
        "support_percent": round((current_price - support) / support * 100, 2),
        "resistance_percent": round((resistance - current_price) / resistance * 100, 2)
    }


# ============================================================================
# BLACK-SCHOLES GREEKS CALCULATION
# ============================================================================

def _d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> Tuple[float, float]:
    """Calculate d1 and d2 for Black-Scholes"""
    if T <= 0 or sigma <= 0:
        return 0, 0

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


def calculate_call_option_greek(S: float, K: float, T: float, r: float, sigma: float, greek_type: str = "delta") -> float:
    """
    Calculate Call Option Greeks using Black-Scholes
    S: Spot price
    K: Strike price
    T: Time to expiry (years)
    r: Risk-free rate
    sigma: Volatility (annualized)
    """
    d1, d2 = _d1_d2(S, K, T, r, sigma)

    if greek_type == "delta":
        return float(norm.cdf(d1))
    elif greek_type == "gamma":
        return float(norm.pdf(d1) / (S * sigma * math.sqrt(T)))
    elif greek_type == "theta":
        # Per day
        return float((-(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm.cdf(d2)) / 365)
    elif greek_type == "vega":
        # Per 1% change in volatility
        return float(S * norm.pdf(d1) * math.sqrt(T) / 100)
    elif greek_type == "rho":
        # Per 1% change in rate
        return float(K * T * math.exp(-r * T) * norm.cdf(d2) / 100)
    return 0


def calculate_put_option_greek(S: float, K: float, T: float, r: float, sigma: float, greek_type: str = "delta") -> float:
    """Calculate Put Option Greeks using Black-Scholes"""
    d1, d2 = _d1_d2(S, K, T, r, sigma)

    if greek_type == "delta":
        return float(norm.cdf(d1) - 1)
    elif greek_type == "gamma":
        return float(norm.pdf(d1) / (S * sigma * math.sqrt(T)))
    elif greek_type == "theta":
        # Per day
        return float((-(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm.cdf(-d2)) / 365)
    elif greek_type == "vega":
        # Per 1% change in volatility
        return float(S * norm.pdf(d1) * math.sqrt(T) / 100)
    elif greek_type == "rho":
        # Per 1% change in rate
        return float(-K * T * math.exp(-r * T) * norm.cdf(-d2) / 100)
    return 0


# ============================================================================
# RISK MANAGEMENT FUNCTIONS
# ============================================================================

def calculate_position_size(account_size: float, risk_pct: float, entry: float, stop_loss: float) -> Dict:
    """Calculate position size based on risk management (fixed risk method)"""
    if entry <= 0 or stop_loss <= 0 or risk_pct <= 0:
        return {"error": "Invalid parameters"}

    risk_amount = account_size * (risk_pct / 100)
    risk_per_share = abs(entry - stop_loss)

    if risk_per_share == 0:
        return {"error": "Entry and stop loss cannot be same"}

    position_size = int(risk_amount / risk_per_share)

    return {
        "position_size": position_size,
        "risk_amount": round(risk_amount, 2),
        "risk_per_share": round(risk_per_share, 2),
        "account_size": account_size,
        "risk_percent": risk_pct
    }


def calculate_risk_reward(entry: float, stop_loss: float, target: float) -> Dict:
    """Calculate Risk:Reward ratio"""
    if entry <= 0 or stop_loss <= 0 or target <= 0:
        return {"error": "Invalid parameters"}

    risk = abs(entry - stop_loss)
    reward = abs(target - entry)

    if risk == 0:
        return {"error": "Risk is zero"}

    ratio = reward / risk

    return {
        "risk": round(risk, 2),
        "reward": round(reward, 2),
        "ratio": round(ratio, 2),
        "entry": entry,
        "stop_loss": stop_loss,
        "target": target
    }


def calculate_max_drawdown(prices: List[float]) -> Dict:
    """Calculate maximum drawdown percentage"""
    if len(prices) < 2:
        return {"error": "Need at least 2 prices"}

    prices_array = np.array(prices, dtype=float)
    cummax = np.maximum.accumulate(prices_array)
    drawdown = (prices_array - cummax) / cummax
    max_dd = np.min(drawdown)

    return {
        "max_drawdown_percent": round(float(max_dd * 100), 2),
        "current_price": round(float(prices[-1]), 2)
    }


def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.05) -> Dict:
    """Calculate Sharpe Ratio"""
    if len(returns) < 2:
        return {"error": "Need at least 2 returns"}

    returns_array = np.array(returns, dtype=float)
    avg_return = np.mean(returns_array)
    std_return = np.std(returns_array)

    if std_return == 0:
        return {"error": "Zero standard deviation"}

    daily_rf = risk_free_rate / 365
    sharpe = (avg_return - daily_rf) / std_return * math.sqrt(252)  # Annualized

    return {
        "sharpe_ratio": round(float(sharpe), 2),
        "average_return": round(float(avg_return), 4),
        "volatility": round(float(std_return), 4)
    }


def calculate_win_rate(trades: List[Dict]) -> Dict:
    """Calculate win rate and trade statistics"""
    if not trades:
        return {"error": "No trades provided"}

    winning_trades = [t for t in trades if t.get("pnl", 0) > 0]
    losing_trades = [t for t in trades if t.get("pnl", 0) < 0]

    total_trades = len(trades)
    win_count = len(winning_trades)
    loss_count = len(losing_trades)

    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

    total_win = sum(t.get("pnl", 0) for t in winning_trades)
    total_loss = abs(sum(t.get("pnl", 0) for t in losing_trades))

    return {
        "total_trades": total_trades,
        "winning_trades": win_count,
        "losing_trades": loss_count,
        "win_rate_percent": round(win_rate, 2),
        "total_profit": round(total_win, 2),
        "total_loss": round(total_loss, 2),
        "net_pnl": round(total_win - total_loss, 2)
    }


def calculate_profit_factor(trades: List[Dict]) -> Dict:
    """Calculate Profit Factor"""
    if not trades:
        return {"error": "No trades provided"}

    winning_trades = [t for t in trades if t.get("pnl", 0) > 0]
    losing_trades = [t for t in trades if t.get("pnl", 0) < 0]

    total_win = sum(t.get("pnl", 0) for t in winning_trades)
    total_loss = abs(sum(t.get("pnl", 0) for t in losing_trades))

    if total_loss == 0:
        profit_factor = float('inf') if total_win > 0 else 0
    else:
        profit_factor = total_win / total_loss

    return {
        "profit_factor": round(profit_factor, 2),
        "total_profit": round(total_win, 2),
        "total_loss": round(total_loss, 2),
        "interpretation": "Good" if profit_factor > 2 else "Acceptable" if profit_factor > 1.5 else "Poor"
    }
