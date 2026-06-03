"""
Economic Calendar Integration untuk News Filter.
- Fetch high-impact news dari Investing.com RSS feed
- Cache news data untuk menghindari API rate limit
- Filter trading 30 menit sebelum/sesudah high-impact news
- Support multiple currencies (USD, EUR, GBP, etc.)
"""
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import os


class NewsEvent:
    """Representasi single news event"""
    def __init__(
        self,
        title: str,
        currency: str,
        impact: str,
        event_time: datetime,
        actual: Optional[str] = None,
        forecast: Optional[str] = None,
        previous: Optional[str] = None,
    ):
        self.title = title
        self.currency = currency
        self.impact = impact  # HIGH, MEDIUM, LOW
        self.event_time = event_time
        self.actual = actual
        self.forecast = forecast
        self.previous = previous

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "currency": self.currency,
            "impact": self.impact,
            "event_time": self.event_time.isoformat(),
            "actual": self.actual,
            "forecast": self.forecast,
            "previous": self.previous,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NewsEvent":
        return cls(
            title=data["title"],
            currency=data["currency"],
            impact=data["impact"],
            event_time=datetime.fromisoformat(data["event_time"]),
            actual=data.get("actual"),
            forecast=data.get("forecast"),
            previous=data.get("previous"),
        )


class EconomicCalendar:
    """
    Economic Calendar Manager.
    Fetch news dari Investing.com RSS feed dan cache locally.
    """
    
    # RSS feeds untuk major currencies
    RSS_FEEDS = {
        "USD": "https://www.investing.com/rss/economic_calendar_USD.rss",
        "EUR": "https://www.investing.com/rss/economic_calendar_EUR.rss",
        "GBP": "https://www.investing.com/rss/economic_calendar_GBP.rss",
        "JPY": "https://www.investing.com/rss/economic_calendar_JPY.rss",
    }
    
    # High-impact keywords untuk filter
    HIGH_IMPACT_KEYWORDS = [
        "NFP", "Non-Farm", "Payrolls", "Interest Rate", "FOMC", "Fed",
        "GDP", "CPI", "Inflation", "Employment", "Unemployment",
        "Central Bank", "ECB", "BoE", "BoJ", "Powell", "Lagarde",
    ]

    def __init__(
        self,
        cache_dir: str = "db/news_cache",
        cache_duration_hours: int = 6,
        buffer_minutes: int = 30,
        currencies: List[str] = None,
    ):
        self.cache_dir = cache_dir
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.buffer_minutes = buffer_minutes
        self.currencies = currencies or ["USD", "EUR"]  # Default: USD & EUR
        
        # Cache
        self.events: List[NewsEvent] = []
        self.last_fetch: Optional[datetime] = None
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_file(self) -> str:
        """Get cache file path"""
        return os.path.join(self.cache_dir, "news_events.json")

    def _load_from_cache(self) -> bool:
        """Load events from cache file"""
        cache_file = self._get_cache_file()
        if not os.path.exists(cache_file):
            return False
        
        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
            
            # Check cache age
            last_fetch = datetime.fromisoformat(data["last_fetch"])
            if datetime.utcnow() - last_fetch > self.cache_duration:
                print("[NEWS] Cache expired")
                return False
            
            # Load events
            self.events = [NewsEvent.from_dict(e) for e in data["events"]]
            self.last_fetch = last_fetch
            print(f"[NEWS] Loaded {len(self.events)} events from cache")
            return True
        
        except Exception as e:
            print(f"[NEWS] Failed to load cache: {e}")
            return False

    def _save_to_cache(self):
        """Save events to cache file"""
        cache_file = self._get_cache_file()
        try:
            data = {
                "last_fetch": self.last_fetch.isoformat(),
                "events": [e.to_dict() for e in self.events],
            }
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)
            print(f"[NEWS] Saved {len(self.events)} events to cache")
        except Exception as e:
            print(f"[NEWS] Failed to save cache: {e}")

    async def _fetch_rss_feed(self, url: str, currency: str) -> List[NewsEvent]:
        """Fetch and parse RSS feed"""
        events = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        print(f"[NEWS] Failed to fetch {currency} feed: {response.status}")
                        return events
                    
                    content = await response.text()
                    root = ET.fromstring(content)
                    
                    # Parse RSS items
                    for item in root.findall(".//item"):
                        title = item.find("title").text if item.find("title") is not None else ""
                        pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                        
                        # Determine impact based on keywords
                        impact = "LOW"
                        for keyword in self.HIGH_IMPACT_KEYWORDS:
                            if keyword.lower() in title.lower():
                                impact = "HIGH"
                                break
                        
                        # Parse date (RSS format: "Wed, 01 Jun 2026 08:30:00 GMT")
                        try:
                            event_time = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
                        except:
                            continue
                        
                        # Only include future events
                        if event_time > datetime.utcnow():
                            events.append(NewsEvent(
                                title=title,
                                currency=currency,
                                impact=impact,
                                event_time=event_time,
                            ))
        
        except Exception as e:
            print(f"[NEWS] Error fetching {currency} feed: {e}")
        
        return events

    async def fetch_news(self, force_refresh: bool = False) -> List[NewsEvent]:
        """
        Fetch news events from RSS feeds.
        Use cache if available and not expired.
        """
        # Try cache first
        if not force_refresh and self._load_from_cache():
            return self.events
        
        print("[NEWS] Fetching fresh news data...")
        all_events = []
        
        # Fetch all currency feeds in parallel
        tasks = []
        for currency in self.currencies:
            if currency in self.RSS_FEEDS:
                tasks.append(self._fetch_rss_feed(self.RSS_FEEDS[currency], currency))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_events.extend(result)
        
        # Sort by event time
        all_events.sort(key=lambda e: e.event_time)
        
        self.events = all_events
        self.last_fetch = datetime.utcnow()
        self._save_to_cache()
        
        print(f"[NEWS] Fetched {len(all_events)} events")
        return all_events

    def get_upcoming_events(self, hours_ahead: int = 24) -> List[NewsEvent]:
        """Get events in the next N hours"""
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours_ahead)
        
        return [
            e for e in self.events
            if now <= e.event_time <= cutoff
        ]

    def is_safe_to_trade(self, check_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Check if it's safe to trade at given time.
        Returns: {"safe": bool, "reason": str, "next_event": NewsEvent or None}
        """
        if check_time is None:
            check_time = datetime.utcnow()
        
        buffer = timedelta(minutes=self.buffer_minutes)
        
        # Check for high-impact events within buffer window
        for event in self.events:
            if event.impact != "HIGH":
                continue
            
            time_diff = event.event_time - check_time
            
            # Event is within buffer window (before or after)
            if abs(time_diff.total_seconds()) <= buffer.total_seconds():
                return {
                    "safe": False,
                    "reason": f"High-impact {event.currency} news in {int(time_diff.total_seconds()/60)} min: {event.title}",
                    "next_event": event,
                }
        
        return {
            "safe": True,
            "reason": "No high-impact news within buffer window",
            "next_event": None,
        }

    def get_news_summary(self) -> str:
        """Get human-readable summary of upcoming news"""
        upcoming = self.get_upcoming_events(hours_ahead=24)
        high_impact = [e for e in upcoming if e.impact == "HIGH"]
        
        if not high_impact:
            return "No high-impact news in next 24 hours"
        
        lines = [f"Upcoming high-impact news ({len(high_impact)}):"]
        for event in high_impact[:5]:  # Show max 5
            time_str = event.event_time.strftime("%H:%M")
            lines.append(f"  - {time_str} {event.currency}: {event.title}")
        
        return "\n".join(lines)


# Singleton instance
_calendar_instance: Optional[EconomicCalendar] = None


def get_calendar(
    cache_dir: str = "db/news_cache",
    buffer_minutes: int = 30,
    currencies: List[str] = None,
) -> EconomicCalendar:
    """Get or create singleton calendar instance"""
    global _calendar_instance
    if _calendar_instance is None:
        _calendar_instance = EconomicCalendar(
            cache_dir=cache_dir,
            buffer_minutes=buffer_minutes,
            currencies=currencies,
        )
    return _calendar_instance