import sys
import json
import re
import requests
import random
import time
import os
from typing import List, Dict, Any, Tuple, Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file if it exists
except ImportError:
    pass  # python-dotenv not installed, will use system environment variables

# OpenAI API Configuration - DISABLED
OPENAI_API_KEY = ''  # Removed - not using AI parsing
USE_AI_PARSING = False  # Hardcoded to False

# Historical corrections database file
CORRECTIONS_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'parser_corrections.json')

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

# AI parsing functions removed - using regex only

def parse_spots_regex(text: str) -> Tuple[bool, Optional[int]]:
    """Parse spot count from comment text using regex (fallback method)"""
    body = (text or "").strip()
    if not body:
        return (False, 0)

    low = body.strip().lower()

    # Word-to-number mapping for spelled-out numbers
    word_to_num = {
        'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
        'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10',
        'eleven': '11', 'twelve': '12', 'thirteen': '13', 'fourteen': '14', 'fifteen': '15',
        'sixteen': '16', 'seventeen': '17', 'eighteen': '18', 'nineteen': '19', 'twenty': '20'
    }

    # Convert spelled-out numbers to digits
    body_converted = body
    for word, num in word_to_num.items():
        body_converted = re.sub(r'\b' + word + r'\b', num, body_converted, flags=re.IGNORECASE)

    low_converted = body_converted.lower()

    # "close" or "closer" → return 0 as placeholder
    if re.search(r'\b(close|closer)\b', low, re.IGNORECASE):
        return (True, 0)
    
    # "drama" → return 0 spots (special keyword)
    if re.search(r'^\s*drama\s*$', low, re.IGNORECASE):
        return (True, 0)

    # "sniper", "snipe", "sniping" → return 1 spot (slang for grabbing last/winning spot)
    if re.search(r'\bsnip(e|er|ing)?\b', low, re.IGNORECASE):
        return (True, 1)

    # "X spots/slots" rule: "4 spots", "12 spot", "10 slots" - CHECK THIS EARLY!
    spots_match = re.search(r"\b(\d+)\s+(?:spots?|slots?)\b", body_converted, re.IGNORECASE)
    if spots_match:
        return (True, int(spots_match.group(1)))

    # ============ FIX #1: Handle MULTIPLE ranges (e.g., "1-5, 17-21") ============
    # Find ALL range patterns in the text
    range_matches = re.findall(r"\b(\d+)\s*-\s*(\d+)\b", body_converted)
    if range_matches:
        total_range_spots = 0
        for match in range_matches:
            a = int(match[0])
            b = int(match[1])
            lo_n = min(a, b)
            hi_n = max(a, b)
            total_range_spots += (hi_n - lo_n + 1)
        return (True, total_range_spots)

    # ============ FIX #2: TAB format - only match when there's a SINGLE number before "tabbed" ============
    # "37 tabbed slum" = 1 spot (single number)
    # "5,9,12,56,65 tabbed doublechen" = should NOT match here (has commas, so multiple numbers)
    # First check: does the text have commas BEFORE "tabbed"?
    tabbed_position = body_converted.lower().find("tabbed")
    if tabbed_position > 0:
        text_before_tabbed = body_converted[:tabbed_position]
        # If there are commas before "tabbed", it's a multi-number request, not TAB format
        if "," not in text_before_tabbed:
            # Now check for single number before "tabbed"
            tabbed_match = re.search(r"(spot\s+)?(\d+)\s+tabbed\b", body_converted, re.IGNORECASE)
            if tabbed_match:
                return (True, 1)  # TAB format: requesting 1 specific spot

    # Random count - NOW INCLUDES "rando"
    random_match = re.search(
        r"(\d+)\s*(?:more\s*)?(?:rand(?:om)?s?|rando(?:s)?)\b",
        body_converted,
        re.IGNORECASE
    )
    random_count = int(random_match.group(1)) if random_match else 0

    # Also check for "a random", "an random", or just "rando" (means 1 random spot)
    if random_count == 0:
        a_random_match = re.search(r"\b(?:a|an)\s+rand(?:om)?\b", body_converted, re.IGNORECASE)
        if a_random_match:
            random_count = 1
        # Check for just "random" or "rando" alone (case-insensitive)
        elif re.search(r"^\s*rand(?:om|o)\s*$", body_converted, re.IGNORECASE):
            random_count = 1
        # Check for "and random" or "and Random" at the end
        elif re.search(r"\band\s+rand(?:om|o)\b", body_converted, re.IGNORECASE):
            random_count = 1

    # All numbers
    numbers = [int(n) for n in re.findall(r"\d+", body_converted)]

    # Remove random quantity from spot list
    if random_match:
        rand_qty = int(random_match.group(1))
        if rand_qty in numbers:
            numbers.remove(rand_qty)

    # Single number only → 1 spot
    if len(numbers) == 1 and random_count == 0:
        return (True, 1)

    # Explicit picks + random count
    if numbers or random_count:
        return (True, len(numbers) + random_count)

    return (False, 0)

def parse_spots(text: str) -> Tuple[bool, Optional[int]]:
    """Main parsing function - uses regex only"""
    return parse_spots_regex(text)

def parse_host_reply(reply_text: str) -> Tuple[Optional[str], Optional[int]]:
    """
    Parse host's reply to extract spot count
    
    Returns: (status, spot_count)
    - status: "confirmed", "waitlist", or None
    - spot_count: number of spots assigned (count of numbers in "You got X, Y, Z")
    """
    if not reply_text:
        return (None, None)
    
    reply_lower = reply_text.strip().lower()
    
    # Check for waitlist
    if "waitlist starts here" in reply_lower:
        return ("waitlist", 0)
    
    # Check for "You got" format anywhere in the reply (not just at start)
    if "you got" not in reply_lower:
        return (None, None)
    
    # Find the "You got" part and extract ONLY that section
    # Strategy: Extract everything between "You got" and any delimiter
    
    # First, find where "You got" starts (case-insensitive)
    you_got_index = reply_lower.find("you got")
    if you_got_index == -1:
        return (None, None)
    
    # Extract from "You got" onwards
    from_you_got = reply_text[you_got_index:]
    
    # Now split at common delimiters to isolate ONLY the spot numbers
    # Stop at: newline, "Please", "Follow", "GL", etc.
    spot_section = from_you_got.split('\n')[0]  # Take first line only
    
    # Also stop at common phrases that come AFTER spot assignment
    for delimiter in ["Please", "please", "Follow", "follow", "GL", "Gl", "Good luck", "good luck", "GLGL", "glgl"]:
        if delimiter in spot_section:
            spot_section = spot_section.split(delimiter)[0]
            break
    
    # Now extract numbers ONLY from the spot section
    # "You got 5, 12, 23, 48, 91" → [5, 12, 23, 48, 91] → 5 spots
    numbers = re.findall(r'\b\d+\b', spot_section)
    
    if numbers:
        spot_count = len(numbers)
        return ("confirmed", spot_count)
    
    return (None, None)

def walk_comment_tree(children: List[Dict[str, Any]], out: List[Dict[str, Any]], depth: int = 0):
    """Recursively walk Reddit comment tree"""
    for child in children or []:
        if not child or child.get("kind") != "t1":
            continue
        d = child.get("data") or {}

        # Collect OP replies for spot confirmation
        op_replies = []
        replies = d.get("replies")
        if isinstance(replies, dict):
            rep_children = (replies.get("data") or {}).get("children") or []
            for rep_child in rep_children:
                if rep_child and rep_child.get("kind") == "t1":
                    rep_data = rep_child.get("data") or {}
                    # Check if this reply is from OP (is_submitter = True)
                    if rep_data.get("is_submitter", False):
                        op_replies.append({
                            "author": rep_data.get("author", ""),
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
            "is_submitter": d.get("is_submitter", False),  # Is this comment from the post author (OP)?
            "parent_id": d.get("parent_id", ""),  # Parent comment ID for threading
        })

        if isinstance(replies, dict):
            if rep_children:
                walk_comment_tree(rep_children, out, depth + 1)


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
            except (IndexError, KeyError, AttributeError):
                pass  # If we can't get OP, we'll continue without filtering

            children = (((data or [None, None])[1] or {}).get("data") or {}).get("children") or []

            flat = []
            walk_comment_tree(children, flat, 0)

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
    
    # Filter out bot reply patterns
    bot_reply_patterns = [
        'you got',
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

def has_payment_confirmation(reply_texts: List[str]) -> bool:
    """Check if any reply contains payment confirmation"""
    if not reply_texts:
        return False

    # Payment confirmation patterns
    payment_patterns = [
        'payment made',
        'paid',
        'payment received',
        'payment sent',
        'payment complete',
        'transaction complete',
        'paypal sent',
        'venmo sent',
        'zelle sent',
        'cashapp sent',
    ]

    for reply in reply_texts:
        reply_lower = reply.lower().strip()
        for pattern in payment_patterns:
            if pattern in reply_lower:
                return True

    return False

# ============ HISTORICAL PATTERN LEARNING ============

def load_corrections_database() -> Dict[str, Any]:
    """Load historical corrections from JSON file"""
    try:
        if os.path.exists(CORRECTIONS_DB_FILE):
            with open(CORRECTIONS_DB_FILE, 'r') as f:
                return json.load(f)
        else:
            # Initialize with empty database
            return {"patterns": [], "stats": {"total_corrections": 0, "last_updated": None}}
    except Exception as e:
        print(f"⚠️ Error loading corrections database: {e}", file=sys.stderr)
        return {"patterns": [], "stats": {"total_corrections": 0, "last_updated": None}}

def save_corrections_database(db: Dict[str, Any]):
    """Save corrections database to JSON file"""
    try:
        db["stats"]["last_updated"] = time.time()
        with open(CORRECTIONS_DB_FILE, 'w') as f:
            json.dump(db, f, indent=2)
        print(f"💾 Saved corrections database to {CORRECTIONS_DB_FILE}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️ Error saving corrections database: {e}", file=sys.stderr)

def normalize_pattern(text: str) -> str:
    """Normalize comment text to a pattern for matching"""
    # Convert to lowercase
    text = text.lower().strip()
    
    # Replace specific numbers with placeholders for pattern matching
    # e.g., "5,9,12,56,65 tabbed username" → "N,N,N,N,N tabbed <username>"
    
    # Count comma-separated numbers at the start
    number_list_match = re.match(r'^([\d,\s]+)\s+tabbed', text)
    if number_list_match:
        number_list = number_list_match.group(1)
        num_count = len(re.findall(r'\d+', number_list))
        # Create pattern: "N,N,N,N,N tabbed <username>"
        pattern = f"{','.join(['N'] * num_count)} tabbed <username>"
        return pattern
    
    # Replace single numbers with N for pattern matching
    # "37 tabbed username" → "N tabbed <username>"
    text = re.sub(r'\b\d+\b', 'N', text)
    
    # Replace usernames after "tabbed" with placeholder
    text = re.sub(r'tabbed\s+\S+', 'tabbed <username>', text)
    
    return text

def match_known_pattern(comment: str, db: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Check if comment matches a known problem pattern"""
    if not db or "patterns" not in db:
        return None
    
    normalized = normalize_pattern(comment)
    
    # Search for matching pattern
    for pattern_entry in db["patterns"]:
        if pattern_entry["pattern"] == normalized:
            # Check confidence threshold (only apply if seen multiple times)
            if pattern_entry["frequency"] >= 2:  # Require at least 2 occurrences
                return pattern_entry
    
    return None

def apply_learned_corrections(participants: List[Dict[str, Any]], cost_per_spot: float) -> List[Dict[str, Any]]:
    """Apply historical pattern corrections to participants"""
    db = load_corrections_database()
    
    if not db or "patterns" not in db or len(db["patterns"]) == 0:
        print("📚 No historical patterns loaded yet", file=sys.stderr)
        return participants
    
    corrections_applied = 0
    
    for i, p in enumerate(participants):
        comment = p.get("comment", "")
        current_spots = p.get("spots", 0)
        
        # Check if this comment matches a known problem pattern
        matched_pattern = match_known_pattern(comment, db)
        
        if matched_pattern:
            correct_spots = matched_pattern["correct_parse"]
            
            # Only apply if there's a discrepancy
            if current_spots != correct_spots:
                print(f"🎓 LEARNED PATTERN MATCH: \"{comment}\"", file=sys.stderr)
                print(f"   Pattern: {matched_pattern['pattern']}", file=sys.stderr)
                print(f"   Correcting {current_spots} → {correct_spots} spots (confidence: {matched_pattern['frequency']} occurrences)", file=sys.stderr)
                
                participants[i]["spots"] = correct_spots
                participants[i]["owed"] = correct_spots * cost_per_spot
                participants[i]["requestedSpots"] = correct_spots
                corrections_applied += 1
    
    if corrections_applied > 0:
        print(f"\n🎓 Applied {corrections_applied} learned corrections from historical patterns", file=sys.stderr)
    
    return participants

def record_correction(comment: str, wrong_parse: int, correct_parse: int):
    """Record a manual correction to the historical database"""
    
    # ============ VALIDATION: Filter out suspicious corrections ============
    # Prevent learning from typos and mistakes instead of real parser errors
    
    # 1. Check for digit appending typo (e.g., "3" → "32", "5" → "54")
    wrong_str = str(wrong_parse)
    correct_str = str(correct_parse)
    
    if len(correct_str) == len(wrong_str) + 1 and correct_str.startswith(wrong_str):
        print(f"⚠️ REJECTED: Likely typo detected (digit appended: {wrong_parse} → {correct_parse})", file=sys.stderr)
        print(f"   Pattern: \"{comment}\"", file=sys.stderr)
        print(f"   This correction was NOT saved to the learning database.", file=sys.stderr)
        return None
    
    # 2. Check for small number becoming large number (likely mistake)
    if wrong_parse > 0 and wrong_parse <= 10 and correct_parse > wrong_parse * 5:
        print(f"⚠️ REJECTED: Suspicious large increase ({wrong_parse} → {correct_parse}, {correct_parse/wrong_parse:.1f}x)", file=sys.stderr)
        print(f"   Pattern: \"{comment}\"", file=sys.stderr)
        print(f"   This correction was NOT saved to the learning database.", file=sys.stderr)
        return None
    
    # 3. Check if parser result seems reasonable - don't learn if parser was likely correct
    # Extract number from comment for basic validation
    numbers_in_comment = re.findall(r'\b(\d+)\b', comment)
    if numbers_in_comment:
        first_number = int(numbers_in_comment[0])
        # If parser matched the first number exactly, it was probably correct
        if wrong_parse == first_number and correct_parse != first_number:
            print(f"⚠️ REJECTED: Parser correctly matched the number in comment ({wrong_parse})", file=sys.stderr)
            print(f"   Pattern: \"{comment}\"", file=sys.stderr)
            print(f"   Manual edit to {correct_parse} appears to be an intentional modification, not a parser error.", file=sys.stderr)
            print(f"   This correction was NOT saved to the learning database.", file=sys.stderr)
            return None
    
    # 4. Require significant change - don't learn from minor adjustments (±1 or ±2)
    if abs(correct_parse - wrong_parse) <= 2:
        print(f"⚠️ REJECTED: Change too small ({wrong_parse} → {correct_parse}), likely intentional adjustment", file=sys.stderr)
        print(f"   Pattern: \"{comment}\"", file=sys.stderr)
        print(f"   This correction was NOT saved to the learning database.", file=sys.stderr)
        return None
    
    # ============ VALIDATION PASSED - Record the correction ============
    
    db = load_corrections_database()
    
    # Normalize the comment to a pattern
    pattern = normalize_pattern(comment)
    
    # Check if pattern already exists
    pattern_found = False
    for pattern_entry in db["patterns"]:
        if pattern_entry["pattern"] == pattern:
            # Update existing pattern
            pattern_entry["frequency"] += 1
            pattern_entry["examples"].append({
                "comment": comment[:100],
                "wrong_parse": wrong_parse,
                "correct_parse": correct_parse,
                "timestamp": time.time()
            })
            # Keep only last 10 examples
            pattern_entry["examples"] = pattern_entry["examples"][-10:]
            pattern_found = True
            print(f"📝 Updated existing pattern (frequency: {pattern_entry['frequency']})", file=sys.stderr)
            break
    
    if not pattern_found:
        # Add new pattern
        db["patterns"].append({
            "pattern": pattern,
            "correct_parse": correct_parse,
            "frequency": 1,
            "examples": [{
                "comment": comment[:100],
                "wrong_parse": wrong_parse,
                "correct_parse": correct_parse,
                "timestamp": time.time()
            }]
        })
        print(f"📝 Recorded new pattern: {pattern}", file=sys.stderr)
    
    # Update stats
    db["stats"]["total_corrections"] += 1
    
    # Save database
    save_corrections_database(db)
    
    return db

def validate_parse_results(participants: List[Dict[str, Any]], total_spots: Optional[int], cost_per_spot: float) -> List[Dict[str, Any]]:
    """Validate parsed results and flag potential errors for re-parsing or review"""
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
    for i, p in enumerate(participants):
        spot_count = p.get("spots", 0)
        if spot_count > HIGH_SPOT_THRESHOLD:
            validation_flags.append({
                "type": "high_spot_count",
                "user": p.get("redditUser", "unknown"),
                "spots": spot_count,
                "comment": p.get("comment", "")[:60]
            })
            print(f"⚠️ VALIDATION: u/{p.get('redditUser')} requested {spot_count} spots (>{HIGH_SPOT_THRESHOLD}) - Comment: \"{p.get('comment', '')[:60]}...\"", file=sys.stderr)
            
            # Optional: Re-parse with stricter prompt
            comment = p.get("comment", "")
            if comment and USE_AI_PARSING and OPENAI_API_KEY:
                print(f"🔄 Re-parsing high spot count comment with double-check...", file=sys.stderr)
                found, revalidated_count = parse_spots_with_ai(comment)
                if found and revalidated_count != spot_count:
                    print(f"  ✅ Corrected: {spot_count} → {revalidated_count}", file=sys.stderr)
                    participants[i]["spots"] = revalidated_count
                    participants[i]["owed"] = revalidated_count * cost_per_spot
                    participants[i]["requestedSpots"] = revalidated_count
    
    # CHECK 3: Allow multiple comments from same user (removed duplicate validation)
    # Users can request spots multiple times in the same raffle
    
    # CHECK 4: Invalid spot counts (negative or zero, except for legitimate close/drama)
    for i, p in enumerate(participants):
        spots = p.get("spots", 0)
        comment = p.get("comment", "").lower()
        
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
    
    # CHECK 5: Sanity check - spot count shouldn't exceed total raffle spots
    if total_spots:
        for i, p in enumerate(participants):
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

def parse_reddit_post(post_url: str, cost_per_spot: float, total_spots: Optional[int] = None, existing_comment_ids: Optional[List[str]] = None, current_assigned_spots: int = 0) -> List[Dict[str, Any]]:
    """Main function to parse Reddit post and extract participants"""
    comments, op_author = fetch_reddit_comments(post_url)
    participants = []
    
    # ✅ Filter out already-processed comments BEFORE parsing
    if existing_comment_ids:
        existing_ids_set = set(existing_comment_ids)
        original_count = len(comments)
        comments = [c for c in comments if c.get('id') not in existing_ids_set]
        filtered_count = original_count - len(comments)
        print(f"✅ Filtered out {filtered_count} already-processed comments BEFORE parsing. {len(comments)} new comments to parse.", file=sys.stderr)

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

        # ============ NEW PARSING LOGIC: Parse from HOST REPLY ============
        # Look for OP's reply to this comment
        host_status = None
        spot_count = None
        
        if op_replies:
            # Check each OP reply for "You got" format
            for op_reply in op_replies:
                reply_body = op_reply.get("body", "")
                status, spots = parse_host_reply(reply_body)
                
                if status:
                    host_status = status
                    spot_count = spots
                    print(f"✅ Found host reply for u/{author}: '{reply_body[:50]}...' → {spots} spots (status: {status})", file=sys.stderr)
                    break
        
        # ONLY parse comments that have host confirmation with "You got"
        if host_status is None:
            print(f"⏭️ Skipping u/{author} - no host confirmation yet", file=sys.stderr)
            continue  # Skip this comment - don't add to participants

        # Clean comment text (remove URLs and images) before storing
        cleaned_comment = clean_comment_text(body)

        # Add participant with host confirmation status
        participants.append({
            "redditUser": author,
            "name": "",  # Will be filled by name mapping
            "comment": cleaned_comment[:100],  # Keep original user comment for display
            "spots": spot_count if host_status == "confirmed" else 0,
            "requestedSpots": spot_count if host_status == "confirmed" else 0,
            "owed": (spot_count * cost_per_spot) if host_status == "confirmed" else 0,
            "paid": False,
            "created_utc": created_utc,
            "commentId": comment_id,
            "status": host_status  # "confirmed" or "waitlist"
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
    participants = validate_parse_results(participants, total_spots, cost_per_spot)

    return participants

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"ok": False, "error": "Usage: reddit_parser.py <post_url> <cost_per_spot> [total_spots] [existing_comment_ids_json] [current_assigned_spots]"}))
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

        print(f"📊 Filtering out {len(existing_comment_ids)} already-processed comment IDs", file=sys.stderr)
        print(f"📊 Current assigned spots: {current_assigned_spots}", file=sys.stderr)

        result = parse_reddit_post(post_url, cost_per_spot, total_spots, existing_comment_ids, current_assigned_spots)
        
        print(json.dumps({"ok": True, "participants": result}))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(1)
