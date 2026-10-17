"""Polite HTTP for the keyless source scripts (stdlib only).

Every request goes through one Fetcher, which:
- identifies itself honestly (no browser impersonation, no proxy rotation),
- waits a minimum interval per host, remembered across script runs, so a shell loop of
  searches does not burst past a provider's limit,
- honors Retry-After and rate-limit responses, with a short capped backoff,
- stops after a request budget,
- optionally caches successful responses on disk (off unless CR_CACHE_DIR is set).

If a provider refuses a request, the script reports that source as unavailable. It never
tries to get around the refusal.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from record import SourceError

USER_AGENT = "ai-agent-skills-content-research/0.1 (research script)"
DEFAULT_INTERVAL = 1.0                      # seconds between requests to one host
HOST_INTERVALS = {                          # providers with tighter published limits
    "api.github.com": 6.5,                  # 10 searches per minute without a token
    "api.stackexchange.com": 0.5,
    "hn.algolia.com": 1.0,
    "www.googleapis.com": 0.25,
}
MAX_RETRIES = 3
MAX_WAIT = 60                               # never sleep longer than this inside a script
DEFAULT_BUDGET = 60                         # requests per process


class Fetcher:
    def __init__(self, *, opener=None, sleep=time.sleep, now=time.time, state_dir=None,
                 cache_dir=None, cache_ttl=3600, max_requests=DEFAULT_BUDGET, intervals=None):
        self.opener = opener or urllib.request.urlopen
        self.sleep, self.now = sleep, now
        self.state_dir = state_dir or os.path.join(tempfile.gettempdir(), "ai-agent-skills-throttle")
        self.cache_dir, self.cache_ttl = cache_dir, cache_ttl
        self.max_requests, self.sent = max_requests, 0
        self.intervals = {**HOST_INTERVALS, **(intervals or {})}

    # ---- throttle: one timestamp file per host, shared by every script run on this machine

    def _state_path(self, host):
        os.makedirs(self.state_dir, exist_ok=True)
        return os.path.join(self.state_dir, hashlib.sha1(host.encode()).hexdigest()[:16])

    def _last(self, host):
        try:
            with open(self._state_path(host)) as handle:
                return float(handle.read())
        except (OSError, ValueError):
            return 0.0

    def _wait_turn(self, host):
        delay = self._last(host) + self.intervals.get(host, DEFAULT_INTERVAL) - self.now()
        if delay > 0:
            self.sleep(min(delay, MAX_WAIT))
        with open(self._state_path(host), "w") as handle:
            handle.write(str(self.now()))

    def defer(self, host, seconds):
        """Make the next request to `host` (from any script run) wait at least `seconds`."""
        interval = self.intervals.get(host, DEFAULT_INTERVAL)
        with open(self._state_path(host), "w") as handle:
            handle.write(str(self.now() + seconds - interval))

    # ---- cache

    def _cache_file(self, url):
        return os.path.join(self.cache_dir, hashlib.sha1(url.encode()).hexdigest() + ".json")

    def _cached(self, url):
        if not self.cache_dir:
            return None
        try:
            with open(self._cache_file(url)) as handle:
                entry = json.load(handle)
            if self.now() - entry["time"] < self.cache_ttl:
                return entry["text"]
        except (OSError, ValueError, KeyError):
            pass
        return None

    def _store(self, url, text):
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)
            with open(self._cache_file(url), "w") as handle:
                json.dump({"time": self.now(), "text": text}, handle)

    # ---- requests

    def get_text(self, url, headers=None, timeout=20):
        cached = self._cached(url)
        if cached is not None:
            return cached
        host = urllib.parse.urlsplit(url).netloc
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip",
                                                       **(headers or {})})
        for attempt in range(MAX_RETRIES + 1):
            if self.sent >= self.max_requests:
                raise SourceError(f"request budget of {self.max_requests} reached; stopping to stay polite "
                                  "(raise it with CR_MAX_REQUESTS if you need more)")
            self._wait_turn(host)
            self.sent += 1
            try:
                with self.opener(request, timeout=timeout) as response:
                    raw = response.read()
            except urllib.error.HTTPError as err:
                wait = self._retry_wait(err, attempt)
                if wait is None or attempt == MAX_RETRIES:
                    raise SourceError(self._describe(host, err))
                self.sleep(wait)
                continue
            except urllib.error.URLError as err:
                raise SourceError(f"could not reach {host}: {err.reason}")
            except TimeoutError:
                raise SourceError(f"{host} did not respond within {timeout} seconds")
            if raw[:2] == b"\x1f\x8b":  # some APIs gzip even when not asked to
                raw = gzip.decompress(raw)
            text = raw.decode("utf-8", errors="replace")
            self._store(url, text)
            return text

    def get_json(self, url, headers=None, timeout=20):
        try:
            return json.loads(self.get_text(url, headers, timeout))
        except json.JSONDecodeError:
            raise SourceError(f"{urllib.parse.urlsplit(url).netloc} did not return JSON")

    def _retry_wait(self, err, attempt):
        """Seconds to wait before retrying, or None if the response is not worth retrying."""
        retry_after = _header_int(err, "Retry-After")
        limited = err.code in (429, 503) or (err.code == 403 and (
            _header_int(err, "X-RateLimit-Remaining") == 0 or "rate limit" in _error_message(err).lower()))
        if not limited:
            return None
        wait = retry_after if retry_after is not None else 2 ** (attempt + 1)
        return wait if wait <= MAX_WAIT else None  # a long wait is the provider telling us to stop

    def _describe(self, host, err):
        message = _error_message(err)
        if err.code in (403, 429, 503):
            retry_after = _header_int(err, "Retry-After")
            reset = _header_int(err, "X-RateLimit-Reset")
            hint = (f" Try again in {retry_after} seconds." if retry_after
                    else f" The limit resets at {_iso(reset)}." if reset else "")
            return f"{host} is rate limiting or refusing requests (HTTP {err.code}: {message}).{hint} Not retrying."
        return f"{host} returned HTTP {err.code}: {message}"


def _header_int(err, name):
    try:
        return int(err.headers.get(name))
    except (TypeError, ValueError, AttributeError):
        return None


def _error_message(err):
    try:
        body = err.read()
        if body[:2] == b"\x1f\x8b":
            body = gzip.decompress(body)
        data = json.loads(body)
        message = str(data.get("message") or data.get("error_message") or err.reason)
        details = [e.get("message") for e in data.get("errors", []) if isinstance(e, dict) and e.get("message")]
        return f"{message} ({'; '.join(details)})" if details else message
    except Exception:
        return str(err.reason)


def _iso(seconds):
    return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime("%H:%M UTC")


# Module-level helpers used by the scripts. Configuration comes from the environment.
default = Fetcher(cache_dir=os.environ.get("CR_CACHE_DIR") or None,
                  max_requests=int(os.environ.get("CR_MAX_REQUESTS", DEFAULT_BUDGET)))


def get_text(url, headers=None, timeout=20):
    return default.get_text(url, headers, timeout)


def get_json(url, headers=None, timeout=20):
    return default.get_json(url, headers, timeout)


def defer(host, seconds):
    default.defer(host, seconds)


def date_to_epoch(text):
    """YYYY-MM-DD (UTC midnight) to epoch seconds."""
    try:
        return int(datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    except ValueError:
        raise SourceError(f"{text!r} is not a date in YYYY-MM-DD form")


def epoch_to_iso(seconds):
    return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
