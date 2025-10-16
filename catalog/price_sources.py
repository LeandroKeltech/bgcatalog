from __future__ import annotations
import re
import time
import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ---------- Types & Helpers ----------

@dataclass
class Offer:
    source: str
    source_url: str
    store_name: str
    store_url: str
    price_eur: Optional[float]
    price_original: float
    currency_original: str
    stock_status: str           # "in_stock" | "preorder" | "backorder" | "oos" | "unknown"
    last_updated: str
    shipping_to_ie: Optional[bool]  # None if unknown
    game_name: Optional[str] = None      # Nome da edição específica encontrada
    game_year: Optional[int] = None      # Ano da edição específica
    notes: Optional[str] = None          # reason codes, edition info, etc.

    def rank_tuple(self) -> Tuple[int, float]:
        # Lower is better: in_stock=0, preorder=1, backorder=2, unknown=3, oos=4
        order = {"in_stock": 0, "preorder": 1, "backorder": 2, "unknown": 3, "oos": 4}
        stock_rank = order.get(self.stock_status, 3)
        price = self.price_eur if self.price_eur is not None else float('inf')
        return stock_rank, price


class FXRates:
    """Inject real rates here (ECB, fixer.io, etc). Fallback to sane defaults."""
    def __init__(self, base="EUR", rates: Optional[Dict[str, float]] = None):
        self.base = base
        # Example defaults; replace with live values daily.
        self.rates = rates or {
            "EUR": 1.0,
            "GBP": 0.86,   # 1 EUR ≈ 0.86 GBP  -> 1 GBP ≈ 1/0.86 ≈ 1.1628 EUR
            "USD": 1.08,
            "DKK": 7.46,
            "SEK": 11.5,
        }

    def to_eur(self, amount: float, currency: str) -> Optional[float]:
        c = currency.upper()
        if c == "EUR": 
            return float(amount)
        if c in self.rates and self.rates[c] > 0:
            # amount_in_eur = amount / (units currency per EUR)
            # if rates dict is "per EUR", then EUR = 1, GBP ~ 0.86
            return round(float(amount) / float(self.rates[c]), 2)
        return None


def _session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=2,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.headers.update({
        "User-Agent": "PriceAggregator/1.0 (+https://yourdomain.example)",
        "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    })
    return s


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- Service ----------

class PriceSourceService:
    REGION = "IE"
    CURRENCY = "EUR"

    def __init__(self, fx: Optional[FXRates] = None, sitename: str = "https://yourdomain.example"):
        self.fx = fx or FXRates()
        self.sitename = sitename
        self.http = _session()

    # --------------- Public ---------------

    def fetch_all_prices(self, bgg_id: int, game_name: str) -> List[Offer]:
        print(f"[PriceSources] Fetching prices for BGG ID: {bgg_id}, Name: {game_name}")

        offers: List[Offer] = []

        # 1) BoardGamePrices (prefer eid path over HTML)
        try:
            o = self._fetch_boardgameprices_uk(bgg_id)
            if o: offers.extend(o)
        except Exception as e:
            print(f"[BoardGamePrices] Error: {e}")

        # 2) BoardGameOracle (keep optional; endpoint may change)
        try:
            o = self._fetch_boardgameoracle(bgg_id)
            if o: offers.extend(o)
        except Exception as e:
            print(f"[BoardGameOracle] Error: {e}")

        # 3) Retailers (optional; brittle)
        try:
            o = self._fetch_zatu(game_name)
            if o: offers.extend(o)
        except Exception as e:
            print(f"[Zatu] Error: {e}")

        try:
            o = self._fetch_magic_madhouse(game_name)
            if o: offers.extend(o)
        except Exception as e:
            print(f"[MagicMadhouse] Error: {e}")

        try:
            o = self._fetch_365games(game_name)
            if o: offers.extend(o)
        except Exception as e:
            print(f"[365Games] Error: {e}")

        try:
            o = self._fetch_philibert(game_name)
            if o: offers.extend(o)
        except Exception as e:
            print(f"[Philibert] Error: {e}")

        # Sort: by stock tier then by price
        offers.sort(key=lambda o: o.rank_tuple())

        print(f"[PriceSources] Found {len(offers)} offers total")
        return offers

    # --------------- Sources ---------------

    def _fetch_boardgameprices_uk(self, bgg_id: int) -> List[Offer]:
        """
        Use the documented endpoint:
          https://boardgameprices.co.uk/api/info?eid=<BGG_ID>&sitename=<your-site>
        Optional: currency=EUR, destination=GB/DE/US/DK/SE, locale=en, preferred_language=GB, sort=SMART
        Returns possibly multiple editions; we flatten to offers.
        """
        url = "https://boardgameprices.co.uk/api/info"
        params = {
            "eid": str(bgg_id),
            "currency": "EUR",
            "sort": "SMART",
            "locale": "en",
            "preferred_language": "GB",
            "sitename": self.sitename
        }
        # destination may filter out results if not supported; omit unless you need a specific region.
        # params["destination"] = "GB"

        r = self.http.get(url, params=params, timeout=12)
        if r.status_code != 200:
            print(f"[BoardGamePrices] HTTP {r.status_code}: {r.text[:200]}")
            return []

        data = r.json() if "application/json" in r.headers.get("Content-Type", "") else {}
        items = data.get("items") or data.get("results") or []
        if not isinstance(items, list) or not items:
            return []

        offers: List[Offer] = []
        for item in items:
            # Extrair informações da edição do item
            item_name = item.get("name") or item.get("title") or ""
            item_year = None
            
            # Tentar extrair ano do nome ou campo específico
            year_field = item.get("year") or item.get("year_published") or item.get("yearpublished")
            if year_field:
                try:
                    item_year = int(year_field)
                except (ValueError, TypeError):
                    pass
            
            # Se não encontrou ano, tentar extrair do nome (formato "Game Name (2020)")
            if item_year is None and item_name:
                import re
                year_match = re.search(r'\((\d{4})\)', item_name)
                if year_match:
                    try:
                        item_year = int(year_match.group(1))
                    except ValueError:
                        pass
            
            prices = item.get("prices") or item.get("offers") or []
            for p in prices:
                raw_price = p.get("price_value") or p.get("price") or p.get("value")
                curr = (p.get("currency") or p.get("currency_code") or "EUR").upper()
                store_name = (p.get("store") or p.get("shop") or p.get("retailer") or "").strip() or "Unknown store"
                store_url = p.get("url") or p.get("link") or p.get("shop_url") or ""
                
                # stock heuristics
                in_stock = p.get("in_stock")
                if in_stock is None:
                    s = (p.get("stock") or "").strip().upper()
                    in_stock = (s == "Y") or ("IN STOCK" in s)
                availability = p.get("availability", "")
                stock_status = "in_stock" if in_stock else (
                    "preorder" if "preorder" in str(availability).lower() else
                    "backorder" if "backorder" in str(availability).lower() else
                    "unknown"
                )

                try:
                    price_float = float(raw_price)
                except (TypeError, ValueError):
                    continue

                price_eur = self.fx.to_eur(price_float, curr)
                offers.append(Offer(
                    source="BoardGamePrices.co.uk",
                    source_url=url,
                    store_name=store_name,
                    store_url=store_url,
                    price_eur=price_eur,
                    price_original=price_float,
                    currency_original=curr,
                    stock_status=stock_status,
                    last_updated=_iso_now(),
                    shipping_to_ie=None,
                    game_name=item_name,
                    game_year=item_year,
                    notes=None
                ))
        return offers

    def _fetch_boardgameoracle(self, bgg_id: int) -> List[Offer]:
        """
        Unofficial; may change. Expect JSON with an 'offers' array.
        We filter to EU/UK countries to be relevant for IE.
        """
        url = f"https://www.boardgameoracle.com/api/game/{bgg_id}/prices"
        r = self.http.get(url, timeout=12)
        if r.status_code != 200:
            return []
        try:
            data = r.json()
        except Exception:
            return []

        offers_raw = data.get("offers") or []
        selected = [o for o in offers_raw if str(o.get("country", "")).upper() in {"UK","DE","FR","IE","NL","ES","IT","AT","BE"}]

        offers: List[Offer] = []
        for o in selected:
            curr = (o.get("currency") or "GBP").upper()
            # Some Oracle entries report GBP even when EU; be defensive
            price = o.get("price")
            try:
                price_float = float(price)
            except (TypeError, ValueError):
                continue

            price_eur = self.fx.to_eur(price_float, curr)

            availability = str(o.get("availability", "")).lower()
            if "out of stock" in availability or "sold out" in availability:
                stock = "oos"
            elif "preorder" in availability:
                stock = "preorder"
            elif "backorder" in availability:
                stock = "backorder"
            elif "in stock" in availability or availability.strip() == "":
                stock = "in_stock"
            else:
                stock = "unknown"

            # Extrair informações da edição do Oracle
            game_name = o.get("name") or o.get("title") or data.get("name") or ""
            game_year = None
            
            # Tentar extrair ano
            year_field = o.get("year") or data.get("year") or data.get("year_published")
            if year_field:
                try:
                    game_year = int(year_field)
                except (ValueError, TypeError):
                    pass
            
            # Se não encontrou ano, tentar extrair do nome
            if game_year is None and game_name:
                import re
                year_match = re.search(r'\((\d{4})\)', game_name)
                if year_match:
                    try:
                        game_year = int(year_match.group(1))
                    except ValueError:
                        pass

            offers.append(Offer(
                source="BoardGameOracle",
                source_url=f"https://www.boardgameoracle.com/game/{bgg_id}",
                store_name=o.get("store", "Unknown Store"),
                store_url=o.get("url", ""),
                price_eur=price_eur,
                price_original=price_float,
                currency_original=curr,
                stock_status=stock,
                last_updated=_iso_now(),
                shipping_to_ie=None,
                game_name=game_name,
                game_year=game_year,
                notes=o.get("notes")
            ))
        return offers

    # ---------- Retailers (scraping: optional & brittle) ----------

    def _fetch_zatu(self, game_name: str) -> List[Offer]:
        # Prefer product pages or JSON if available; search pages can be misleading.
        search_url = "https://www.board-game.co.uk/search/"
        r = self.http.get(search_url, params={"q": game_name}, timeout=10)
        if r.status_code != 200:
            return []

        # Try to pick the first product price block; avoid “from £” ranges.
        # NOTE: This is intentionally conservative.
        prices = re.findall(r'£\s?(\d+\.\d{2})', r.text)
        if not prices:
            return []

        try:
            price_gbp = float(prices[0])
        except ValueError:
            return []

        price_eur = self.fx.to_eur(price_gbp, "GBP")
        return [Offer(
            source="Zatu Games",
            source_url="https://www.board-game.co.uk/",
            store_name="Zatu Games",
            store_url=f"{search_url}?q={requests.utils.quote(game_name)}",
            price_eur=price_eur,
            price_original=price_gbp,
            currency_original="GBP",
            stock_status="unknown",
            last_updated=_iso_now(),
            shipping_to_ie=None,
            game_name=game_name,  # Nome pesquisado
            game_year=None,       # Não conseguimos extrair do scraping
            notes="search-page price; verify SKU/edition"
        )]

    def _fetch_magic_madhouse(self, game_name: str) -> List[Offer]:
        search_url = "https://www.magicmadhouse.co.uk/search"
        r = self.http.get(search_url, params={"q": game_name}, timeout=10)
        if r.status_code != 200:
            return []
        prices = re.findall(r'£\s?(\d+\.\d{2})', r.text)
        if not prices:
            return []
        try:
            price_gbp = float(prices[0])
        except ValueError:
            return []
        price_eur = self.fx.to_eur(price_gbp, "GBP")
        return [Offer(
            source="Magic Madhouse",
            source_url="https://www.magicmadhouse.co.uk/",
            store_name="Magic Madhouse",
            store_url=f"{search_url}?q={requests.utils.quote(game_name)}",
            price_eur=price_eur,
            price_original=price_gbp,
            currency_original="GBP",
            stock_status="unknown",
            last_updated=_iso_now(),
            shipping_to_ie=None,
            game_name=game_name,
            game_year=None,
            notes="search-page price; verify SKU/edition"
        )]

    def _fetch_365games(self, game_name: str) -> List[Offer]:
        search_url = "https://www.365games.co.uk/search"
        r = self.http.get(search_url, params={"q": game_name}, timeout=10)
        if r.status_code != 200:
            return []
        prices = re.findall(r'£\s?(\d+\.\d{2})', r.text)
        if not prices:
            return []
        try:
            price_gbp = float(prices[0])
        except ValueError:
            return []
        price_eur = self.fx.to_eur(price_gbp, "GBP")
        return [Offer(
            source="365Games",
            source_url="https://www.365games.co.uk/",
            store_name="365Games",
            store_url=f"{search_url}?q={requests.utils.quote(game_name)}",
            price_eur=price_eur,
            price_original=price_gbp,
            currency_original="GBP",
            stock_status="unknown",
            last_updated=_iso_now(),
            shipping_to_ie=None,
            game_name=game_name,
            game_year=None,
            notes="search-page price; verify SKU/edition"
        )]

    def _fetch_philibert(self, game_name: str) -> List[Offer]:
        search_url = "https://www.philibertnet.com/en/search"
        r = self.http.get(search_url, params={"q": game_name}, timeout=10)
        if r.status_code != 200:
            return []
        # Favor €xx.yy with two decimals
        prices = re.findall(r'€\s?(\d+\.\d{2})', r.text)
        if not prices:
            return []
        try:
            price_eur = float(prices[0])
        except ValueError:
            return []
        return [Offer(
            source="Philibert",
            source_url="https://www.philibertnet.com/",
            store_name="Philibert",
            store_url=f"{search_url}?q={requests.utils.quote(game_name)}",
            price_eur=price_eur,
            price_original=price_eur,
            currency_original="EUR",
            stock_status="unknown",
            last_updated=_iso_now(),
            shipping_to_ie=True,   # Philibert generally ships to IE; shipping fee varies.
            game_name=game_name,
            game_year=None,
            notes="search-page price; verify SKU/edition; shipping at checkout"
        )]
