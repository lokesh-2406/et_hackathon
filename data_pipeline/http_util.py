"""HTTP Utilities with Caching, Retries, and Rate Limiting.

Provides robust fetching with automatic disk caching to prevent
unnecessary API requests and rate-limiting issues.
"""
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import requests

from .config import USER_AGENT, RAW_DIR

API_CACHE_DIR = RAW_DIR / "api_cache"
API_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _get_cache_path(url: str, method: str, params: Optional[Dict] = None, data: Optional[Any] = None) -> Path:
    """Generate a deterministic cache file path based on request signature."""
    sig = f"{method}:{url}"
    if params:
        sig += f":params={json.dumps(params, sort_keys=True)}"
    if data:
        if isinstance(data, dict):
            sig += f":data={json.dumps(data, sort_keys=True)}"
        else:
            sig += f":data={str(data)}"
            
    hash_str = hashlib.md5(sig.encode('utf-8')).hexdigest()
    # Create subdirectories based on domain/endpoint hints for organization
    domain_hint = url.split("://")[-1].split("/")[0]
    domain_dir = API_CACHE_DIR / domain_hint
    domain_dir.mkdir(exist_ok=True)
    return domain_dir / f"{hash_str}.json"


def read_cache(url: str, method: str, params: Optional[Dict] = None, data: Optional[Any] = None, max_age_days: int = 1) -> Optional[Dict]:
    """Read a request from the local JSON cache if it exists and is fresh enough."""
    cache_path = _get_cache_path(url, method, params, data)
    if not cache_path.exists():
        return None
        
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cached = json.load(f)
            
        retrieved_at = datetime.fromisoformat(cached.get("retrieved_at", "2000-01-01T00:00:00"))
        age_days = (datetime.now() - retrieved_at).total_seconds() / 86400.0
        
        if age_days > max_age_days:
            return None  # Stale
            
        return cached
    except Exception:
        return None


def write_cache(url: str, method: str, params: Optional[Dict], data: Optional[Any], 
                response_text: str, status_code: int, headers: Dict) -> None:
    """Write raw response to local cache along with metadata."""
    cache_path = _get_cache_path(url, method, params, data)
    
    # Try to parse as JSON for cleaner storage, fallback to string
    try:
        content = json.loads(response_text)
        is_json = True
    except Exception:
        content = response_text
        is_json = False

    meta = {
        "url": url,
        "method": method,
        "params": params,
        "request_data": data if isinstance(data, (dict, list, str, type(None))) else str(data),
        "retrieved_at": datetime.now().isoformat(),
        "status_code": status_code,
        "content_length": len(response_text),
        "is_json": is_json,
        "content": content
    }
    
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  [warning] Failed to write cache {cache_path}: {e}")


def request_with_cache(method: str, url: str, force: bool = False, max_age_days: int = 1,
                       retries: int = 5, pause: float = 0.0, **kw) -> Tuple[Optional[Union[Dict, str]], Dict]:
    """
    Make an HTTP request with caching, retries, and exponential backoff.
    Returns (parsed_content, cache_metadata_dict)
    """
    params = kw.get("params")
    data = kw.get("data")
    
    if not force:
        cached = read_cache(url, method, params, data, max_age_days)
        if cached:
            return cached.get("content"), cached

    # Need to fetch
    headers = {**USER_AGENT, **kw.pop("headers", {})}
    timeout = kw.pop("timeout", 40)
    
    for i in range(retries):
        try:
            r = requests.request(method, url, headers=headers, timeout=timeout, **kw)
            
            # Cache it regardless of success if we got a response, might be useful for debugging
            write_cache(url, method, params, data, r.text, r.status_code, dict(r.headers))
            
            if r.status_code == 200:
                if pause:
                    time.sleep(pause)
                try:
                    return r.json(), {"status_code": r.status_code, "cached": False, "source": "network"}
                except ValueError:
                    return r.text, {"status_code": r.status_code, "cached": False, "source": "network"}
            print(f"  [http {r.status_code}] {url[:90]} (try {i+1})")
        except (requests.RequestException, ValueError) as e:
            print(f"  [error] {type(e).__name__}: {e} (try {i+1})")
        
        time.sleep(2 ** i)
        
    return None, {"status_code": 0, "error": "Max retries exceeded"}

