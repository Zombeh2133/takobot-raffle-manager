import sys
import json
import re
import requests
import random
import time
from typing import List, Dict, Any, Tuple, Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file if it exists
except ImportError:
    pass  # python-dotenv not installed, will use system environment variables

# Rotating User Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
]

# Updated Proxy List - NEW PROXIES (Format: IP:PORT:USERNAME:PASSWORD converted to requests format)
PROXIES = [
    None,  # Try without proxy first
    {"http": "http://zivSw:sl9AvAK9@137.155.106.87:11717", "https": "http://zivSw:sl9AvAK9@137.155.106.87:11717"},
    {"http": "http://zivSw:sl9AvAK9@137.155.106.88:11718", "https": "http://zivSw:sl9AvAK9@137.155.106.88:11718"},
    {"http": "http://zivSw:sl9AvAK9@137.155.106.89:11719", "https": "http://zivSw:sl9AvAK9@137.155.106.89:11719"},
    {"http": "http://zivSw:sl9AvAK9@137.155.106.90:11720", "https": "http://zivSw:sl9AvAK9@137.155.106.90:11720"},
    {"http": "http://zivSw:sl9AvAK9@137.155.106.91:11721", "https": "http://zivSw:sl9AvAK9@137.155.106.91:11721"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.182:11047", "https": "http://zivSw:sl9AvAK9@137.155.103.182:11047"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.183:11048", "https": "http://zivSw:sl9AvAK9@137.155.103.183:11048"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.184:11049", "https": "http://zivSw:sl9AvAK9@137.155.103.184:11049"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.185:11050", "https": "http://zivSw:sl9AvAK9@137.155.103.185:11050"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.186:11051", "https": "http://zivSw:sl9AvAK9@137.155.103.186:11051"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.187:11052", "https": "http://zivSw:sl9AvAK9@137.155.103.187:11052"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.188:11053", "https": "http://zivSw:sl9AvAK9@137.155.103.188:11053"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.189:11054", "https": "http://zivSw:sl9AvAK9@137.155.103.189:11054"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.190:11055", "https": "http://zivSw:sl9AvAK9@137.155.103.190:11055"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.191:11056", "https": "http://zivSw:sl9AvAK9@137.155.103.191:11056"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.192:11057", "https": "http://zivSw:sl9AvAK9@137.155.103.192:11057"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.193:11058", "https": "http://zivSw:sl9AvAK9@137.155.103.193:11058"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.194:11059", "https": "http://zivSw:sl9AvAK9@137.155.103.194:11059"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.195:11060", "https": "http://zivSw:sl9AvAK9@137.155.103.195:11060"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.196:11061", "https": "http://zivSw:sl9AvAK9@137.155.103.196:11061"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.197:11062", "https": "http://zivSw:sl9AvAK9@137.155.103.197:11062"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.198:11063", "https": "http://zivSw:sl9AvAK9@137.155.103.198:11063"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.199:11064", "https": "http://zivSw:sl9AvAK9@137.155.103.199:11064"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.200:11065", "https": "http://zivSw:sl9AvAK9@137.155.103.200:11065"},
    {"http": "http://zivSw:sl9AvAK9@137.155.103.201:11066", "https": "http://zivSw:sl9AvAK9@137.155.103.201:11066"},
    {"http": "http://zivSw:sl9AvAK9@137.155.106.39:7589", "https": "http://zivSw:sl9AvAK9@137.155.106.39:7589"},
    {"http": "http://zivSw:sl9AvAK9@137.155.106.40:7590", "https": "http://zivSw:sl9AvAK9@137.155.106.40:7590"},
    {"http": "http://zivSw:sl9AvAK9@137.155.106.41:7591", "https": "http://zivSw:sl9AvAK9@137.155.106.41:7591"},
    {"http": "http://zivSw:sl9AvAK9@137.155.106.42:7592", "https": "http://zivSw:sl9AvAK9@137.155.106.42:7592"},
    {"http": "http://zivSw:sl9AvAK9@137.155.106.43:7593", "https": "http://zivSw:sl9AvAK9@137.155.106.43:7593"},
    {"http": "http://zivSw:sl9AvAK9@137.155.106.239:7789", "https": "http://zivSw:sl9AvAK9@137.155.106.239:7789"},
    {"http": "http://zivSw:sl9AvAK9@137.155.106.240:7790", "https": "http://zivSw:sl9AvAK9@137.155.106.240:7790"},
    {"http": "http://zivSw:sl9AvAK9@137.155.106.241:7791", "https": "http://zivSw:sl9AvAK9@137.155.106.241:7791"},
    {"http": "http://zivSw:sl9AvAK9@137.155.106.242:7792", "https": "http://zivSw:sl9AvAK9@137.155.106.242:7792"},
    {"http": "http://zivSw:sl9AvAK9@137.155.106.243:7793", "https": "http://zivSw:sl9AvAK9@137.155.106.243:7793"},
    {"http": "http://zivSw:sl9AvAK9@137.155.110.242:12892", "https": "http://zivSw:sl9AvAK9@137.155.110.242:12892"},
    {"http": "http://zivSw:sl9AvAK9@137.155.110.243:12893", "https": "http://zivSw:sl9AvAK9@137.155.110.243:12893"},
    {"http": "http://zivSw:sl9AvAK9@137.155.110.244:12894", "https": "http://zivSw:sl9AvAK9@137.155.110.244:12894"},
    {"http": "http://zivSw:sl9AvAK9@137.155.110.245:12895", "https": "http://zivSw:sl9AvAK9@137.155.110.245:12895"},
    {"http": "http://zivSw:sl9AvAK9@137.155.110.246:12896", "https": "http://zivSw:sl9AvAK9@137.155.110.246:12896"},
    {"http": "http://zivSw:sl9AvAK9@137.155.110.247:12897", "https": "http://zivSw:sl9AvAK9@137.155.110.247:12897"},
    {"http": "http://zivSw:sl9AvAK9@137.155.110.248:12898", "https": "http://zivSw:sl9AvAK9@137.155.110.248:12898"},
    {"http": "http://zivSw:sl9AvAK9@137.155.110.249:12899", "https": "http://zivSw:sl9AvAK9@137.155.110.249:12899"},
    {"http": "http://zivSw:sl9AvAK9@137.155.110.250:12900", "https": "http://zivSw:sl9AvAK9@137.155.110.250:12900"},
    {"http": "http://zivSw:sl9AvAK9@137.155.110.251:12901", "https": "http://zivSw:sl9AvAK9@137.155.110.251:12901"},
    {"http": "http://zivSw:sl9AvAK9@137.155.110.252:12902", "https": "http://zivSw:sl9AvAK9@137.155.110.252:12902"},
    {"http": "http://zivSw:sl9AvAK9@137.155.110.253:12903", "https": "http://zivSw:sl9AvAK9@137.155.110.253:12903"},
    {"http": "http://zivSw:sl9AvAK9@137.155.110.254:12904", "https": "http://zivSw:sl9AvAK9@137.155.110.254:12904"},
    {"http": "http://zivSw:sl9AvAK9@137.155.110.255:12905", "https": "http://zivSw:sl9AvAK9@137.155.110.255:12905"},
    {"http": "http://zivSw:sl9AvAK9@137.155.107.192:12077", "https": "http://zivSw:sl9AvAK9@137.155.107.192:12077"},
]

def get_random_user_agent():
    """Get a random user agent"""
    return random.choice(USER_AGENTS)

def clean_comment_text(text: str) -> str:
    """Remove URLs, images, and other non-text content from comment"""
    if not text:
        return ""

    # Remove URLs (http, https, www)
    text = re.sub(r'https?://[^\s]+', '', text)
    text = re.sub(r'www\.[^\s]+', '', text)

    # Remove markdown image syntax ![alt](url)
    text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', text)

    # Remove markdown link syntax [text](url) - keep the text part
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    # Remove image file extensions
    text = re.sub(r'\S+\.(jpg|jpeg|png|gif|webp|svg|bmp)\b', '', text, flags=re.IGNORECASE)

    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    return text

def parse_host_reply(reply_text: str) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """
    Parse host's reply to extract spot count and beneficiary username

    Returns: (status, spot_count, beneficiary_username)
    - status: "confirmed", "waitlist", "removed", or None
    - spot_count: number of spots assigned (count of numbers in "You got X, Y, Z")
    - beneficiary_username: username mentioned in "u/username got X, Y, Z" format, or None
    """
    if not reply_text:
        return (None, None, None)

    # Strip whitespace from the original text so indices match
    reply_text = reply_text.strip()
    reply_lower = reply_text.lower()

    # Check for waitlist
    if "waitlist starts here" in reply_lower:
        return ("waitlist", 0, None)

    # CHECK 1: Proxy/mention format: "u/username got X, Y, Z" or "/u/username got X, Y, Z"
    # This handles: proxy requests, host self-replies, etc.
    proxy_match = re.search(r'/?u/(\w+)\s+got', reply_text, re.IGNORECASE)
    if proxy_match:
        beneficiary_username = proxy_match.group(1)
        
        # Extract spot numbers from the part AFTER "got"
        got_index = reply_lower.find("got", proxy_match.start())
        from_got = reply_text[got_index:]
        
        # Split at newline or common delimiters
        spot_section = from_got.split('\n')[0]
        for delimiter in ["Please", "please", "Follow", "follow", "GL", "Gl", "Good luck", "good luck", "GLGL", "glgl"]:
            if delimiter in spot_section:
                spot_section = spot_section.split(delimiter)[0]
                break
        
        # Skip "got" text and extract numbers
        after_got = spot_section[3:].strip()  # "got" is 3 characters
        numbers = re.findall(r'\b\d+\b', after_got)
        
        if numbers:
            spot_count = len(numbers)
            return ("confirmed", spot_count, beneficiary_username)
        
        return (None, None, None)

    # CHECK 2: Regular format "You got" - beneficiary is the comment author
    if "you got" not in reply_lower:
        return (None, None, None)

    # ✅ WORKAROUND: Handle multiple "You got" occurrences (e.g., "You got the last two. GL.\nYou got 8, 20")
    # Split by newlines and find the "You got" line with actual spot numbers
    lines = reply_text.split('\n')
    best_match = None
    best_spot_count = 0
    
    for line in lines:
        line_lower = line.lower()
        if "you got" not in line_lower:
            continue
        
        # Find "you got" in this line
        you_got_index = line_lower.find("you got")
        if you_got_index == -1:
            continue
        
        # Extract from "You got" onwards in this line
        from_you_got = line[you_got_index:]
        
        # Stop at common delimiters
        spot_section = from_you_got
        for delimiter in ["Please", "please", "Follow", "follow", "GL", "Gl", "Good luck", "good luck", "GLGL", "glgl"]:
            if delimiter in spot_section:
                spot_section = spot_section.split(delimiter)[0]
                break
        
        # Extract numbers after "you got"
        you_got_phrase = "you got"
        after_you_got = spot_section[len(you_got_phrase):].strip()
        numbers = re.findall(r'\b\d+\b', after_you_got)
        
        # Keep the match with the most numbers (actual spot assignments vs text like "the last two")
        if numbers and len(numbers) > best_spot_count:
            best_spot_count = len(numbers)
            best_match = numbers
    
    if best_match:
        return ("confirmed", best_spot_count, None)  # None = use comment author

    return (None, None, None)

def walk_comment_tree(children: List[Dict[str, Any]], out: List[Dict[str, Any]], depth: int = 0, op_author: Optional[str] = None):
    """Recursively walk Reddit comment tree"""
    for child in children or []:
        if not child or child.get("kind") != "t1":
            continue
        d = child.get("data") or {}

        # Collect OP replies for spot confirmation
        op_replies = []
        # ✅ NEW: Also collect ALL replies (for removal detection)
        all_replies = []
        replies = d.get("replies")
        if isinstance(replies, dict):
            rep_children = (replies.get("data") or {}).get("children") or []
            for rep_child in rep_children:
                if rep_child and rep_child.get("kind") == "t1":
                    rep_data = rep_child.get("data") or {}
                    reply_author = rep_data.get("author", "")

                    # Store ALL replies for removal detection
                    all_replies.append({
                        "author": reply_author,
                        "body": rep_data.get("body", ""),
                        "is_submitter": rep_data.get("is_submitter", False)
                    })

                    # Check if this reply is from OP - check BOTH is_submitter flag AND author match
                    is_from_op = rep_data.get("is_submitter", False) or (op_author and reply_author.lower() == op_author.lower())

                    if is_from_op:
                        op_replies.append({
                            "author": reply_author,
                            "body": rep_data.get("body", ""),
                            "is_submitter": True
                        })

        out.append({
            "id": d.get("id", ""),
            "author": d.get("author", "") or "[deleted]",
            "body": d.get("body", "") or "",
            "created_utc": d.get("created_utc", 0),
            "permalink": ("https://www.reddit.com" + d["permalink"]) if d.get("permalink") else "",
            "depth": depth,
            "op_replies": op_replies,  # Store OP replies for parsing
            "all_replies": all_replies,  # Store ALL replies for removal detection
            "is_submitter": d.get("is_submitter", False),  # Is this comment from the post author (OP)?
            "parent_id": d.get("parent_id", ""),  # Parent comment ID for threading
        })

        if isinstance(replies, dict):
            if rep_children:
                walk_comment_tree(rep_children, out, depth + 1, op_author)


def fetch_reddit_comments(post_url: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Fetch and parse Reddit comments with proxy rotation - returns (comments, OP_username)"""
    # Convert to JSON API URL
    post_url = post_url.strip().split("?")[0].rstrip("/")
    json_url = f"{post_url}.json?limit=1000&sort=new"

    # Shuffle proxies for random order
    proxies_to_try = PROXIES.copy()
    random.shuffle(proxies_to_try)

    last_error = None

    # Try each proxy
    for proxy in proxies_to_try:
        try:
            session = requests.Session()

            # Random user agent for each attempt
            session.headers.update({
                "User-Agent": get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            })

            # Make request with 60 second timeout (increased from 20)
            resp = session.get(json_url, proxies=proxy, timeout=60)

            # Check status code
            if resp.status_code == 403:
                last_error = "Reddit blocked the request (403). Trying next proxy..."
                continue
            elif resp.status_code == 429:
                last_error = "Rate limit (429). Trying next proxy..."
                time.sleep(1)  # Brief pause before next attempt
                continue
            elif resp.status_code != 200:
                last_error = f"HTTP {resp.status_code}"
                continue

            # Try to parse JSON
            try:
                data = resp.json()
            except json.JSONDecodeError:
                last_error = "Invalid JSON response (possible CAPTCHA)"
                continue

            # Extract comments
            if not isinstance(data, list) or len(data) < 2:
                last_error = "Unexpected API response format"
                continue

            # Extract OP (Original Poster) from post data
            op_author = None
            try:
                post_data = data[0].get("data", {}).get("children", [{}])[0].get("data", {})
                op_author = post_data.get("author", None)
                if op_author:
                    print(f"📝 Detected OP (host): u/{op_author}", file=sys.stderr)
            except (IndexError, KeyError, AttributeError):
                pass  # If we can't get OP, we'll continue without filtering

            children = (((data or [None, None])[1] or {}).get("data") or {}).get("children") or []

            flat = []
            walk_comment_tree(children, flat, 0, op_author)

            if len(flat) == 0:
                raise Exception("No comments found. Post may be empty or private.")

            # Success!
            return flat, op_author

        except requests.exceptions.Timeout:
            last_error = f"Request timed out with proxy: {proxy}"
            continue
        except requests.exceptions.RequestException as e:
            last_error = f"Request error: {str(e)}"
            continue
        except Exception as e:
            last_error = f"Error: {str(e)}"
            continue

    # All proxies failed
    raise Exception(f"Failed to fetch Reddit comments after trying all proxies. Last error: {last_error}")


def is_bot_confirmation(text: str) -> bool:
    """Check if comment is a bot confirmation message (like 'You got 13, 26...')"""
    if not text:
        return False

    text_lower = text.lower().strip()

    # Common bot confirmation patterns
    bot_patterns = [
        r'^you got',                    # "You got 13, 26, 44"
        r'^/u/\w+ got',                 # "/u/username got 5, 12"
        r'^u/\w+ got',                  # "u/username got 5, 12"
        r'you have been assigned',      # "You have been assigned spots..."
        r'slot assignment confirmation', # Bot confirmation headers
        r'your spots are:',             # "Your spots are: 1, 5, 12"
        r'assigned spots:',             # "Assigned spots: 1, 5, 12"
    ]

    for pattern in bot_patterns:
        if re.search(pattern, text_lower):
            return True

    return False

def is_host_bot_reply(author: str, body: str) -> bool:
    """Check if comment is from host/bot (spot assignments, announcements, etc.)"""
    if not author or not body:
        return False

    author_lower = author.lower().strip()
    body_lower = body.lower().strip()

    # Filter out common host/bot usernames
    host_bot_usernames = [
        'theextrabutthole',
        'takobot',
        'rafflebot',
        'pokemonrafflebot',
        'automoderator'
    ]

    if author_lower in host_bot_usernames:
        return True

    # Filter out bot reply patterns - REMOVED "you got" since we need those for parsing!
    bot_reply_patterns = [
        'congrats!',
        'gl\r\n',
        'glgl\r\n',
        'goodluck!\r\n',
        'good luck!',
        'added',
        '[announcement]',
        'please follow these instructions',
        'payment received',
        'paid - thank',
        'spots confirmed',
    ]

    for pattern in bot_reply_patterns:
        if pattern in body_lower:
            return True

    # Filter out standalone short responses (likely host acknowledgments)
    if body_lower in ['gl', 'glgl', 'ty', 'thanks', 'thank you', 'congrats']:
        return True

    return False

def is_tab_request(text: str) -> bool:
    """Check if comment is a tab/retab request"""
    if not text:
        return False

    text_lower = text.lower().strip()

    # Check for tab-related keywords
    tab_patterns = [
        r'\btab\b',       # standalone "tab"
        r'\btabbed\b',    # "tabbed"
        r'\bretab\b',     # "retab"
    ]

    for pattern in tab_patterns:
        if re.search(pattern, text_lower):
            return True

    return False

def is_removal_reply(reply_text: str, comment_author: str) -> bool:
    """
    Check if host reply indicates user removal (unpaid/removed)
    
    Patterns:
    1. Host posts: "Attention unpaid participants: your unpaid slots have been removed due to lack of payment."
       Then replies: "u/username" (just the username)
    2. Reply contains removal keywords + username mention
    
    ⚠️ CRITICAL: This should ONLY match actual removals, NOT confirmations that mention "removed" in instructions
    """
    if not reply_text:
        return False
    
    reply_lower = reply_text.lower().strip()
    
    # ✅ SAFETY CHECK: If reply contains spot assignment, it's NOT a removal
    # This prevents false positives like "You got 13, 26. Pay within 30 mins or slots will be removed"
    if "you got" in reply_lower or re.search(r'/?u/\w+\s+got', reply_lower):
        return False
    
    # Pattern 1: Reply is JUST a username mention (with optional /u/ prefix)
    # Example: "u/dfresh1518" or "/u/dfresh1518"
    username_only_pattern = r'^/?u/\w+$'
    if re.match(username_only_pattern, reply_lower):
        return True
    
    # Pattern 2: Reply contains removal keywords
    removal_keywords = [
        'removed',
        'unpaid',
        'slots have been removed',
        'have been removed',
        'slot has been removed',
        'due to lack of payment',
        'did not pay'
    ]
    
    for keyword in removal_keywords:
        if keyword in reply_lower:
            return True
    
    return False

def validate_parse_results(participants: List[Dict[str, Any]], total_spots: Optional[int]) -> List[Dict[str, Any]]:
    """Validate parsed results and flag potential errors for review"""
    if not participants:
        return participants

    validation_flags = []

    # CHECK 1: Calculate total assigned spots
    total_assigned = sum(p.get("spots", 0) for p in participants)

    if total_spots and total_assigned > total_spots:
        validation_flags.append({
            "type": "over_assigned",
            "message": f"⚠️ VALIDATION: Total assigned spots ({total_assigned}) exceeds limit ({total_spots})"
        })
        print(f"⚠️ VALIDATION: Total assigned spots ({total_assigned}) exceeds limit ({total_spots})", file=sys.stderr)

    # CHECK 2: Flag unusually high spot counts
    HIGH_SPOT_THRESHOLD = 25  # Configurable threshold
    for p in participants:
        spot_count = p.get("spots", 0)
        if spot_count > HIGH_SPOT_THRESHOLD:
            validation_flags.append({
                "type": "high_spot_count",
                "user": p.get("redditUser", "unknown"),
                "spots": spot_count,
                "comment": p.get("comment", "")[:60]
            })
            print(f"⚠️ VALIDATION: u/{p.get('redditUser')} requested {spot_count} spots (>{HIGH_SPOT_THRESHOLD}) - Comment: \"{p.get('comment', '')[:60]}...\"", file=sys.stderr)

    # CHECK 3: Invalid spot counts (negative)
    for i, p in enumerate(participants):
        spots = p.get("spots", 0)

        # Negative spots should never happen
        if spots < 0:
            validation_flags.append({
                "type": "negative_spots",
                "user": p.get("redditUser", "unknown"),
                "spots": spots
            })
            print(f"⚠️ VALIDATION: u/{p.get('redditUser')} has NEGATIVE spots ({spots}) - setting to 0", file=sys.stderr)
            participants[i]["spots"] = 0
            participants[i]["owed"] = 0

    # CHECK 4: Sanity check - spot count shouldn't exceed total raffle spots
    if total_spots:
        for p in participants:
            spots = p.get("spots", 0)
            if spots > total_spots:
                validation_flags.append({
                    "type": "exceeds_total",
                    "user": p.get("redditUser", "unknown"),
                    "spots": spots,
                    "total": total_spots
                })
                print(f"⚠️ VALIDATION: u/{p.get('redditUser')} requested {spots} spots but raffle only has {total_spots} total - may be a parsing error", file=sys.stderr)

    # Print summary
    if validation_flags:
        print(f"\n🔍 VALIDATION SUMMARY: Found {len(validation_flags)} potential issues", file=sys.stderr)
    else:
        print(f"\n✅ VALIDATION: All checks passed!", file=sys.stderr)

    return participants

def parse_reddit_post(post_url: str, cost_per_spot: float, total_spots: Optional[int] = None, existing_comment_ids: Optional[List[str]] = None, current_assigned_spots: int = 0, pending_tab_comment_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Main function to parse Reddit post and extract participants

    Args:
        post_url: Reddit post URL
        cost_per_spot: Cost per spot
        total_spots: Optional total spots limit
        existing_comment_ids: Comment IDs to skip (already processed with confirmed/waitlist status)
        current_assigned_spots: Number of spots already assigned
        pending_tab_comment_ids: Comment IDs with tab_pending status that should be re-scanned for host replies
    """
    comments, op_author = fetch_reddit_comments(post_url)
    participants = []

    # ============ PHASE 1: Detect removals from host announcement ============
    # ✅ ALWAYS scan for removal announcements (independent of raffle fill status)
    # ✅ Scan ALL comments BEFORE filtering (removal announcements might be in already-processed comments)
    removed_users = set()
    
    print(f"🔍 Scanning for unpaid participant removal announcements...", file=sys.stderr)
    
    for comment in comments:
        author = comment.get("author", "")
        body = comment.get("body", "")
        all_replies = comment.get("all_replies", [])  # ✅ Use all_replies instead of op_replies
        
        # Check if this is the host's removal announcement
        if author and author.lower() == (op_author.lower() if op_author else ""):
            body_lower = body.lower().strip()
            
            # Pattern 1: Standard removal announcement
            if "attention unpaid participants" in body_lower and "your unpaid slots have been removed due to lack of payment" in body_lower:
                print(f"🚨 Found removal announcement from u/{author}", file=sys.stderr)
                
                # Check ALL replies to this announcement for usernames (not just OP replies)
                for reply in all_replies:
                    reply_author = reply.get("author", "")
                    reply_body = reply.get("body", "").strip()
                    
                    # Only process replies from the host
                    if reply_author.lower() == op_author.lower():
                        # Check if reply is just a username mention
                        username_match = re.match(r'^/?u/(\w+)$', reply_body, re.IGNORECASE)
                        if username_match:
                            removed_username = username_match.group(1)
                            removed_users.add(removed_username.lower())
                            print(f"🚫 Marked u/{removed_username} for removal (found in announcement replies)", file=sys.stderr)
            
            # Pattern 2: Alternative removal phrases
            elif any(phrase in body_lower for phrase in [
                "unpaid slots have been removed",
                "slots have been removed due to lack of payment",
                "removed due to non-payment",
                "removed for non-payment"
            ]):
                print(f"🚨 Found removal announcement (alt format) from u/{author}", file=sys.stderr)
                
                # Check ALL replies for usernames
                for reply in all_replies:
                    reply_author = reply.get("author", "")
                    reply_body = reply.get("body", "").strip()
                    
                    if reply_author.lower() == op_author.lower():
                        username_match = re.match(r'^/?u/(\w+)$', reply_body, re.IGNORECASE)
                        if username_match:
                            removed_username = username_match.group(1)
                            removed_users.add(removed_username.lower())
                            print(f"🚫 Marked u/{removed_username} for removal (alt format)", file=sys.stderr)
    
    if removed_users:
        print(f"📊 Found {len(removed_users)} users marked for removal: {', '.join(sorted(removed_users))}", file=sys.stderr)
    else:
        print(f"📊 No removal announcements found", file=sys.stderr)

    # Convert pending_tab_comment_ids to set for fast lookup
    pending_tab_ids = set(pending_tab_comment_ids) if pending_tab_comment_ids else set()

    # ✅ Filter out already-processed comments BEFORE parsing
    # BUT keep comments that have tab_pending status (need to re-scan for host replies)
    if existing_comment_ids:
        existing_ids_set = set(existing_comment_ids)
        original_count = len(comments)
        # Filter out comments that are fully processed (confirmed/waitlist), but KEEP tab_pending ones
        comments = [c for c in comments if c.get('id') not in existing_ids_set or c.get('id') in pending_tab_ids]
        filtered_count = original_count - len(comments)
        print(f"✅ Filtered out {filtered_count} already-processed comments. Keeping {len(pending_tab_ids)} tab_pending comments for re-scan. {len(comments)} total comments to parse.", file=sys.stderr)

    # ============ PHASE 2: Parse participant comments ============
    for i, comment in enumerate(comments):
        author = comment.get("author", "")
        body = comment.get("body", "")
        op_replies = comment.get("op_replies", [])
        created_utc = comment.get("created_utc", 0)
        comment_id = comment.get("id", "")

        # Skip deleted/removed comments and AutoModerator
        if not author or author in ["[deleted]", "[removed]", "AutoModerator"]:
            continue

        # Skip bot confirmation messages (includes "You got" spot assignments from host)
        if is_bot_confirmation(body):
            continue

        # Skip host/bot replies
        if is_host_bot_reply(author, body):
            continue

        # Skip comments that contain ONLY links/images (no actual text content)
        cleaned_for_check = clean_comment_text(body)
        if not cleaned_for_check or len(cleaned_for_check.strip()) == 0:
            continue

        # ============ PARSING LOGIC: Parse from HOST REPLY ============
        # Look for OP's reply to this comment
        host_status = None
        spot_count = None
        beneficiary_username = None
        
        # ✅ NEW: Track if we need to create multiple participants from one reply
        # (e.g., "You got 1,2,3 u/username got 4,5,6")
        participants_to_add = []

        if op_replies:
            # Check each OP reply
            for op_reply in op_replies:
                reply_body = op_reply.get("body", "")
                
                # Parse for spot assignment
                status, spots, beneficiary = parse_host_reply(reply_body)

                if status:
                    # ✅ SPECIAL CASE: Check if reply contains BOTH "You got" AND "u/username got"
                    # Example: "You got 1,2,3 u/username got 200"
                    reply_lower = reply_body.lower()
                    has_you_got = "you got" in reply_lower
                    has_proxy_got = re.search(r'/?u/(\w+)\s+got', reply_body, re.IGNORECASE)
                    
                    if has_you_got and has_proxy_got:
                        # This reply assigns spots to BOTH comment author AND proxy user
                        print(f"🔄 Found DUAL assignment in one reply for u/{author}", file=sys.stderr)
                        
                        # Parse "You got" for comment author - manually extract to avoid parse_host_reply confusion
                        you_got_index = reply_lower.find("you got")
                        from_you_got = reply_body[you_got_index:]
                        
                        # Find where the proxy assignment starts (if exists)
                        proxy_got_match = re.search(r'/?u/\w+\s+got', from_you_got, re.IGNORECASE)
                        if proxy_got_match:
                            # Extract only the "You got" section (before proxy assignment)
                            you_section = from_you_got[:proxy_got_match.start()]
                        else:
                            you_section = from_you_got
                        
                        # Split at newline or common delimiters
                        you_section = you_section.split('\n')[0]
                        for delimiter in ["Please", "please", "Follow", "follow", "GL", "Gl", "Good luck", "good luck", "GLGL", "glgl"]:
                            if delimiter in you_section:
                                you_section = you_section.split(delimiter)[0]
                                break
                        
                        # Extract numbers from "You got" section
                        you_got_phrase = "you got"
                        after_you_got = you_section[len(you_got_phrase):].strip()
                        you_numbers = re.findall(r'\b\d+\b', after_you_got)
                        
                        if you_numbers:
                            you_spots = len(you_numbers)
                            cleaned_comment = clean_comment_text(body)
                            actual_user = author
                            
                            # Check if user is in removal list
                            user_status = "confirmed"
                            user_spot_count = you_spots
                            if actual_user.lower() in removed_users:
                                print(f"🚫 User u/{actual_user} is in removal list - setting spots to 0 and status to 'removed'", file=sys.stderr)
                                user_status = "removed"
                                user_spot_count = 0
                            
                            participants_to_add.append({
                                "redditUser": actual_user,
                                "name": "",
                                "comment": cleaned_comment[:100],
                                "spots": user_spot_count if user_status == "confirmed" else 0,
                                "requestedSpots": user_spot_count if user_status == "confirmed" else 0,
                                "owed": (user_spot_count * cost_per_spot) if user_status == "confirmed" else 0,
                                "paid": False,
                                "created_utc": created_utc,
                                "commentId": comment_id,
                                "status": user_status
                            })
                            print(f"✅ Found 'You got' for u/{actual_user}: '{reply_body[:50]}...' → {user_spot_count} spots (status: {user_status})", file=sys.stderr)
                        
                        # Parse "u/username got" for proxy user
                        # Extract proxy username and spots manually since parse_host_reply returns the FIRST match
                        proxy_match = re.search(r'/?u/(\w+)\s+got', reply_body, re.IGNORECASE)
                        if proxy_match:
                            proxy_username = proxy_match.group(1)
                            
                            # Extract spot numbers from the part AFTER "got"
                            got_index = reply_lower.find("got", proxy_match.start())
                            from_got = reply_body[got_index:]
                            
                            # Split at newline or common delimiters
                            spot_section = from_got.split('\n')[0]
                            for delimiter in ["Please", "please", "Follow", "follow", "GL", "Gl", "Good luck", "good luck", "GLGL", "glgl"]:
                                if delimiter in spot_section:
                                    spot_section = spot_section.split(delimiter)[0]
                                    break
                            
                            # Skip "got" text and extract numbers
                            after_got = spot_section[3:].strip()  # "got" is 3 characters
                            numbers = re.findall(r'\b\d+\b', after_got)
                            
                            if numbers:
                                proxy_spots = len(numbers)
                                cleaned_comment = clean_comment_text(body)
                                
                                # Check if proxy user is in removal list
                                proxy_status = "confirmed"
                                proxy_spot_count = proxy_spots
                                if proxy_username.lower() in removed_users:
                                    print(f"🚫 User u/{proxy_username} is in removal list - setting spots to 0 and status to 'removed'", file=sys.stderr)
                                    proxy_status = "removed"
                                    proxy_spot_count = 0
                                
                                participants_to_add.append({
                                    "redditUser": proxy_username,
                                    "name": "",
                                    "comment": cleaned_comment[:100],
                                    "spots": proxy_spot_count if proxy_status == "confirmed" else 0,
                                    "requestedSpots": proxy_spot_count if proxy_status == "confirmed" else 0,
                                    "owed": (proxy_spot_count * cost_per_spot) if proxy_status == "confirmed" else 0,
                                    "paid": False,
                                    "created_utc": created_utc,
                                    "commentId": comment_id,
                                    "status": proxy_status
                                })
                                print(f"✅ Found PROXY in dual assignment: u/{author} requested for u/{proxy_username}: '{reply_body[:50]}...' → {proxy_spot_count} spots (status: {proxy_status})", file=sys.stderr)
                        
                        break  # Found the assignment, stop checking replies
                    else:
                        # Normal case: single assignment
                        host_status = status
                        spot_count = spots
                        beneficiary_username = beneficiary
                        
                        # Use beneficiary username if provided (proxy request), otherwise use comment author
                        if beneficiary_username:
                            print(f"✅ Found PROXY request: u/{author} requested for u/{beneficiary_username}: '{reply_body[:50]}...' → {spots} spots (status: {status})", file=sys.stderr)
                        else:
                            print(f"✅ Found host reply for u/{author}: '{reply_body[:50]}...' → {spots} spots (status: {status})", file=sys.stderr)
                        break
        else:
            print(f"🔍 DEBUG: NO OP replies found for u/{author}", file=sys.stderr)

        # ✅ If we have participants to add from dual assignment, add them now
        if participants_to_add:
            participants.extend(participants_to_add)
            continue  # Skip normal processing since we already handled this comment

        # ✅ Handle tab/retab requests without host reply
        # If no host reply but comment contains tab/tabbed/retab, add with 0 spots
        if host_status is None:
            if is_tab_request(body):
                # ✅ Wait 5 minutes (300 seconds) before adding tab requests without host reply
                # This gives the host time to respond
                current_time = time.time()
                comment_age_seconds = current_time - created_utc

                if comment_age_seconds >= 300:
                    host_status = "tab_pending"
                    spot_count = 0
                    print(f"📋 Found TAB request without host reply for u/{author}: '{body[:50]}...' → 0 spots (pending, {int(comment_age_seconds)}s old)", file=sys.stderr)
                else:
                    # Comment is too recent, skip for now (will be picked up on next scan)
                    print(f"⏳ Skipping recent TAB request for u/{author} ({int(300 - comment_age_seconds)}s until eligible)", file=sys.stderr)
                    continue
            else:
                continue  # Skip this comment - don't add to participants

        # Clean comment text (remove URLs and images) before storing
        cleaned_comment = clean_comment_text(body)

        # Determine the actual Reddit user who gets the spots
        # If beneficiary_username is set (proxy request), use that. Otherwise use comment author.
        actual_reddit_user = beneficiary_username if beneficiary_username else author

        # ✅ CHECK: Is this user in the removal list?
        if actual_reddit_user.lower() in removed_users:
            print(f"🚫 User u/{actual_reddit_user} is in removal list - setting spots to 0 and status to 'removed'", file=sys.stderr)
            host_status = "removed"
            spot_count = 0

        # Add participant with host confirmation status
        participants.append({
            "redditUser": actual_reddit_user,  # The user who gets the spots
            "name": "",  # Will be filled by name mapping
            "comment": cleaned_comment[:100],  # Keep original user comment for display
            "spots": spot_count if host_status == "confirmed" else 0,
            "requestedSpots": spot_count if host_status == "confirmed" else 0,
            "owed": (spot_count * cost_per_spot) if host_status == "confirmed" else 0,
            "paid": False,
            "created_utc": created_utc,
            "commentId": comment_id,
            "status": host_status  # "confirmed", "waitlist", "removed", or "tab_pending"
        })

    # Sort by timestamp descending (newest first = oldest at bottom)
    participants.sort(key=lambda p: p.get("created_utc", 0), reverse=True)

    # ============ SPOT LIMIT ENFORCEMENT - Only for confirmed spots ============
    if total_spots is not None and total_spots > 0:
        running_total = current_assigned_spots
        print(f"📊 Starting spot enforcement with {running_total} already assigned spots", file=sys.stderr)

        for i in range(len(participants) - 1, -1, -1):  # Iterate from oldest to newest
            # Only enforce limits on confirmed entries
            if participants[i]["status"] != "confirmed":
                continue

            requested_spots = participants[i]["requestedSpots"]

            # Check if this request would exceed the limit
            if running_total >= total_spots:
                # Raffle is full
                participants[i]["spots"] = 0
                participants[i]["owed"] = 0
                print(f"⚠️ Raffle FULL ({running_total}/{total_spots}) - cannot assign {requested_spots} spots to u/{participants[i]['redditUser']}", file=sys.stderr)
            elif running_total + requested_spots > total_spots:
                # Partial assignment
                remaining = total_spots - running_total
                participants[i]["spots"] = remaining
                participants[i]["owed"] = remaining * cost_per_spot
                running_total = total_spots
                print(f"⚠️ Partial assignment for u/{participants[i]['redditUser']}: requested {requested_spots}, got {remaining} spots ({running_total}/{total_spots})", file=sys.stderr)
            else:
                # Full assignment
                participants[i]["spots"] = requested_spots
                participants[i]["owed"] = requested_spots * cost_per_spot
                running_total += requested_spots
                print(f"✅ Assigned {requested_spots} spots to u/{participants[i]['redditUser']} ({running_total}/{total_spots})", file=sys.stderr)

    # Validate parsed results
    participants = validate_parse_results(participants, total_spots)

    return participants

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"ok": False, "error": "Usage: reddit_parser.py <post_url> <cost_per_spot> [total_spots] [existing_comment_ids_json] [current_assigned_spots] [pending_tab_comment_ids_json]"}))
        sys.exit(1)

    try:
        post_url = sys.argv[1]
        cost_per_spot = float(sys.argv[2])

        # Parse totalSpots from argv[3] (always present, 'null' if not set)
        total_spots = None
        if len(sys.argv) > 3 and sys.argv[3] != 'null':
            try:
                total_spots = int(sys.argv[3])
            except:
                pass

        # Parse existing comment IDs from argv[4] (always present, '[]' if empty)
        existing_comment_ids = []
        if len(sys.argv) > 4:
            try:
                existing_comment_ids = json.loads(sys.argv[4])
            except:
                pass

        # Parse current assigned spots from argv[5] (always present, '0' if not set)
        current_assigned_spots = 0
        if len(sys.argv) > 5:
            try:
                current_assigned_spots = int(sys.argv[5])
            except:
                pass

        # Parse pending tab comment IDs from argv[6] (always present, '[]' if empty)
        pending_tab_comment_ids = []
        if len(sys.argv) > 6:
            try:
                pending_tab_comment_ids = json.loads(sys.argv[6])
            except:
                pass

        print(f"📊 Filtering out {len(existing_comment_ids)} already-processed comment IDs", file=sys.stderr)
        print(f"📊 Current assigned spots: {current_assigned_spots}", file=sys.stderr)

        result = parse_reddit_post(post_url, cost_per_spot, total_spots, existing_comment_ids, current_assigned_spots, pending_tab_comment_ids)

        print(json.dumps({"ok": True, "participants": result}))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(1)
