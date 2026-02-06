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

# OpenAI API Configuration
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')  # Set via environment variable
USE_AI_PARSING = os.environ.get('USE_AI_PARSING', 'false').lower() == 'true'

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

def parse_spots_with_ai(text: str) -> Tuple[bool, Optional[int]]:
    """Use OpenAI to parse spot count from comment text"""
    if not OPENAI_API_KEY:
        # Fallback to regex if no API key
        print("⚠️ No API key found - using regex fallback", file=sys.stderr)
        return parse_spots_regex(text)

    try:
        print(f"🤖 Using OpenAI AI parsing for: {text[:50]}...", file=sys.stderr)
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-4o',  # Ultra-fast and most accurate model
                'messages': [
                    {
                        'role': 'system',
                        'content': '''You are a Reddit raffle comment parser. Your job is to extract the TOTAL NUMBER OF SPOTS being requested from a comment.

CRITICAL RULES:
0. **REJECT COMMENTS WITH NO NUMBERS**: If a comment contains NO numbers at all, return 0. Only parse comments that contain at least one number.
   - Example: "sorry for the slow day, will be cancelling" → 0 (no numbers = not a spot request)
   - Example: "This raffle has been cancelled" → 0 (no numbers = not a spot request)
   - Example: "good luck everyone!" → 0 (no numbers = not a spot request)
1. Count EACH explicitly mentioned spot number as 1 spot (e.g., "5, 12, 99" = 3 spots)
2. Count ranges inclusively (e.g., "1-20" = 20 spots, "5-8" = 4 spots)
   - IMPORTANT: When you see MULTIPLE ranges separated by commas, count EACH range separately and ADD them together
   - Example: "1-5, 17-21" means range 1 to 5 (that's 5 spots) PLUS range 17 to 21 (that's 5 spots) = 10 total spots
3. "random" or "rando" alone (case-insensitive) = 1 spot (e.g., "Random", "random", "RANDOM" all = 1 spot)
   - IMPORTANT: When "and random" or "and Random" appears AFTER a list of explicit numbers, add 1 spot to the count
   - Example: "6,30,44,67 and Random" = count the 4 numbers (6, 30, 44, 67) PLUS the word "Random" = 5 total spots
4. "X randoms" = X spots (e.g., "5 randoms" = 5 spots)
5. "X spots" means X spots total (e.g., "5 spots" = 5 spots)
6. ADD explicit spots + random spots together (e.g., "spot 5, 12 and 3 randoms" = 2 + 3 = 5 total)
7. Ignore any names, dollar amounts, or non-spot-request text
8. Return ONLY the total number, nothing else
9. IGNORE numbers in usernames after "tabbed" or "tag" keywords (e.g., "tabbed chewy96" - ignore the 96)
   - EXCEPTION: When there are MULTIPLE comma-separated numbers BEFORE the word "tabbed", count ALL those numbers
   - Example: "5,9,12,56,65 tabbed doublechen" = count all 5 numbers (5, 9, 12, 56, 65) = 5 spots (ignore "doublechen")
   - Example: "37 tabbed slum" = only 1 number before "tabbed" = 1 spot
10. Handle slang: "booties" = randoms, "drama" = 0 spots (parsed but defaults to 0)
11. Handle typos/misspellings of "random": "tandom", "randon", "milking", etc.
12. Words before "random" like "additional", "more", "extra" don't negate the quantity (e.g., "10 additional random" = 10 spots)
13. "or" means ONE choice, not both (e.g., "spot 33 or 34" = 1 spot, not 2)
14. "sub" or "if not available" indicates conditional/substitute - count only ONE set (e.g., "2,22 sub 13,10" = 2 spots, not 4)
15. "spot X" refers to a specific spot NUMBER, which counts as 1 spot (e.g., "spot 82" = 1 spot, not 82 spots)
16. Ignore conversational context - only parse actual requests
17. "close" or "closer" = 0 spots (special keyword for closing raffle)

TRAINING EXAMPLES (learn from these mistakes):
"Random" → 1 (just the word "random" alone, any capitalization)
"random" → 1 (lowercase works too)
"RANDOM" → 1 (uppercase works too)
"5 booties please" → 5 (not 0, "booties" is slang for randoms)
"10 additional random please" → 10 (not 1, "additional" doesn't negate the 10)
"10 tandom" → 10 (not 1, "tandom" is a typo for "random")
"20 milking spots" → 20 (not 1, "milking" is autocorrect error for "random")
"2 more" → 2 (not 1, "2 more" means 2 additional spots)
"2 randoms tabbed chewy96" → 2 (not 3, ignore the 96 in username)
"spot 33 or 34" → 1 (not 2, "or" means one choice)
"2,22 sub 13 and 10 if not available" → 2 (not 4, wants 2 total: either 2+22 OR 13+10)
"spot 82" → 1 (not 82, this is requesting spot NUMBER 82, which is 1 spot)
"37 tabbed slum" → 1 (TAB format: requesting spot #37, which is 1 spot, not 37 spots)
"Spot 32 tabbed to chen" → 1 (TAB format: requesting spot #32, which is 1 spot)
"Spot 21 tabbed Jealous (WFF)" → 1 (TAB format: requesting spot #21, which is 1 spot)
"1-20" → 20 (range from 1 to 20 = 20 spots total)
"5, 12, 99 and 2 randoms" → 5 (3 specific spots + 2 randoms)
"3 odd numbers" → 3 (qualifier word "odd" doesn't change count, extract the number)
"Random 10 tabbed drip" → 10 (extract the number, ignore qualifier "random")
"10 even spots plz" → 10 (qualifier word "even" doesn't change count)
"Sniper" → 1 (slang for trying to grab last/winning spot, always 1 spot)
"snipe" → 1 (variation of "sniper")
"sniping" → 1 (variation of "sniper")
"10-20 24 28 35 67 69 no sub" → Count the spots in the request, but NOTE: actual assigned spots depend on host confirmation
"17 no sub" → Requested spot may result in 0 if taken (no substitution allowed, host won't reply)
"1-5, 10 random" → 15 (range 1-5 = 5 spots, PLUS 10 random = 10 spots, ADD them: 5 + 10 = 15 total)
"5 more tabbed to dr wins" → 5 (\"5 more\" means 5 spots, don't count it as 1 spot)
"drama" → 0 (special keyword meaning participant wants to be on waitlist, no spots requested)

MORE EXAMPLES:
"Spot 5 and 12 please" → 2
"5 spots please" → 5
"1-20" → 20
"Spot 17, 23, and 2 randoms" → 4
"3, 4, 33, 34, 343, and 5 randoms pls" → 10
"7, 11, 22, 77 and 4 random" → 8
"5 random" → 5
"a random" → 1
"Henry Thang 373" → 1
"spot 69" → 1
"3 even" → 3
"5 odd" → 5
"snipe" → 1
"close" → 0
"6,30,44,67 and Random" → 5 (4 explicit spots + 1 random = 5 total)
"5,9,12,56,65 tabbed doublechen w/t" → 5 (5 explicit comma-separated spots)
"1-5, 17-21" → 10 (range 1-5 = 5 spots, range 17-21 = 5 spots, total = 10)'''
                    },
                    {
                        'role': 'user',
                        'content': text
                    }
                ],
                'temperature': 0,
                'max_tokens': 10
            },
            timeout=5
        )

        if response.status_code == 200:
            result = response.json()
            spots_str = result['choices'][0]['message']['content'].strip()
            spots = int(spots_str)
            return (True, spots)
        else:
            # Fallback to regex if API call fails
            return parse_spots_regex(text)

    except Exception as e:
        # Fallback to regex on any error
        return parse_spots_regex(text)

def parse_spots_with_ai_batch(comments: List[str]) -> List[Tuple[bool, Optional[int]]]:
    """Use OpenAI to parse spot counts for multiple comments in a single batch (MUCH faster and cheaper!)"""
    if not OPENAI_API_KEY:
        print("⚠️ No API key found - using regex fallback for all comments", file=sys.stderr)
        return [parse_spots_regex(text) for text in comments]

    if not comments:
        return []

    try:
        print(f"🚀 Batching {len(comments)} comments into a single AI call...", file=sys.stderr)

        # Build batch input: number each comment
        batch_input = ""
        for i, text in enumerate(comments):
            batch_input += f"{i+1}. {text}\n"

        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-4o',
                'messages': [
                    {
                        'role': 'system',
                        'content': '''You are a Reddit raffle comment parser. Parse EACH numbered comment and return ONLY a JSON array of spot counts.

CRITICAL RULES:
0. **REJECT COMMENTS WITH NO NUMBERS**: If a comment contains NO numbers at all, return 0. Only parse comments that contain at least one number.
   - Example: "sorry for the slow day, will be cancelling" → 0 (no numbers = not a spot request)
   - Example: "This raffle has been cancelled" → 0 (no numbers = not a spot request)
   - Example: "good luck everyone!" → 0 (no numbers = not a spot request)
1. Count EACH explicitly mentioned spot number as 1 spot (e.g., "5, 12, 99" = 3 spots)
2. Count ranges inclusively (e.g., "1-20" = 20 spots, "5-8" = 4 spots)
   - IMPORTANT: When you see MULTIPLE ranges separated by commas, count EACH range separately and ADD them together
   - Example: "1-5, 17-21" means range 1 to 5 (that's 5 spots) PLUS range 17 to 21 (that's 5 spots) = 10 total spots
3. "random" or "rando" alone (case-insensitive) = 1 spot (e.g., "Random", "random", "RANDOM" all = 1 spot)
   - IMPORTANT: When "and random" or "and Random" appears AFTER a list of explicit numbers, add 1 spot to the count
   - Example: "6,30,44,67 and Random" = count the 4 numbers (6, 30, 44, 67) PLUS the word "Random" = 5 total spots
4. "X randoms" = X spots (e.g., "5 randoms" = 5 spots)
5. "X spots" means X spots total (e.g., "5 spots" = 5 spots)
6. ADD explicit spots + random spots together (e.g., "spot 5, 12 and 3 randoms" = 2 + 3 = 5 total)
7. Ignore any names, dollar amounts, or non-spot-request text
8. IGNORE numbers in usernames after "tabbed" or "tag" keywords (e.g., "tabbed chewy96" - ignore the 96)
   - EXCEPTION: When there are MULTIPLE comma-separated numbers BEFORE the word "tabbed", count ALL those numbers
   - Example: "5,9,12,56,65 tabbed doublechen" = count all 5 numbers (5, 9, 12, 56, 65) = 5 spots (ignore "doublechen")
   - Example: "37 tabbed slum" = only 1 number before "tabbed" = 1 spot
9. Handle slang: "booties" = randoms, "drama" = 0 spots (parsed but defaults to 0)
10. Handle typos/misspellings of "random": "tandom", "randon", "milking", etc.
11. Words before "random" like "additional", "more", "extra" don't negate the quantity (e.g., "10 additional random" = 10 spots)
12. "or" means ONE choice, not both (e.g., "spot 33 or 34" = 1 spot, not 2)
13. "sub" or "if not available" indicates conditional/substitute - count only ONE set (e.g., "2,22 sub 13,10" = 2 spots, not 4)
14. "spot X" refers to a specific spot NUMBER, which counts as 1 spot (e.g., "spot 82" = 1 spot, not 82 spots)
15. Ignore conversational context - only parse actual requests
16. "close" or "closer" = 0 spots (special keyword for closing raffle)

OUTPUT FORMAT:
Return ONLY a JSON array of numbers, one per comment, in order.
Example: [2, 5, 20, 4, 1, 0]

TRAINING EXAMPLES (learn from these):
"Random" → 1
"6,30,44,67 and Random" → 5 (4 explicit spots + 1 random = 5 total)
"5,9,12,56,65 tabbed doublechen w/t" → 5 (5 explicit comma-separated spots)
"1-5, 17-21" → 10 (range 1-5 = 5 spots, range 17-21 = 5 spots, total = 10)
"37 tabbed slum" → 1 (single number with tabbed = 1 spot)
"Spot 5 and 12 please" → 2
"5 spots please" → 5
"1-20" → 20
"Spot 17, 23, and 2 randoms" → 4

Do NOT include any other text, explanation, or formatting. JUST the JSON array.'''
                    },
                    {
                        'role': 'user',
                        'content': batch_input
                    }
                ],
                'temperature': 0,
                'max_tokens': len(comments) * 5  # ~5 tokens per spot count
            },
            timeout=15  # Longer timeout for batch processing
        )

        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()

            # Parse JSON array from response
            spot_counts = json.loads(content)

            if len(spot_counts) != len(comments):
                print(f"⚠️ AI returned {len(spot_counts)} counts but expected {len(comments)}, falling back to regex", file=sys.stderr)
                return [parse_spots_regex(text) for text in comments]

            # Convert to tuple format
            results = []
            for count in spot_counts:
                if isinstance(count, int) and count >= 0:
                    results.append((True, count))
                else:
                    results.append((False, 0))

            print(f"✅ Successfully parsed {len(results)} comments in batch!", file=sys.stderr)
            return results
        else:
            print(f"⚠️ AI batch call failed with status {response.status_code}, falling back to regex", file=sys.stderr)
            return [parse_spots_regex(text) for text in comments]

    except Exception as e:
        print(f"⚠️ AI batch parsing error: {str(e)}, falling back to regex", file=sys.stderr)
        return [parse_spots_regex(text) for text in comments]

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
    """Main parsing function - uses AI if enabled, otherwise regex"""
    if USE_AI_PARSING and OPENAI_API_KEY:
        return parse_spots_with_ai(text)
    else:
        return parse_spots_regex(text)

def walk_comment_tree(children: List[Dict[str, Any]], out: List[Dict[str, Any]], depth: int = 0):
    """Recursively walk Reddit comment tree"""
    for child in children or []:
        if not child or child.get("kind") != "t1":
            continue
        d = child.get("data") or {}

        # Collect replies for payment detection
        reply_texts = []
        replies = d.get("replies")
        if isinstance(replies, dict):
            rep_children = (replies.get("data") or {}).get("children") or []
            for rep_child in rep_children:
                if rep_child and rep_child.get("kind") == "t1":
                    rep_data = rep_child.get("data") or {}
                    rep_body = (rep_data.get("body") or "").lower()
                    reply_texts.append(rep_body)

        out.append({
            "id": d.get("id", ""),
            "author": d.get("author", "") or "[deleted]",
            "body": d.get("body", "") or "",
            "created_utc": d.get("created_utc", 0),
            "permalink": ("https://www.reddit.com" + d["permalink"]) if d.get("permalink") else "",
            "depth": depth,
            "reply_texts": reply_texts,  # Store reply texts for payment detection
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

def parse_reddit_post(post_url: str, cost_per_spot: float, total_spots: Optional[int] = None) -> List[Dict[str, Any]]:
    """Main function to parse Reddit post and extract participants"""
    comments, op_author = fetch_reddit_comments(post_url)
    participants = []

    # Collect all comment bodies for batch parsing
    comment_bodies = [comment.get("body", "") for comment in comments]

    # Parse spots using batch AI if enabled
    if USE_AI_PARSING and OPENAI_API_KEY:
        spot_results = parse_spots_with_ai_batch(comment_bodies)
    else:
        spot_results = [parse_spots_regex(body) for body in comment_bodies]

    for i, comment in enumerate(comments):
        author = comment.get("author", "")
        body = comment.get("body", "")
        reply_texts = comment.get("reply_texts", [])
        created_utc = comment.get("created_utc", 0)
        comment_id = comment.get("id", "")  # Get Reddit comment ID for duplicate detection

        # Skip deleted/removed comments and AutoModerator
        if not author or author in ["[deleted]", "[removed]", "AutoModerator"]:
            continue

        # ✅ CHANGED: Allow OP/host comments (for escrow participation)
        # The is_bot_confirmation() check below will filter out spot assignment replies
        # if author == op_author:
        #     continue

        # Skip bot confirmation messages (includes "You got" spot assignments from host)
        if is_bot_confirmation(body):
            continue

        # Skip comments that have payment confirmation replies
        if has_payment_confirmation(reply_texts):
            continue

        # Skip host/bot replies
        if is_host_bot_reply(author, body):
            continue

        # Skip comments that contain ONLY links/images (no actual text content)
        cleaned_for_check = clean_comment_text(body)
        if not cleaned_for_check or len(cleaned_for_check.strip()) == 0:
            continue

        # Parse spots
        found, spot_count = spot_results[i]

        if found and spot_count is not None:
            actual_spots = spot_count

            # ✅ SKIP COMMENTS WITH NO SPOTS (e.g., cancellation announcements, non-request comments)
            # Only add participants who actually requested spots
            if actual_spots is None or actual_spots == 0:
                print(f"⚠️ Skipping comment from u/{author} - no spots requested: \"{body[:60]}...\"", file=sys.stderr)
                continue  # Skip this comment, don't add to participants

            # Clean comment text (remove URLs and images) before storing
            cleaned_comment = clean_comment_text(body)

            # Add participant with timestamp and comment ID
            participants.append({
                "redditUser": author,
                "name": "",  # Will be filled by name mapping
                "comment": cleaned_comment[:100],
                "spots": actual_spots,
                "requestedSpots": actual_spots,  # Store original request BEFORE limit enforcement
                "owed": actual_spots * cost_per_spot,
                "paid": False,
                "created_utc": created_utc,  # Include timestamp for sorting
                "commentId": comment_id  # IMPORTANT: Reddit comment ID for duplicate detection
            })

    # Sort by timestamp descending (newest first = oldest at bottom)
    participants.sort(key=lambda p: p.get("created_utc", 0), reverse=True)

    # ============ ENFORCE SPOT LIMIT ============
    # If total_spots is provided, prevent over-assignment
    if total_spots is not None and total_spots > 0:
        running_total = 0
        for i in range(len(participants) - 1, -1, -1):  # Iterate from oldest to newest
            requested_spots = participants[i]["requestedSpots"]  # Use ORIGINAL request, not current assignment

            # Check if this request would exceed the limit
            if running_total >= total_spots:
                # Raffle is full - set to 0 spots
                participants[i]["spots"] = 0
                participants[i]["owed"] = 0
            elif running_total + requested_spots > total_spots:
                # Partial assignment - give only what's left
                remaining = total_spots - running_total
                participants[i]["spots"] = remaining
                participants[i]["owed"] = remaining * cost_per_spot
                running_total = total_spots
            else:
                # Full assignment - within limits
                running_total += requested_spots

    # ============ HANDLE "CLOSE" or "CLOSER" LOGIC ============
    # If total_spots is provided, handle the "close"/"closer" keyword
    if total_spots is not None and total_spots > 0:
        # Find the first "close" or "closer" comment (chronologically oldest)
        close_index = -1
        for i, p in enumerate(participants):
            # Check if the participant has 0 spots (which indicates "close"/"closer")
            # Also verify the comment text contains "close" or "closer"
            if p["spots"] == 0 and re.search(r'\b(close|closer)\b', p["comment"], re.IGNORECASE):
                close_index = i
                break

        if close_index >= 0:
            # Calculate spots already allocated BEFORE the "close" comment
            spots_before_close = sum(p["spots"] for i, p in enumerate(participants) if i > close_index)

            # Calculate remaining spots
            remaining_spots = max(0, total_spots - spots_before_close)

            # Assign remaining spots to the "close" comment
            participants[close_index]["spots"] = remaining_spots
            participants[close_index]["owed"] = remaining_spots * cost_per_spot

            # Set all comments AFTER "close" to 0 spots
            for i in range(close_index):
                participants[i]["spots"] = 0
                participants[i]["owed"] = 0

    return participants

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"ok": False, "error": "Usage: reddit_parser.py <post_url> <cost_per_spot> [total_spots] [existing_comment_ids_json]"}))
        sys.exit(1)

    try:
        post_url = sys.argv[1]
        cost_per_spot = float(sys.argv[2])
        total_spots = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] != 'null' and not sys.argv[3].startswith('[') else None
        
        # Parse existing comment IDs from 4th argument (JSON array)
        existing_comment_ids = []
        if len(sys.argv) > 4:
            try:
                existing_comment_ids = json.loads(sys.argv[4])
            except:
                pass
        elif len(sys.argv) > 3 and sys.argv[3].startswith('['):
            # If 3rd arg is a JSON array, it's the existing_comment_ids (no total_spots)
            try:
                existing_comment_ids = json.loads(sys.argv[3])
            except:
                pass

        print(f"📊 Filtering out {len(existing_comment_ids)} already-processed comment IDs", file=sys.stderr)

        result = parse_reddit_post(post_url, cost_per_spot, total_spots)
        
        # FILTER OUT already-processed comments BEFORE returning
        if existing_comment_ids:
            existing_ids_set = set(existing_comment_ids)
            original_count = len(result)
            result = [p for p in result if p.get('commentId') not in existing_ids_set]
            filtered_count = original_count - len(result)
            print(f"✅ Filtered out {filtered_count} already-processed comments. {len(result)} new comments to parse.", file=sys.stderr)

        print(json.dumps({"ok": True, "participants": result}))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(1)
