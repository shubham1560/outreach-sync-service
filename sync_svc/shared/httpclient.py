import json
import uuid
import time
import logging
import random
from typing import Dict, Optional, Any
import requests
from requests.exceptions import (
    RequestException,
    ConnectionError,
    Timeout,
    HTTPError,
    TooManyRedirects,
)

logger = logging.getLogger(__name__)


class HttpClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        default_headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        auth: Optional[tuple] = None,
        max_retries: int = 3,
        jitter: bool = True
    ):
        self.base_url = base_url.rstrip('/') if base_url else None
        self.default_headers = default_headers or {}
        self.timeout = timeout
        self.auth = auth
        self.max_retries = max_retries
        self.jitter = jitter
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if an error is retryable."""
        if isinstance(error, (ConnectionError, Timeout, TooManyRedirects)):
            return True
        
        if isinstance(error, HTTPError):
            if error.response is None:
                return True
            status_code = error.response.status_code
            if status_code >= 500 or status_code == 429:
                return True
            return False
        
        if isinstance(error, RequestException):
            return True
        
        return False
    
    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff: 2^1, 2^2, 2^3, 2^4, 2^5 seconds.
        """
        exponent = min(attempt + 1, 5)
        backoff = 2 ** exponent
        return backoff
    
    def _log_error(self, error_instance_id: str, function_name: str, error: Exception, url: str, attempt: int = None):
        """Log error in structured format: Instance - uuid - function_name - error_type"""
        error_type = type(error).__name__
        if attempt is not None:
            log_message = f"{error_instance_id} - {function_name} - Attempt {attempt + 1}/{self.max_retries + 1} - {error_type} - URL: {url}"
        else:
            log_message = f"{error_instance_id} - {function_name} - {error_type} - URL: {url}"
        logger.error(log_message, exc_info=True)
    
    def _execute_with_retry(self, method: str, url: str, function_name: str, **request_kwargs) -> Dict[str, Any]:
        """Execute HTTP request with retry logic and exponential backoff."""
        full_url = self._build_url(url)
        last_error = None
        error_instance_id = str(uuid.uuid4())
        
        for attempt in range(self.max_retries + 1):
            try:
                if method.upper() == 'GET':
                    response = requests.get(full_url, **request_kwargs)
                elif method.upper() == 'POST':
                    response = requests.post(full_url, **request_kwargs)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                
                try:
                    data = response.json()
                except (ValueError, json.JSONDecodeError):
                    data = response.text
                
                return {
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'data': data
                }
                
            except Exception as e:
                last_error = e
                is_retryable = self._is_retryable_error(e)
                
                if not is_retryable or attempt >= self.max_retries:
                    self._log_error(error_instance_id, function_name, e, full_url)
                    raise
                
                self._log_error(error_instance_id, function_name, e, full_url, attempt)
                
                if attempt < self.max_retries:
                    backoff_time = self._calculate_backoff(attempt)
                    logger.info(
                        f"{error_instance_id} - {function_name} - "
                        f"Retrying in {backoff_time:.2f}s (attempt {attempt + 2}/{self.max_retries + 1})"
                    )
                    time.sleep(backoff_time)
        
        if last_error:
            self._log_error(error_instance_id, function_name, last_error, full_url)
            raise last_error
    
    def _build_url(self, url: str) -> str:
        if self.base_url:
            if url.startswith('http://') or url.startswith('https://'):
                return url
            return f"{self.base_url}/{url.lstrip('/')}"
        return url
    
    def _merge_headers(self, headers: Optional[Dict[str, str]]) -> Dict[str, str]:
        merged = self.default_headers.copy()
        if headers:
            merged.update(headers)
        return merged
    
    def get(self, url: str, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request with retry logic and exponential backoff."""
        merged_headers = self._merge_headers(headers)
        
        request_kwargs = {
            'headers': merged_headers,
            'params': params,
            'timeout': self.timeout,
            'auth': self.auth
        }
        
        return self._execute_with_retry('GET', url, 'HttpClient.get', **request_kwargs)
    
    def post(self, url: str, body: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a POST request with retry logic and exponential backoff."""
        merged_headers = self._merge_headers(headers)
        
        request_kwargs = {
            'headers': merged_headers,
            'timeout': self.timeout,
            'auth': self.auth
        }
        
        if json_data is not None:
            merged_headers.setdefault('Content-Type', 'application/json')
            request_kwargs['json'] = json_data
        elif body is not None:
            request_kwargs['data'] = body
        
        return self._execute_with_retry('POST', url, 'HttpClient.post', **request_kwargs)
