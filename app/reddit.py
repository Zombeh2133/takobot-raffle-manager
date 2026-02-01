import os
import json
import time
import re
from typing import List, Dict, Any, Tuple, Optional
from zoneinfo import ZoneInfo

def norm_name(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def parse_claim(text: str) -> Tuple[bool, Optional[int]]:
    body = (text or "").strip()
    if not body:
        return (False, 0)

    low = body.strip().lower()

    # NEW: "close" only → keep comment, blank spots
    if re.fullmatch(r"close", low):
        return (True, None)

    # NEW: range syntax like "1-20" (inclusive count)
    range_match = re.search(r"\b(\d+)\s*-\s*(\d+)\b", body)
    if range_match:
        a = int(range_match.group(1))
        b = int(range_match.group(2))
        lo_n = min(a, b)
        hi_n = max(a, b)
        return (True, hi_n - lo_n + 1)

    # TAB rule: "4 tabbed ..."
    tabbed_match = re.search(r"(\d+)\s+tabbed\b", body, re.IGNORECASE)
    if tabbed_match:
        return (True, int(tabbed_match.group(1)))

    # "X spots" rule: "4 spots", "12 spot"
    spots_match = re.search(r"\b(\d+)\s+spots?\b", body, re.IGNORECASE)
    if spots_match:
        return (True, int(spots_match.group(1)))

    # Random count (supports "and 4 more random", "20 rando", "5 randos", etc)
    random_match = re.search(
        r"(\d+)\s*(?:more\s*)?(?:rand(?:om)?s?|rando(?:s)?)\b",
        body,
        re.IGNORECASE
    )
    random_count = int(random_match.group(1)) if random_match else 0

    # All numbers
    numbers = [int(n) for n in re.findall(r"\d+", body)]

    # Remove one occurrence of the random quantity number so it doesn't count as a picked spot
    if random_match:
        rand_qty = int(random_match.group(1))
        if rand_qty in numbers:
            numbers.remove(rand_qty)

    # Single number only (no randoms) -> 1 spot request (spot number)
    if len(numbers) == 1 and random_count == 0:
        return (True, 1)

    # Otherwise: explicit picks + random count
    if numbers or random_count:
        return (True, len(numbers) + random_count)

    return (False, 0)

def to_reddit_json_url(post_url: str) -> str:
    post_url = post_url.strip().split("?")[0].rstrip("/")
    return f"{post_url}.json?limit={REDDIT_LIMIT}&sort=new"

def walk_comment_tree(children: List[Dict[str, Any]], out: List[Dict[str, Any]], depth: int = 0) -> None:
    for child in children or []:
        if not child or child.get("kind") != "t1":
            continue
        d = child.get("data") or {}
        out.append({
            "id": d.get("id", ""),
            "author": d.get("author", "") or "[deleted]",
            "body": d.get("body", "") or "",
            "created_utc": d.get("created_utc", 0),
            "permalink": ("https://www.reddit.com" + d["permalink"]) if d.get("permalink") else "",
            "depth": depth,
        })

        replies = d.get("replies")
        if isinstance(replies, dict):
            rep_children = (replies.get("data") or {}).get("children") or []
            if rep_children:
                walk_comment_tree(rep_children, out, depth + 1)

def fetch_reddit_comments(post_url, session=None):
    """Returns (ok, error_message, flat_comments)."""
    url = to_reddit_json_url(post_url)
    try:
        # If no session is provided, create a new one
        if session is None:
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
            })  # Ensure a legitimate user-agent is used

        # Make the GET request using session
        resp = session.get(url, timeout=25)

        if resp.status_code != 200:
            return (False, f"HTTP {resp.status_code} from Reddit", [])

        data = resp.json()
        children = (((data or [None, None])[1] or {}).get("data") or {}).get("children") or []

        flat: List[Dict[str, Any]] = []
        walk_comment_tree(children, flat, 0)

        return (True, "", flat)

    except Exception as e:
        return (False, f"Fetch/parse error: {e}", [])

def fetch_reddit_comments_simple(post_url: str) -> List[Dict[str, Any]]:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    ok, err, flat = fetch_reddit_comments(post_url, s)
    if not ok:
        raise RuntimeError(err)
    return flat

# =========================
# STATE / MENU
# =========================
def load_state() -> Dict[str, Any]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {
        "reddit_post_url": "",
        "poll_seconds": 180,
        "mode": "append",          # default append
        "seen_ids": [],            # reddit comment ids for polling append dedupe
        "raffle_start_ts": 0,      # unix timestamp (seconds)
        "raffle_end_ts": 0         # unix timestamp (seconds)
    }

def save_state(state: Dict[str, Any]) -> None:
    if "seen_ids" in state and isinstance(state["seen_ids"], list) and len(state["seen_ids"]) > 5000:
        state["seen_ids"] = state["seen_ids"][-5000:]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def run_once(state: Dict[str, Any]) -> None:
    post_url = sanitize_reddit_post_url(state.get("reddit_post_url", ""))
    if not post_url:
        print("❌ No valid Reddit post URL set. Choose option 1 to set it.")
        return

    ws = open_worksheet()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    ok, err, flat = fetch_reddit_comments(post_url, session)
    if not ok:
        print(f"❌ Reddit fetch failed: {err}")
        return

    mode = state.get("mode", "append").lower()

    if mode == "overwrite":
        rows: List[Tuple[str, str, Optional[int]]] = []
        for c in flat:
            body = (c.get("body") or "").strip()
            if not body:
                continue
            if is_host_instructions(body) or is_admin_noise(body):
                continue
            is_claim, spots = parse_claim(body)
            if not is_claim:
                continue
            author = c.get("author") or "[deleted]"
            rows.append((author, body, spots))

        write_snapshot(ws, rows)
        print(f"✅ Wrote snapshot of {len(rows)} claim comments (overwrite).")
        return

    seen = set(state.get("seen_ids", []))
    new_rows: List[Tuple[int, str, str, Optional[int]]] = []

    for c in flat:
        cid = (c.get("id") or "").strip()
        if not cid or cid in seen:
            continue

        body = (c.get("body") or "").strip()
        if not body:
            seen.add(cid)
            continue
        if is_host_instructions(body) or is_admin_noise(body):
            seen.add(cid)
            continue

        is_claim, spots = parse_claim(body)
        if not is_claim:
            seen.add(cid)
            continue

        author = c.get("author") or "[deleted]"
        created = int(c.get("created_utc") or 0)
        new_rows.append((created, author, body, spots))
        seen.add(cid)

    if new_rows:
        new_rows.sort(key=lambda x: x[0], reverse=True)  # newest first
        prepend_new(ws, new_rows)
        state["seen_ids"] = list(seen)
        save_state(state)
        print(f"✅ Prepended {len(new_rows)} new claim comments (append mode).")
    else:
        print("✅ No new claim comments to add (append mode).")

def start_polling(state: Dict[str, Any]) -> None:
    post_url = sanitize_reddit_post_url(state.get("reddit_post_url", ""))
    if not post_url:
        print("❌ No valid Reddit post URL set. Choose option 1 to set it.")
        return

    poll_seconds = int(state.get("poll_seconds", 180))
    mode = state.get("mode", "append").lower()

    ws = open_worksheet()

    backoff = 5
    max_backoff = 600

    print(f"▶ Polling started. Mode={mode}, every {poll_seconds}s. Ctrl+C to stop.\n")

    try:
        while True:
            ok, err, flat = fetch_reddit_comments(post_url, session)

            if not ok:
                if "HTTP 429" in err:
                    print(f"[Reddit] {err}. Backing off {backoff}s...")
                    time.sleep(backoff)
                    backoff = min(max_backoff, backoff * 2)
                else:
                    print(f"[Reddit] {err}. Retrying in {poll_seconds}s...")
                    time.sleep(poll_seconds)
                continue

            backoff = 5

            if mode == "overwrite":
                rows: List[Tuple[str, str, Optional[int]]] = []
                for c in flat:
                    body = (c.get("body") or "").strip()
                    if not body:
                        continue
                    if is_host_instructions(body) or is_admin_noise(body):
                        continue
                    is_claim, spots = parse_claim(body)
                    if not is_claim:
                        continue
                    author = c.get("author") or "[deleted]"
                    rows.append((author, body, spots))

                write_snapshot(ws, rows)
                print(f"[Sheet] Snapshot wrote {len(rows)} claim comment(s).")

            else:
                seen = set(state.get("seen_ids", []))
                new_rows: List[Tuple[int, str, str, Optional[int]]] = []

                for c in flat:
                    cid = (c.get("id") or "").strip()
                    if not cid or cid in seen:
                        continue

                    body = (c.get("body") or "").strip()
                    if not body:
                        seen.add(cid)
                        continue
                    if is_host_instructions(body) or is_admin_noise(body):
                        seen.add(cid)
                        continue

                    is_claim, spots = parse_claim(body)
                    if not is_claim:
                        seen.add(cid)
                        continue

                    author = c.get("author") or "[deleted]"
                    created = int(c.get("created_utc") or 0)
                    new_rows.append((created, author, body, spots))
                    seen.add(cid)

                if new_rows:
                    new_rows.sort(key=lambda x: x[0], reverse=True)  # newest first at top
                    prepend_new(ws, new_rows)
                    state["seen_ids"] = list(seen)
                    save_state(state)
                    print(f"[Sheet] Prepended {len(new_rows)} new claim comment(s).")
                else:
                    print("[Sheet] No new claim comments.")

            time.sleep(poll_seconds)

    except KeyboardInterrupt:
        print("\n⏹ Polling stopped.")

def _fmt_ts(ts: int) -> str:
    if not ts:
        return "(not set)"
    try:
        dt = datetime.fromtimestamp(int(ts), tz=EASTERN)
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    except:
        return str(ts)

def start_raffle_window(state: Dict[str, Any]) -> None:
    now = int(time.time())
    state["raffle_start_ts"] = now
    state["raffle_end_ts"] = 0
    save_state(state)
    print(f"✅ Raffle email window START set to: {_fmt_ts(now)}")

def end_raffle_window(state: Dict[str, Any]) -> None:
    start_ts = int(state.get("raffle_start_ts") or 0)
    if not start_ts:
        print("❌ No raffle window start set. Use option 10 first.")
        return
    now = int(time.time())
    state["raffle_end_ts"] = now
    save_state(state)
    print(f"✅ Raffle email window END set to: {_fmt_ts(now)}")

def menu():
    state = load_state()

    while True:
        print("\n==============================")
        print(" Raffle Reddit → Google Sheet ")
        print("==============================")
        print(f"Sheet Tab: {WORKSHEET_NAME}")
        print(f"Post URL : {state.get('reddit_post_url') or '(not set)'}")
        print(f"Mode     : {state.get('mode', 'append')}")
        print(f"Poll     : {state.get('poll_seconds', 180)} seconds")
        print(f"EmailWin : start={_fmt_ts(int(state.get('raffle_start_ts') or 0))} | end={_fmt_ts(int(state.get('raffle_end_ts') or 0))}")
        print("------------------------------")
        print("1) Set Reddit post link")
        print("2) Set mode (overwrite / append)")
        print("3) Set polling interval seconds")
        print("4) Run once now")
        print("5) Start polling")
        print("6) Clear seen IDs (append mode)")
        print("7) Import PayPal CSV and mark Paid (file picker)")
        print("8) Scan PayPal Gmail label TODAY (EST preview matches only)  [uses WINDOW if set]")
        print("9) Scan PayPal Gmail label TODAY (EST MARK PAID in H)        [uses WINDOW if set]")
        print("10) Start raffle email window (sets start time = now)")
        print("11) End raffle email window (sets end time = now)")
        print("0) Quit")
        choice = input("Choose: ").strip()

        if choice == "1":
            url = input("Paste Reddit post URL: ").strip()
            clean = sanitize_reddit_post_url(url)
            if not clean:
                print("❌ Invalid Reddit post URL (must be a /comments/ link).")
            else:
                state["reddit_post_url"] = clean
                save_state(state)
                print("✅ Saved.")

        elif choice == "2":
            m = input("Mode (overwrite/append): ").strip().lower()
            if m not in ("overwrite", "append"):
                print("❌ Must be overwrite or append.")
            else:
                state["mode"] = m
                save_state(state)
                print("✅ Saved.")

        elif choice == "3":
            s = input("Polling seconds (e.g. 120, 180, 300): ").strip()
            try:
                n = int(s)
                if n < 30:
                    print("❌ Too low. Use 30+ seconds (recommended 120+).")
                else:
                    state["poll_seconds"] = n
                    save_state(state)
                    print("✅ Saved.")
            except:
                print("❌ Not a number.")

        elif choice == "4":
            run_once(state)

        elif choice == "5":
            start_polling(state)

        elif choice == "6":
            state["seen_ids"] = []
            save_state(state)
            print("✅ Cleared seen IDs.")

        elif choice == "7":
            ws = open_worksheet()
            csv_path = pick_csv_file()
            if not csv_path:
                print("❌ No file selected.")
            else:
                import_paypal_csv(ws, csv_path)

        elif choice == "8":
            scan_paypal_emails_today_or_window(state, mark_paid=False)

        elif choice == "9":
            scan_paypal_emails_today_or_window(state, mark_paid=True)

        elif choice == "10":
            start_raffle_window(state)

        elif choice == "11":
            end_raffle_window(state)

        elif choice == "0":
            print("Bye.")
            return

        else:
            print("❌ Invalid choice.")

if __name__ == "__main__":
    menu()
