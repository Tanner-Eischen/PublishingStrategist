"""Ubersuggest API Client for keyword research data.

Provides search volume, competition, and CPC data with comprehensive
error handling and fallback strategies.
"""

import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from .http_client import SyncHTTPClient, HTTPClientConfig

logger = logging.getLogger(__name__)


@dataclass
class KeywordData:
    """Keyword research data from Ubersuggest API."""
    search_volume: int = 0
    competition: float = 0.5
    cpc: float = 0.0
    difficulty: Optional[float] = None
    trend: Optional[str] = None
    source: str = "ubersuggest"
    last_updated: Optional[datetime] = None


class UbersuggestClient:
    """Simple Ubersuggest API client with comprehensive error handling."""
    
    def __init__(self, api_key: str, timeout: int = 15):
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = "https://api.ubersuggest.io/v1"
        
        # Initialize unified HTTP client
        config = HTTPClientConfig(
            timeout=timeout,
            max_retries=2,
            retry_delay=1.0
        )
        self.client = SyncHTTPClient(config)
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum 1 second between requests
        
        # Error tracking
        self.consecutive_failures = 0
        self.last_failure_time = None
        self.max_consecutive_failures = 3
        self.failure_backoff_seconds = 300  # 5 minutes
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        logger.info("UbersuggestClient initialized")
    
    def get_keyword_data(self, keyword: str) -> Optional[KeywordData]:
        """Get keyword research data from Ubersuggest API.
        
        Returns None if API fails, allowing graceful fallback to Amazon-only analysis.
        """
        if not keyword or not keyword.strip():
            logger.warning("Empty keyword provided to UbersuggestClient")
            return None
        
        keyword = keyword.strip()
        
        # Check if we should skip due to recent failures
        if self._should_skip_due_to_failures():
            logger.info(f"Skipping Ubersuggest request for '{keyword}' due to recent failures")
            return None
        
        try:
            # Rate limiting
            self._enforce_rate_limit()
            
            # Make API request
            self.total_requests += 1
            data = self._make_api_request(keyword)
            
            if data:
                self.successful_requests += 1
                self.consecutive_failures = 0
                self.last_failure_time = None
                
                keyword_data = self._parse_keyword_data(keyword, data)
                logger.info(f"Successfully retrieved keyword data for '{keyword}'")
                return keyword_data
            else:
                self._handle_api_failure(f"No data returned for keyword '{keyword}'")
                return None
                
        except Exception as e:
            # Handle various HTTP client exceptions
            if 'timeout' in str(e).lower():
                self._handle_api_failure(f"Timeout retrieving data for '{keyword}'")
            elif 'connection' in str(e).lower():
                self._handle_api_failure(f"Connection error for '{keyword}'")
            elif 'http' in str(e).lower():
                self._handle_api_failure(f"HTTP error for '{keyword}': {e}")
            else:
                self._handle_api_failure(f"Request error for '{keyword}': {e}")
            return None
        except Exception as e:
            self._handle_api_failure(f"Unexpected error for '{keyword}': {e}")
            return None
    
    def _make_api_request(self, keyword: str) -> Optional[Dict[str, Any]]:
        """Make the actual API request to Ubersuggest."""
        url = f"{self.base_url}/keywords"
        
        params = {
            'keyword': keyword,
            'country': 'US',
            'language': 'en'
        }
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'KDP-Strategist/1.0'
        }
        
        logger.debug(f"Making Ubersuggest API request for keyword: {keyword}")
        
        try:
            # Use unified HTTP client
            data = self.client.get(url, params=params, headers=headers)
            return data
        except Exception as e:
            error_msg = str(e).lower()
            if '429' in error_msg or 'rate limit' in error_msg:
                logger.warning("Ubersuggest API rate limit exceeded")
                time.sleep(60)  # Wait 1 minute for rate limit
                raise Exception("Rate limit exceeded")
            elif '401' in error_msg or 'authentication' in error_msg:
                logger.error("Ubersuggest API authentication failed - check API key")
                raise Exception("Authentication failed")
            else:
                logger.error(f"API request failed: {e}")
                raise
            return None
    
    def _parse_keyword_data(self, keyword: str, data: Dict[str, Any]) -> KeywordData:
        """Parse Ubersuggest API response into KeywordData object."""
        try:
            # Extract data with safe defaults
            search_volume = int(data.get('search_volume', 0))
            competition = float(data.get('competition', 0.5))
            cpc = float(data.get('cpc', 0.0))
            difficulty = data.get('difficulty')
            trend = data.get('trend')
            
            # Validate and normalize data
            search_volume = max(0, search_volume)
            competition = max(0.0, min(1.0, competition))  # Ensure 0-1 range
            cpc = max(0.0, cpc)
            
            if difficulty is not None:
                difficulty = max(0.0, min(100.0, float(difficulty)))
            
            return KeywordData(
                search_volume=search_volume,
                competition=competition,
                cpc=cpc,
                difficulty=difficulty,
                trend=trend,
                source="ubersuggest",
                last_updated=datetime.now()
            )
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing Ubersuggest data for '{keyword}': {e}")
            # Return default data rather than None to maintain some functionality
            return KeywordData(
                search_volume=0,
                competition=0.5,
                cpc=0.0,
                source="ubersuggest_fallback",
                last_updated=datetime.now()
            )
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting between API requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _should_skip_due_to_failures(self) -> bool:
        """Check if we should skip API requests due to recent failures."""
        if self.consecutive_failures < self.max_consecutive_failures:
            return False
        
        if self.last_failure_time is None:
            return False
        
        time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
        return time_since_failure < self.failure_backoff_seconds
    
    def _handle_api_failure(self, error_message: str):
        """Handle API failure with logging and failure tracking."""
        self.failed_requests += 1
        self.consecutive_failures += 1
        self.last_failure_time = datetime.now()
        
        logger.warning(f"Ubersuggest API failure ({self.consecutive_failures}/{self.max_consecutive_failures}): {error_message}")
        
        if self.consecutive_failures >= self.max_consecutive_failures:
            logger.error(f"Ubersuggest API has failed {self.consecutive_failures} consecutive times. "
                        f"Entering backoff period of {self.failure_backoff_seconds} seconds.")
    
    def is_healthy(self) -> bool:
        """Check if the client is in a healthy state."""
        return self.consecutive_failures < self.max_consecutive_failures
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics for monitoring."""
        success_rate = 0.0
        if self.total_requests > 0:
            success_rate = (self.successful_requests / self.total_requests) * 100
        
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': success_rate,
            'consecutive_failures': self.consecutive_failures,
            'is_healthy': self.is_healthy(),
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None
        }
    
    def reset_failure_state(self):
        """Reset failure state (useful for testing or manual recovery)."""
        self.consecutive_failures = 0
        self.last_failure_time = None
        logger.info("UbersuggestClient failure state reset")