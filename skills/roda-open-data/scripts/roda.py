"""roda.py - Registry of Open Data on AWS (RODA) helpers.

Reimplements the core of the awslabs roda-mcp-server (search, list, details,
organization/license discovery, related datasets, stats, STAC discovery,
S3 preview URL building) over the public index:
    https://registry.opendata.aws/index.ndjson

Use as a CLI (python roda.py --help) or import it and call the functions.
Download the index once with `python roda.py download` (or any HTTP client);
it is cached at ~/.cache/roda-open-data/index.ndjson unless RODA_INDEX is set.
In sandboxes without outbound internet, fetch the index with the platform's
download tool into $WORKSPACE_DIR/downloads/index.ndjson instead.
"""
import argparse, json, os, re, glob, sys
from collections import defaultdict, Counter

INDEX_URL = "https://registry.opendata.aws/index.ndjson"
SUPPORTED_LICENSE_TYPES = ["creative commons", "mit", "apache", "public domain"]
_STOP = set("a an and are as at be by data dataset datasets for from in into is it of on or "
            "the to with about any find show me i want need looking some".split())
_DS = None

CACHE_PATH = os.path.expanduser("~/.cache/roda-open-data/index.ndjson")

def _find_index():
    """Resolve the index: $RODA_INDEX, then $WORKSPACE_DIR/downloads, then the cache."""
    env = os.environ.get("RODA_INDEX")
    if env and os.path.exists(env): return env
    ws = globals().get("WORKSPACE_DIR") or os.environ.get("WORKSPACE_DIR", ".")
    hits = sorted(glob.glob(os.path.join(ws, "downloads", "index*.ndjson")), key=os.path.getmtime)
    if hits: return hits[-1]
    if os.path.exists(CACHE_PATH): return CACHE_PATH
    raise FileNotFoundError(f"Index not found. Run `python roda.py download` or fetch {INDEX_URL} first.")

def download_index(dest=None):
    """Download the public index (fixed HTTPS URL) and return the saved path."""
    from urllib.request import urlopen
    dest = dest or os.environ.get("RODA_INDEX") or CACHE_PATH
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    with urlopen(INDEX_URL, timeout=60) as r, open(dest, "wb") as f:
        f.write(r.read())
    return dest

def load(path=None, include_deprecated=False):
    """Load (and cache) the index. Deprecated datasets are excluded by default."""
    global _DS
    if _DS is None or path:
        rows = []
        with open(path or _find_index()) as f:
            for line in f:
                if line.strip():
                    try: rows.append(json.loads(line))
                    except json.JSONDecodeError: pass
        _DS = rows
    if include_deprecated:
        return _DS
    return [d for d in _DS if str(d.get("Deprecated", "")).lower() != "true"]

def _tags(d): return [t.lower() for t in (d.get("Tags") or []) if isinstance(t, str)]
def _org(d):
    raw = (d.get("ManagedBy") or "").strip().strip('"').strip()
    m = re.search(r"\[(.*?)\]", raw)
    return m.group(1) if m else raw

def summary(d, desc_chars=300):
    """Compact record for presenting results. License is kept verbatim."""
    desc = (d.get("Description") or "").strip()
    return {
        "slug": d.get("Slug"), "name": d.get("Name"),
        "description": desc[:desc_chars] + ("..." if len(desc) > desc_chars else ""),
        "managed_by": _org(d), "license": d.get("License"),
        "tags": d.get("Tags") or [], "update_frequency": d.get("UpdateFrequency"),
        "url": f"https://registry.opendata.aws/{d.get('Slug')}/",
    }

def _word(term, text): return re.search(r"\b" + re.escape(term) + r"\b", text) is not None

def _score(name, desc, tags, terms):
    score, matched = 0.0, 0
    for t in terms:
        s = 0.0
        if t in tags: s = 6.0
        elif any(t in g for g in tags): s = 3.0
        if _word(t, name): s = max(s, 5.0)
        elif t in name: s = max(s, 2.5)
        if _word(t, desc): s = max(s, 1.5)
        elif t in desc: s = max(s, 0.5)
        if s: matched += 1; score += s
    return score + matched

def _filters(d, tags=None, organization=None, license_type=None):
    if tags:
        want = [t.strip().lower() for t in (tags.split(",") if isinstance(tags, str) else tags)]
        if not any(w in _tags(d) for w in want): return False
    if organization and organization.lower() not in (d.get("ManagedBy") or "").lower(): return False
    if license_type and not license_matches(d, license_type): return False
    return True

def license_matches(d, license_type):
    lt, txt = license_type.lower(), (d.get("License") or "").lower()
    if lt == "creative commons": return re.search(r"\bcc\b", txt) is not None or "creative commons" in txt
    return lt in txt

def search_datasets(query, tags=None, organization=None, license_type=None, limit=10):
    """Ranked keyword search over name/description/tags plus optional filters."""
    q = query.lower()
    terms = [t for t in re.findall(r"[\w\-\.]+", q) if t not in _STOP] or [q]
    hits = []
    for d in load():
        name, desc, tg = (d.get("Name") or "").lower(), (d.get("Description") or "").lower(), _tags(d)
        if not _filters(d, tags, organization, license_type): continue
        s = _score(name, desc, tg, terms)
        if s > 0: hits.append((s, d))
    hits.sort(key=lambda x: -x[0])
    return {"query": query, "total_count": len(hits),
            "returned_count": min(limit, len(hits)),
            "datasets": [summary(d) | {"score": round(s, 1)} for s, d in hits[:limit]]}

def list_datasets(tag=None, limit=20):
    ds = [d for d in load() if not tag or tag.lower() in _tags(d)]
    return {"tag": tag, "total_count": len(ds), "datasets": [summary(d) for d in ds[:limit]]}

def get_dataset(slug):
    for d in load(include_deprecated=True):
        if d.get("Slug") == slug: return d
    return None

def get_dataset_details(slug):
    """Full record + derived access info. None if not found (then search)."""
    d = get_dataset(slug)
    if not d: return None
    out = dict(d)
    out["registry_url"] = f"https://registry.opendata.aws/{slug}/"
    out["access"] = [access_info(r) for r in d.get("Resources") or []]
    return out

def access_info(r):
    """Derive bucket/prefix/CLI command and access flags for one resource."""
    info = {"type": r.get("Type"), "region": r.get("Region"), "arn": r.get("ARN"),
            "description": r.get("Description"),
            "requester_pays": bool(r.get("RequesterPays")),
            "controlled_access": r.get("ControlledAccess") or None,
            "account_required": bool(r.get("AccountRequired"))}
    arn = r.get("ARN") or ""
    if (r.get("Type") or "").lower() == "s3 bucket" and arn.startswith("arn:aws:s3:::"):
        bucket, _, prefix = arn[len("arn:aws:s3:::"):].partition("/")
        info.update(bucket=bucket, prefix=prefix)
        flag = " --request-payer requester" if info["requester_pays"] else " --no-sign-request"
        info["cli"] = f"aws s3 ls s3://{bucket}/{prefix}{flag} --region {r.get('Region')}"
        info["public"] = not info["requester_pays"] and not info["controlled_access"] and not info["account_required"]
        if info["public"]:
            info["list_url"] = s3_list_url(bucket, r.get("Region"), prefix)
    return info

def s3_list_url(bucket, region, prefix="", max_keys=10, delimiter="/"):
    """Anonymous S3 ListObjectsV2 URL (fetch with url_fetch / download_file)."""
    from urllib.parse import urlencode
    qs = urlencode({"list-type": 2, "max-keys": max_keys, "prefix": prefix, "delimiter": delimiter})
    return f"https://{bucket}.s3.{region or 'us-east-1'}.amazonaws.com/?{qs}"

def parse_s3_listing(xml_text):
    """Parse an S3 ListObjectsV2 XML response into prefixes + objects."""
    from xml.etree import ElementTree as ET
    xml_text = xml_text[xml_text.find("<"):]  # strip any wrapper text
    root = ET.fromstring(xml_text)
    ns = {"s": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}
    p = "s:" if ns else ""
    objs = [{"key": c.findtext(f"{p}Key", namespaces=ns), "size": int(c.findtext(f"{p}Size", "0", ns)),
             "last_modified": c.findtext(f"{p}LastModified", namespaces=ns)}
            for c in root.findall(f"{p}Contents", ns)]
    prefixes = [c.findtext(f"{p}Prefix", namespaces=ns) for c in root.findall(f"{p}CommonPrefixes", ns)]
    return {"prefixes": prefixes, "objects": objs}

def discover_by_organization(organization, limit=10):
    ds = [d for d in load() if organization.lower() in (d.get("ManagedBy") or "").lower()]
    return {"organization": organization, "total_count": len(ds), "datasets": [summary(d) for d in ds[:limit]]}

def discover_by_license(license_type, limit=10):
    if license_type.lower() not in SUPPORTED_LICENSE_TYPES:
        return {"total_count": 0, "hint": f"Supported license types: {SUPPORTED_LICENSE_TYPES}"}
    ds = [d for d in load() if license_matches(d, license_type)]
    return {"license_type": license_type, "total_count": len(ds), "datasets": [summary(d) for d in ds[:limit]]}

def find_related_datasets(slug, limit=5):
    """Rank other datasets by number of shared tags (ties broken by org match)."""
    src = get_dataset(slug)
    if not src: return None
    st, so = set(_tags(src)), _org(src)
    scored = []
    for d in load():
        if d.get("Slug") == slug: continue
        shared = st & set(_tags(d))
        if shared: scored.append((len(shared) + (0.5 if _org(d) == so else 0), sorted(shared), d))
    scored.sort(key=lambda x: -x[0])
    return {"source": summary(src), "related": [summary(d) | {"shared_tags": sh} for _, sh, d in scored[:limit]]}

def get_stats():
    ds = load()
    tags = Counter(t for d in ds for t in _tags(d))
    orgs = Counter(_org(d) for d in ds)
    rtypes = Counter(r.get("Type") for d in ds for r in d.get("Resources") or [])
    lic = {lt: sum(license_matches(d, lt) for d in ds) for lt in SUPPORTED_LICENSE_TYPES}
    return {"total_datasets": len(ds), "deprecated_excluded": len(load(include_deprecated=True)) - len(ds),
            "total_tags": len(tags), "total_organizations": len(orgs),
            "top_tags": tags.most_common(15), "top_organizations": orgs.most_common(10),
            "resource_types": dict(rtypes), "license_types": lic,
            "regions": Counter(r.get("Region") for d in ds for r in d.get("Resources") or []).most_common(10)}

def list_tags(min_count=1):
    return [t for t in Counter(t for d in load() for t in _tags(d)).most_common() if t[1] >= min_count]

def search_stac_endpoints(query=None, limit=20):
    url_re, stac = re.compile(r'https?://[^\s\)\]>"\']+'), re.compile("stac", re.I)
    out = []
    for d in load():
        eps = []
        for r in d.get("Resources") or []:
            for ex in r.get("Explore") or []:
                if stac.search(ex): eps += [{"url": u, "source": "Resource Explore"} for u in url_re.findall(ex)]
            if stac.search(r.get("Description") or ""):
                eps += [{"url": u, "source": "Resource Description"} for u in url_re.findall(r["Description"])]
        for sec in ("Tools & Applications", "Tutorials"):
            for it in (d.get("DataAtWork") or {}).get(sec) or []:
                if it.get("URL") and (stac.search(it.get("Title") or "") or stac.search(it["URL"])):
                    eps.append({"url": it["URL"], "title": it.get("Title"), "source": f"DataAtWork/{sec}"})
        has_tag = any(stac.search(t) for t in _tags(d))
        if not eps and not has_tag: continue
        if query:
            q = query.lower()
            if not (q in (d.get("Name") or "").lower() or q in (d.get("Description") or "").lower()
                    or any(q in t for t in _tags(d))): continue
        seen, uniq = set(), []
        for e in eps:
            if e["url"] not in seen: seen.add(e["url"]); uniq.append(e)
        out.append({"slug": d["Slug"], "name": d["Name"], "managed_by": _org(d), "has_stac_tag": has_tag, "stac_endpoints": uniq})
        if len(out) >= limit: break
    return {"query": query, "count": len(out), "datasets": out}

def to_markdown(result, max_items=10):
    """Render a list-style result as a numbered markdown list (license verbatim)."""
    items = result.get("datasets") or result.get("related") or []
    lines = []
    if "total_count" in result and result["total_count"] > len(items):
        lines.append(f"_Showing {len(items[:max_items])} of {result['total_count']} matching datasets._\n")
    for i, d in enumerate(items[:max_items], 1):
        lines.append(f"{i}. **[{d['name']}]({d['url']})** (`{d['slug']}`)")
        lines.append(f"   - {d['description']}")
        lines.append(f"   - Managed by: {d['managed_by']}")
        lines.append(f"   - License: {d['license']}")
        if d.get("shared_tags"): lines.append(f"   - Shared tags: {', '.join(d['shared_tags'])}")
    return "\n".join(lines)

def preview_bucket(slug, prefix=None, resource_index=0):
    """List up to 10 top-level keys of a PUBLIC bucket (anonymous ListObjectsV2)."""
    from urllib.request import urlopen
    from urllib.error import HTTPError
    det = get_dataset_details(slug)
    if not det: return {"error": f"slug not found: {slug}"}
    s3 = [a for a in det["access"] if a.get("bucket")]
    if not s3: return {"error": "no S3 bucket resources"}
    a = s3[min(resource_index, len(s3) - 1)]
    if not a["public"]:
        return {"error": "not anonymously listable (requester-pays, controlled, or account required)", "cli": a["cli"]}
    url = s3_list_url(a["bucket"], a["region"], prefix if prefix is not None else a["prefix"])
    try:
        with urlopen(url, timeout=30) as r: xml = r.read().decode("utf-8", "replace")
    except HTTPError as e:
        return {"error": f"HTTP {e.code} (bucket likely not anonymously listable)", "cli": a["cli"]}
    return {"bucket": a["bucket"], "region": a["region"], "listing": parse_s3_listing(xml)}

def main(argv=None):
    ap = argparse.ArgumentParser(description="Search the Registry of Open Data on AWS (RODA).")
    ap.add_argument("--index", help="path to index.ndjson (default: $RODA_INDEX or cache)")
    ap.add_argument("--include-deprecated", action="store_true")
    ap.add_argument("--json", action="store_true", help="print raw JSON instead of markdown")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("download", help="download the index to the cache")
    p = sub.add_parser("search"); p.add_argument("query"); p.add_argument("--tags"); p.add_argument("--organization")
    p.add_argument("--license-type"); p.add_argument("--limit", type=int, default=10)
    p = sub.add_parser("list"); p.add_argument("--tag"); p.add_argument("--limit", type=int, default=20)
    p = sub.add_parser("details"); p.add_argument("slug")
    p = sub.add_parser("org"); p.add_argument("organization"); p.add_argument("--limit", type=int, default=10)
    p = sub.add_parser("license"); p.add_argument("license_type"); p.add_argument("--limit", type=int, default=10)
    p = sub.add_parser("related"); p.add_argument("slug"); p.add_argument("--limit", type=int, default=5)
    sub.add_parser("stats")
    p = sub.add_parser("tags"); p.add_argument("--min-count", type=int, default=1)
    p = sub.add_parser("stac"); p.add_argument("--query"); p.add_argument("--limit", type=int, default=20)
    p = sub.add_parser("preview"); p.add_argument("slug"); p.add_argument("--prefix"); p.add_argument("--resource-index", type=int, default=0)
    a = ap.parse_args(argv)
    if a.cmd == "download":
        print(download_index(a.index)); return 0
    load(a.index, include_deprecated=a.include_deprecated)
    if a.cmd == "search": r = search_datasets(a.query, a.tags, a.organization, a.license_type, a.limit)
    elif a.cmd == "list": r = list_datasets(a.tag, a.limit)
    elif a.cmd == "details": r = get_dataset_details(a.slug)
    elif a.cmd == "org": r = discover_by_organization(a.organization, a.limit)
    elif a.cmd == "license": r = discover_by_license(a.license_type, a.limit)
    elif a.cmd == "related": r = find_related_datasets(a.slug, a.limit)
    elif a.cmd == "stats": r = get_stats()
    elif a.cmd == "tags": r = list_tags(a.min_count)
    elif a.cmd == "stac": r = search_stac_endpoints(a.query, a.limit)
    else: r = preview_bucket(a.slug, a.prefix, a.resource_index)
    if r is None:
        print("Not found. Run `search` to find the correct slug.", file=sys.stderr); return 1
    is_list = isinstance(r, dict) and ("datasets" in r or "related" in r) and a.cmd != "stac"
    print(to_markdown(r) if is_list and not a.json else json.dumps(r, indent=2, default=str))
    return 0

if __name__ == "__main__":
    sys.exit(main())
