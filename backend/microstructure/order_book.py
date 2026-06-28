"""
Level 2 Order Book analyzer.
Analyzes Zerodha's market depth (5 levels bid/ask) for:
- Bid/ask imbalance
- Wall detection (iceberg orders / institutional orders)
- Order book pressure (who is in control)
"""

import numpy as np
from dataclasses import dataclass
from loguru import logger


@dataclass
class OrderBookAnalysis:
    bid_total: int
    ask_total: int
    imbalance_ratio: float     # bid_total / ask_total (>1 = buyers winning)
    pressure: str              # "BUY_PRESSURE", "SELL_PRESSURE", "BALANCED"
    bid_wall: float | None     # large bid order detected (support)
    ask_wall: float | None     # large ask order detected (resistance)
    best_bid: float
    best_ask: float
    spread: float
    spread_pct: float
    depth_score: float         # 0–1 liquidity score
    description: str


class OrderBookAnalyzer:

    def analyze(self, depth: dict, ltp: float) -> OrderBookAnalysis:
        """
        depth: Kite format
        {
          "buy": [{"price": x, "quantity": q, "orders": n}, ...],  # 5 levels
          "sell": [{"price": x, "quantity": q, "orders": n}, ...]
        }
        """
        bids = depth.get("buy", [])
        asks = depth.get("sell", [])

        if not bids or not asks:
            return OrderBookAnalysis(
                bid_total=0, ask_total=0, imbalance_ratio=1.0,
                pressure="BALANCED", bid_wall=None, ask_wall=None,
                best_bid=ltp, best_ask=ltp, spread=0, spread_pct=0,
                depth_score=0, description="No order book data"
            )

        # Totals
        bid_vols = [b.get("quantity", 0) for b in bids]
        ask_vols = [a.get("quantity", 0) for a in asks]
        bid_total = sum(bid_vols)
        ask_total = sum(ask_vols)

        if ask_total == 0:
            imbalance = 5.0
        else:
            imbalance = bid_total / ask_total

        # Best bid/ask
        best_bid = bids[0].get("price", ltp) if bids else ltp
        best_ask = asks[0].get("price", ltp) if asks else ltp
        spread = best_ask - best_bid
        spread_pct = (spread / ltp * 100) if ltp > 0 else 0

        # Wall detection (a single level with > 30% of total on that side)
        bid_wall = None
        for bid in bids:
            qty = bid.get("quantity", 0)
            if bid_total > 0 and qty / bid_total > 0.35:
                bid_wall = bid.get("price")
                break

        ask_wall = None
        for ask in asks:
            qty = ask.get("quantity", 0)
            if ask_total > 0 and qty / ask_total > 0.35:
                ask_wall = ask.get("price")
                break

        # Pressure classification
        if imbalance >= 1.5:
            pressure = "BUY_PRESSURE"
        elif imbalance <= 0.67:
            pressure = "SELL_PRESSURE"
        else:
            pressure = "BALANCED"

        # Depth score (liquidity = higher is better)
        depth_score = min(1.0, (bid_total + ask_total) / 10000.0)

        # Description
        parts = [
            f"Bid/Ask ratio: {imbalance:.2f} ({pressure})",
            f"Spread: ₹{spread:.2f} ({spread_pct:.3f}%)",
        ]
        if bid_wall:
            parts.append(f"Bid wall at {bid_wall:.2f} (strong support)")
        if ask_wall:
            parts.append(f"Ask wall at {ask_wall:.2f} (resistance)")

        return OrderBookAnalysis(
            bid_total=bid_total,
            ask_total=ask_total,
            imbalance_ratio=round(imbalance, 2),
            pressure=pressure,
            bid_wall=bid_wall,
            ask_wall=ask_wall,
            best_bid=best_bid,
            best_ask=best_ask,
            spread=round(spread, 2),
            spread_pct=round(spread_pct, 4),
            depth_score=round(depth_score, 2),
            description=" | ".join(parts),
        )


order_book_analyzer = OrderBookAnalyzer()
