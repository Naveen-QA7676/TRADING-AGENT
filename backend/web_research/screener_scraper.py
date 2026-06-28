"""
Screener.in scraper — fetches fundamental data, financial ratios,
and shareholding pattern for fundamental quality grading.
"""

import asyncio
import httpx
from bs4 import BeautifulSoup
from loguru import logger


class ScreenerScraper:

    def __init__(self):
        self._client = httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20.0,
            follow_redirects=True,
        )

    async def get_fundamentals(self, symbol: str) -> dict:
        """
        Fetch fundamental data from Screener.in.
        Returns: PE, EPS, ROE, ROCE, D/E, Promoter holding, Market Cap, etc.
        """
        url = f"https://www.screener.in/company/{symbol}/consolidated/"
        try:
            resp = await self._client.get(url)
            soup = BeautifulSoup(resp.text, "lxml")

            # Extract ratios from the ratios table
            ratios = {}
            ratio_section = soup.find("ul", class_="ratios")
            if ratio_section:
                for li in ratio_section.find_all("li"):
                    label = li.find("span", class_="name")
                    value = li.find("span", class_="value")
                    if label and value:
                        key = label.text.strip().lower().replace(" ", "_")
                        val = value.text.strip()
                        ratios[key] = val

            # Shareholding
            holding = {}
            holding_section = soup.find("section", id="shareholding")
            if holding_section:
                for row in holding_section.find_all("tr"):
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        category = cols[0].text.strip()
                        pct = cols[-1].text.strip()
                        holding[category] = pct

            # Quarterly results (last 4 quarters)
            quarters = []
            q_table = soup.find("section", id="quarters")
            if q_table:
                rows = q_table.find_all("tr")
                for row in rows[:5]:
                    cells = row.find_all(["th", "td"])
                    quarters.append([c.text.strip() for c in cells])

            return {
                "symbol": symbol,
                "ratios": ratios,
                "shareholding": holding,
                "quarterly_summary": quarters[:5],
                "source": f"screener.in/company/{symbol}",
            }

        except Exception as e:
            logger.error(f"Screener scrape error ({symbol}): {e}")
            return {"symbol": symbol, "ratios": {}, "shareholding": {}, "quarterly_summary": [], "source": ""}

    def grade_fundamentals(self, data: dict) -> str:
        """
        Grade company fundamentals: A+, A, B, C based on key ratios.
        """
        ratios = data.get("ratios", {})
        score = 0

        try:
            roe = float(str(ratios.get("return_on_equity", "0")).replace("%", "").replace(",", ""))
            if roe >= 20:
                score += 3
            elif roe >= 15:
                score += 2
            elif roe >= 10:
                score += 1
        except ValueError:
            pass

        try:
            pe = float(str(ratios.get("price_to_earning", "0")).replace(",", ""))
            if 5 < pe < 25:
                score += 2
            elif 25 <= pe <= 40:
                score += 1
        except ValueError:
            pass

        try:
            de = float(str(ratios.get("debt_to_equity", "99")).replace(",", ""))
            if de < 0.5:
                score += 2
            elif de < 1.5:
                score += 1
        except ValueError:
            pass

        try:
            holding = data.get("shareholding", {})
            promoter = float(str(holding.get("Promoters", "0")).replace("%", "").replace(",", ""))
            if promoter >= 50:
                score += 2
            elif promoter >= 35:
                score += 1
        except ValueError:
            pass

        if score >= 8:
            return "A+"
        elif score >= 6:
            return "A"
        elif score >= 4:
            return "B"
        else:
            return "C"

    async def close(self):
        await self._client.aclose()


screener_scraper = ScreenerScraper()
