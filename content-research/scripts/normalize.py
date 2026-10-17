#!/usr/bin/env python3
"""Normalize and deduplicate collected source records into an evidence set.

    python3 scripts/normalize.py web.jsonl reddit.jsonl youtube.jsonl > evidence.jsonl
    cat *.jsonl | python3 scripts/normalize.py > evidence.jsonl

Input: JSON Lines in the source record shape (schemas/source.json).
Output: JSON Lines in the evidence record shape (schemas/evidence.json), one per
distinct item, each with a stable evidence_id for citations. A summary goes to stderr.

Nothing is invented: unknown dates stay null, `url` stays the URL that was retrieved
(the canonical form is only used to find duplicates), and unobserved metrics stay absent.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schema_check import load_schema, validate  # noqa: E402

_QA_HOSTS = {"stackoverflow.com", "superuser.com", "serverfault.com", "askubuntu.com", "mathoverflow.net"}
TRACKING_PARAMS = {"fbclid", "gclid", "dclid", "msclkid", "igshid", "mc_cid", "mc_eid",
                   "_hsenc", "_hsmi", "ref_src", "ref_url", "si", "feature", "spm"}
MIN_TEXT_FOR_HASH = 200  # shorter texts are too generic to treat as copies
MIN_TITLE_FOR_MIRROR = 20  # shorter titles ("Home", "Blog") say nothing about identity
FUTURE_TOLERANCE = timedelta(days=1)
ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# ---------------------------------------------------------------- URLs


def _is_tracking(name):
    name = name.lower()
    return name.startswith("utm_") or name in TRACKING_PARAMS


def canonical_url(url):
    """A stable form of a URL, for finding duplicates only. Never use it as a citation."""
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    for prefix in ("www.", "m.", "mobile."):
        if host.startswith(prefix):
            host = host[len(prefix):]
            break
    if host.endswith(".reddit.com"):
        host = "reddit.com"
    path = parts.path or "/"
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not _is_tracking(k)]

    if host == "youtu.be":
        video = path.strip("/").split("/")[0]
        host, path, query = "youtube.com", "/watch", [("v", video)]
    elif host in ("youtube.com", "music.youtube.com"):
        host = "youtube.com"
        match = re.match(r"^/(?:shorts|embed|live)/([\w-]+)", path)
        if match:
            path, query = "/watch", [("v", match.group(1))]
        elif path == "/watch":
            query = [(k, v) for k, v in query if k == "v"]
    elif host == "github.com":
        path = path.lower()
    elif host in _QA_HOSTS or host.endswith(".stackexchange.com"):
        # /questions/<id>/<slug> and /q/<id> are the same question
        match = re.match(r"^/(?:questions|q)/(\d+)", path)
        if match:
            path, query = f"/questions/{match.group(1)}", []     # the id identifies the question; parameters like ?rq=1 do not

    path = re.sub(r"/{2,}", "/", path)
    if len(path) > 1:
        path = path.rstrip("/")
    try:
        port = parts.port
    except ValueError:
        port = None
    netloc = host if port in (None, 80, 443) else f"{host}:{port}"
    return urlunsplit(("https", netloc, path, urlencode(sorted(query)), ""))


# ---------------------------------------------------------------- dates

_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:[.,]\d+)?)?)?\s*(Z|[+-]\d{2}:?\d{2})?$")
_DAY_FORMATS = ("%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y", "%Y/%m/%d", "%b %d %Y")  # as printed on pages
_RELATIVE = re.compile(r"^(\d+|an?|one)\s+(minute|hour|day|week|month|year)s?\s+ago$", re.I)
_UNIT_DAYS = {"minute": 1 / 1440, "hour": 1 / 24, "day": 1, "week": 7, "month": 30, "year": 365}


def parse_datetime(value):
    """Parse a timestamp. Returns an aware UTC datetime, or None if it is not one."""
    if isinstance(value, str):
        text = value.strip()
        match = _ISO.match(text)
        if match:
            y, mo, d, h, mi, s, tz = match.groups()
            try:
                dt = datetime(int(y), int(mo), int(d), int(h or 0), int(mi or 0), int(s or 0),
                              tzinfo=timezone.utc)
            except ValueError:
                return None
            if tz and tz != "Z":
                sign = 1 if tz[0] == "+" else -1
                digits = tz[1:].replace(":", "")
                dt -= sign * timedelta(hours=int(digits[:2]), minutes=int(digits[2:]))
            return dt
        try:
            dt = parsedate_to_datetime(text)  # RFC 2822, e.g. "Tue, 01 Sep 2026 09:00:00 GMT"
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError, IndexError):
            pass
        for pattern in _DAY_FORMATS:
            try:
                return datetime.strptime(text, pattern).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None
    return None


def _is_day_format(text):
    for pattern in _DAY_FORMATS:
        try:
            datetime.strptime(text, pattern)
            return True
        except ValueError:
            continue
    return False


def parse_published(value, retrieved):
    """Return (iso_utc or None, precision or None, warning or None).

    precision: "exact" (time given), "day" (date only), "approx" (relative, such as "3 days ago").
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, None, None
    text = str(value).strip()

    if re.fullmatch(r"\d{10}|\d{13}", text):  # epoch seconds or milliseconds
        seconds = int(text) / (1000 if len(text) == 13 else 1)
        dt, precision = datetime.fromtimestamp(seconds, tz=timezone.utc), "exact"
    elif text.lower() in ("today", "just now", "yesterday") or _RELATIVE.match(text):
        lowered = text.lower()
        if lowered in ("today", "just now"):
            days = 0
        elif lowered == "yesterday":
            days = 1
        else:
            amount, unit = _RELATIVE.match(text).groups()
            days = (1 if amount.lower() in ("a", "an", "one") else int(amount)) * _UNIT_DAYS[unit.lower()]
        dt, precision = retrieved - timedelta(days=days), "approx"
    else:
        dt = parse_datetime(text)
        if dt is None:
            return None, None, "date_unparseable"
        iso = _ISO.match(text)
        precision = "day" if (iso and not iso.group(4)) or (not iso and _is_day_format(text)) else "exact"

    if dt > retrieved + FUTURE_TOLERANCE:
        return None, None, "date_in_future"
    return dt.strftime(ISO_FORMAT), precision, None


# ---------------------------------------------------------------- text

_TAGS = re.compile(r"<[^>]+>")
_INVISIBLE = re.compile(r"[​-‏⁠﻿\x00-\x08\x0b\x0c\x0e-\x1f]")


def clean_text(value):
    text = html.unescape(_TAGS.sub(" ", value or ""))
    text = _INVISIBLE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


_SECOND_LEVEL = {"co", "com", "org", "net", "gov", "ac", "edu"}


def registrable_domain(host):
    """The site a hostname belongs to, approximately (app.example.com and www.example.com match)."""
    labels = host.split(".")
    if len(labels) >= 3 and labels[-2] in _SECOND_LEVEL and len(labels[-1]) == 2:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def mirror_key(record):
    """Same long title on one site's hostnames is the same page (mirrors, www/app/api). Web and news only."""
    if record["source_type"] in ("web", "news") and len(record["title"]) >= MIN_TITLE_FOR_MIRROR:
        return registrable_domain(record["domain"]), record["title"].lower()
    return None


def content_hash(title, text):
    if len(text) < MIN_TEXT_FOR_HASH:
        return None
    basis = f"{title.lower()}|{text[:500].lower()}"
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- records


def normalize_record(raw, source_schema):
    """Return (evidence record, None) or (None, [errors])."""
    errors = validate(raw, source_schema)
    if errors:
        return None, errors
    if raw["id"].split(":", 1)[0] != raw["source_type"]:
        return None, [f"$.id: prefix does not match source_type {raw['source_type']!r}"]
    retrieved = parse_datetime(raw["retrieved_at"])
    if retrieved is None:
        return None, ["$.retrieved_at: not a valid timestamp"]

    warnings = []
    published, precision, warning = parse_published(raw.get("published_at"), retrieved)
    if warning:
        warnings.append(warning)
    raw_date = raw.get("published_at")
    title, text = clean_text(raw["title"]), clean_text(raw.get("text"))
    if not text:
        warnings.append("no_text")
    canonical = canonical_url(raw["url"])

    record = {
        "evidence_id": "e-" + hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:8],
        "id": raw["id"],
        "source_type": raw["source_type"],
        "url": raw["url"],
        "canonical_url": canonical,
        "domain": urlsplit(canonical).netloc,
        "title": title,
        "author": raw.get("author"),
        "published_at": published,
        "published_at_raw": raw_date if raw_date and raw_date != published else None,
        "date_precision": precision,
        "retrieved_at": retrieved.strftime(ISO_FORMAT),
        "text": text,
        "metrics": dict(raw.get("metrics") or {}),
        "queries": [raw["query"]],
        "access": raw["access"],
        "tier": raw["tier"],
        "competitor": raw.get("competitor"),
        "extra": dict(raw.get("extra") or {}),
        "duplicate_urls": [],
        "merged_count": 1,
        "warnings": warnings,
    }
    record["quality"] = quality(record)
    return record, None


def quality(record):
    age = None
    if record["published_at"]:
        published = datetime.strptime(record["published_at"], ISO_FORMAT)
        retrieved = datetime.strptime(record["retrieved_at"], ISO_FORMAT)
        age = max(0, (retrieved - published).days)
    return {
        "dated": record["published_at"] is not None,
        "fetched": record["access"] == "fetched",
        "has_text": len(record["text"]) >= 80,
        "metrics": sorted(record["metrics"]),
        "age_days": age,
    }


def _rank(record):
    return (record["access"] == "fetched", record["published_at"] is not None,
            len(record["metrics"]), len(record["text"]))


def merge_group(group):
    primary = max(group, key=_rank)  # first wins on ties
    merged = dict(primary)
    merged["metrics"] = dict(primary["metrics"])
    merged["warnings"] = list(primary["warnings"])
    merged["queries"] = list(dict.fromkeys(q for r in group for q in r["queries"]))
    merged["duplicate_urls"] = list(dict.fromkeys(
        r["url"] for r in group if r["url"] != primary["url"]))
    merged["merged_count"] = len(group)
    for other in group:
        for key, value in other["metrics"].items():
            merged["metrics"].setdefault(key, value)
    if merged["competitor"] is None:
        merged["competitor"] = next((r["competitor"] for r in group if r["competitor"]), None)
    if merged["published_at"] is None:
        donor = next((r for r in group if r["published_at"]), None)
        if donor:
            for key in ("published_at", "published_at_raw", "date_precision"):
                merged[key] = donor[key]
            merged["warnings"] = [w for w in merged["warnings"] if not w.startswith("date_")]
    merged["quality"] = quality(merged)
    return merged


def deduplicate(records):
    """Group by canonical URL, then identical long text, then same long title on one site. Keep first-seen order."""
    groups, by_url, by_hash, by_mirror = [], {}, {}, {}
    for record in records:
        index = by_url.get(record["canonical_url"])
        digest = content_hash(record["title"], record["text"])
        mirror = mirror_key(record)
        if index is None and digest:
            index = by_hash.get(digest)
        if index is None and mirror:
            index = by_mirror.get(mirror)
        if index is None:
            index = len(groups)
            groups.append([])
        groups[index].append(record)
        by_url.setdefault(record["canonical_url"], index)
        if digest:
            by_hash.setdefault(digest, index)
        if mirror:
            by_mirror.setdefault(mirror, index)
    return [merge_group(g) for g in groups]


def normalize_lines(lines, label="input"):
    """Return (evidence records, rejected [(where, errors)], records_read)."""
    schema = load_schema("source.json")
    accepted, rejected, count = [], [], 0
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        count += 1
        where = f"{label}:{number}"
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as err:
            rejected.append((where, [f"invalid JSON: {err.msg}"]))
            continue
        record, errors = normalize_record(raw, schema)
        if errors:
            rejected.append((where, errors))
        else:
            accepted.append(record)
    return accepted, rejected, count


def summarize(read, rejected, accepted, evidence):
    by_source = Counter(r["source_type"] for r in evidence)
    undated = sum(1 for r in evidence if not r["published_at"])
    warnings = Counter(w for r in evidence for w in r["warnings"])
    lines = [f"normalize: {read} read, {len(rejected)} rejected, "
             f"{len(accepted) - len(evidence)} duplicates merged -> {len(evidence)} evidence records"]
    if by_source:
        lines.append("  by source: " + ", ".join(f"{k} {v}" for k, v in sorted(by_source.items())))
    if evidence:
        lines.append(f"  undated: {undated} of {len(evidence)}")
    if warnings:
        lines.append("  warnings: " + ", ".join(f"{k} {v}" for k, v in sorted(warnings.items())))
    for where, errors in rejected:
        lines.append(f"  rejected {where}: {'; '.join(errors)}")
    return "\n".join(lines)


def main(argv=None, stdin=None, out=None, err=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="*", help="JSONL files; reads stdin if none are given")
    parser.add_argument("--strict", action="store_true", help="exit 1 if any record was rejected")
    args = parser.parse_args(argv)
    out, err, stdin = out or sys.stdout, err or sys.stderr, stdin or sys.stdin

    accepted, rejected, read = [], [], 0
    try:
        sources = [(path, open(path, encoding="utf-8")) for path in args.files] or [("stdin", stdin)]
    except OSError as error:
        print(f"normalize: cannot read {error.filename}: {error.strerror}", file=err)
        return 2
    for label, handle in sources:
        a, r, n = normalize_lines(handle, os.path.basename(label))
        accepted += a
        rejected += r
        read += n
        if handle is not stdin:
            handle.close()

    evidence = deduplicate(accepted)
    for record in evidence:
        out.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(summarize(read, rejected, accepted, evidence), file=err)
    return 1 if (args.strict and rejected) else 0


if __name__ == "__main__":
    sys.exit(main())
