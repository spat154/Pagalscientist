"""Read-only WordPress access check.

Verifies that the WP_* credentials authenticate and lists recent posts.
Reads everything from the environment — no secrets in this file.

Usage:
    WP_BASE_URL=https://madeinindiamagazine.com.au \
    WP_USERNAME=miim-automation \
    WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx" \
    python3 scripts/wp_check.py

If you see "Host not in allowlist", the environment's network egress policy
has not been updated for THIS session. Start a fresh session after saving the
allowlist (a running session does not pick up the change).
"""
import os
import sys

try:
    import requests
except ImportError:
    sys.exit("Install requests first: pip install requests")

base = os.environ.get("WP_BASE_URL", "").rstrip("/")
user = os.environ.get("WP_USERNAME", "")
pw = os.environ.get("WP_APP_PASSWORD", "").replace(" ", "")  # WP accepts pw without spaces
if not (base and user and pw):
    sys.exit("Set WP_BASE_URL, WP_USERNAME, WP_APP_PASSWORD in the environment.")

s = requests.Session()
s.headers.update({"User-Agent": "MIIM-Engine/0.1 (+content automation)"})


def show(label, r):
    print(f"--- {label}: HTTP {r.status_code} ({len(r.content)} bytes)")


try:
    r = s.get(f"{base}/wp-json", timeout=25)
    show("REST discovery /wp-json", r)
    if r.ok:
        j = r.json()
        print("   site name:", j.get("name"))
        print("   namespaces:", j.get("namespaces", []))
except Exception as e:  # noqa: BLE001
    print("discovery error:", repr(e))

try:
    r = s.get(f"{base}/wp-json/wp/v2/users/me?context=edit", auth=(user, pw), timeout=25)
    show("auth check /users/me", r)
    if r.ok:
        j = r.json()
        print("   authenticated as:", j.get("name"), "| roles:", j.get("roles"))
    else:
        print("   body:", r.text[:300])
except Exception as e:  # noqa: BLE001
    print("auth error:", repr(e))

try:
    r = s.get(f"{base}/wp-json/wp/v2/posts?per_page=5&_fields=id,title,link,date,status",
              auth=(user, pw), timeout=25)
    show("recent posts", r)
    if r.ok:
        for p in r.json():
            title = p.get("title", {}).get("rendered", "")[:70]
            print("   -", p.get("id"), p.get("status"), title)
except Exception as e:  # noqa: BLE001
    print("posts error:", repr(e))
