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

# Import the original parser functions
from reddit_parser import (
    fetch_reddit_comments,
    parse_spots_with_ai_batch,
    parse_spots_regex,
    is_bot_confirmation,
    has_payment_confirmation,
    OPENAI_API_KEY,
    USE_AI_PARSING
)

def extract_spots_from_host_comment(text: str) -> List[int]:
    """Extract spot numbers from host 'You got X, Y, Z' confirmation
    
    Uses AI to parse the numbers after 'You got' in the host's reply.
    Returns list of spot numbers assigned.
    """
    if not OPENAI_API_KEY or not USE_AI_PARSING:
        # Fallback to regex if no AI available
        return extract_spots_regex(text)
    
    try:
        print(f"🎯 Parsing host assignment: {text[:60]}...", file=sys.stderr)
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
                        'content': '''You are parsing a raffle host's spot assignment confirmation.
The host comment contains "You got X, Y, Z" where X, Y, Z are the specific spot numbers assigned.

Extract ONLY the spot numbers that appear after "You got" and return them as a JSON array of integers.

Examples:
"You got 10, 13, 25" → [10, 13, 25]
"You got 5" → [5]
"You got 1, 2, 3, 4, 5" → [1, 2, 3, 4, 5]
"You got spots 12, 45, 67" → [12, 45, 67]

Return ONLY a JSON array of integers. Nothing else.
If no spots are found, return an empty array: []'''
                    },
                    {
                        'role': 'user',
                        'content': text
                    }
                ],
                'temperature': 0,
                'max_tokens': 100
            },
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            spots = json.loads(content)
            if isinstance(spots, list) and all(isinstance(s, int) for s in spots):
                print(f"✅ Extracted {len(spots)} spot(s) from host comment", file=sys.stderr)
                return spots
            else:
                print(f"⚠️ Invalid AI response format, using regex fallback", file=sys.stderr)
                return extract_spots_regex(text)
        else:
            print(f"⚠️ AI call failed, using regex fallback", file=sys.stderr)
            return extract_spots_regex(text)
            
    except Exception as e:
        print(f"⚠️ AI error: {str(e)}, using regex fallback", file=sys.stderr)
        return extract_spots_regex(text)

def extract_spots_regex(text: str) -> List[int]:
    """Fallback regex to extract spot numbers from 'You got X, Y, Z'"""
    if not text:
        return []
    
    # Look for "You got" followed by numbers
    match = re.search(r'you got (.+?)(?:\n|$)', text.lower())
    if not match:
        return []
    
    # Extract all numbers from that line
    numbers_text = match.group(1)
    # Find all numbers (could be comma-separated, space-separated, etc.)
    numbers = [int(n) for n in re.findall(r'\d+', numbers_text)]
    
    return numbers

def parse_reddit_post_optimized(
    post_url: str, 
    cost_per_spot: int, 
    total_spots: Optional[int] = None,
    existing_comment_ids: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Optimized parser that:
    1. Parses ALL participant comments for the activity table
    2. Uses HOST 'You got' confirmations for actual spot assignments
    3. Skips AI calls for already-processed comments
    
    Args:
        post_url: Reddit post URL
        cost_per_spot: Cost per raffle spot
        total_spots: Optional total spots limit
        existing_comment_ids: List of comment IDs that have already been parsed
    """
    comments, op_author = fetch_reddit_comments(post_url)
    
    # Convert to set for faster lookup
    existing_ids_set = set(existing_comment_ids) if existing_comment_ids else set()

    # ============ PART 1: Parse participant comments for activity table ============
    participant_comments = []
    comments_to_parse = []
    comment_indices_to_parse = []
    
    for i, comment in enumerate(comments):
        author = comment.get("author", "")
        comment_id = comment.get("id", "")
        body = comment.get("body", "")
        is_submitter = comment.get("is_submitter", False)
        reply_texts = comment.get("reply_texts", [])
        created_utc = comment.get("created_utc", 0)
        
        # Skip deleted/removed comments and AutoModerator
        if not author or author in ["[deleted]", "[removed]", "AutoModerator"]:
            continue
        
        # Skip host comments (we process these separately)
        if is_submitter or author == op_author:
            continue
        
        # Skip bot confirmation messages
        if is_bot_confirmation(body):
            continue
        
        # Skip comments that have payment confirmation replies
        if has_payment_confirmation(reply_texts):
            continue
        
        # Store participant comment info
        participant_comments.append({
            "index": i,
            "comment_id": comment_id,
            "author": author,
            "body": body,
            "created_utc": created_utc,
            "is_new": comment_id not in existing_ids_set
        })
        
        # Only parse NEW comments with AI
        if comment_id not in existing_ids_set:
            comments_to_parse.append(body)
            comment_indices_to_parse.append(len(participant_comments) - 1)
    
    print(f"📊 Participant comments: {len(participant_comments)}, Already parsed: {len(existing_ids_set)}, New to parse: {len(comments_to_parse)}", file=sys.stderr)

    # Parse spot requests ONLY for new comments (for display purposes)
    spot_results_map = {}
    if comments_to_parse:
        if USE_AI_PARSING and OPENAI_API_KEY:
            print(f"🤖 Using AI to parse {len(comments_to_parse)} NEW participant comments (saving {len(existing_ids_set)} API calls!)", file=sys.stderr)
            new_spot_results = parse_spots_with_ai_batch(comments_to_parse)
        else:
            new_spot_results = [parse_spots_regex(body) for body in comments_to_parse]
        
        # Map results back to their indices
        for idx, result in zip(comment_indices_to_parse, new_spot_results):
            spot_results_map[idx] = result
    else:
        print(f"✅ No new participant comments to parse!", file=sys.stderr)

    # ============ PART 2: Parse HOST confirmations for actual spot assignments ============
    # Find all host "You got" comments
    host_confirmations = []
    for comment in comments:
        is_submitter = comment.get("is_submitter", False)
        author = comment.get("author", "")
        body = comment.get("body", "")
        parent_id = comment.get("parent_id", "")
        
        # Only process host comments
        if not (is_submitter or author == op_author):
            continue
        
        # Check if it's a "You got" confirmation
        if not re.search(r'\byou got\b', body, re.IGNORECASE):
            continue
        
        # Extract spot numbers from the confirmation
        assigned_spots = extract_spots_from_host_comment(body)
        
        if assigned_spots:
            # Extract the comment ID from parent_id (format: "t1_commentid")
            parent_comment_id = parent_id.split("_")[-1] if parent_id else ""
            
            host_confirmations.append({
                "parent_comment_id": parent_comment_id,
                "assigned_spots": assigned_spots
            })
            print(f"🎯 Host confirmed {len(assigned_spots)} spot(s) for parent comment {parent_comment_id}", file=sys.stderr)
    
    print(f"📋 Found {len(host_confirmations)} host confirmations", file=sys.stderr)

    # ============ PART 3: Build participant list with spot assignments ============
    participants = []
    
    for pc_idx, pc in enumerate(participant_comments):
        comment_id = pc["comment_id"]
        author = pc["author"]
        body = pc["body"]
        created_utc = pc["created_utc"]
        
        # Find if there's a host confirmation for this comment
        assigned_spots = []
        for confirmation in host_confirmations:
            if confirmation["parent_comment_id"] == comment_id:
                assigned_spots = confirmation["assigned_spots"]
                break
        
        # Determine spot count
        if assigned_spots:
            # Use actual assigned spots from host confirmation
            spot_count = len(assigned_spots)
            print(f"✅ {author}: Using host-confirmed {spot_count} spot(s)", file=sys.stderr)
        elif pc_idx in spot_results_map:
            # Use parsed request (for new comments without host confirmation yet)
            found, parsed_count = spot_results_map[pc_idx]
            spot_count = parsed_count if (found and parsed_count is not None) else 0
            print(f"⏳ {author}: Using requested {spot_count} spot(s) (awaiting host confirmation)", file=sys.stderr)
        else:
            # Skip already-processed comments that don't have new data
            continue
        
        if spot_count > 0:
            participants.append({
                "redditUser": author,
                "name": "",  # Will be filled by name mapping
                "comment": body[:100],
                "spots": spot_count,
                "owed": spot_count * cost_per_spot,
                "paid": False,
                "created_utc": created_utc,
                "commentId": comment_id,
                "assignedSpots": assigned_spots  # Include actual spot numbers if confirmed
            })

    # Sort by timestamp descending (newest first = oldest at bottom)
    participants.sort(key=lambda p: p.get("created_utc", 0), reverse=True)

    # ============ ENFORCE SPOT LIMIT ============
    if total_spots is not None and total_spots > 0:
        running_total = 0
        for i in range(len(participants) - 1, -1, -1):  # Iterate from oldest to newest
            requested_spots = participants[i]["spots"]
            
            # Check if this request would exceed the limit
            if running_total >= total_spots:
                participants[i]["spots"] = 0
                participants[i]["owed"] = 0
            elif running_total + requested_spots > total_spots:
                remaining = total_spots - running_total
                participants[i]["spots"] = remaining
                participants[i]["owed"] = remaining * cost_per_spot
                running_total = total_spots
            else:
                running_total += requested_spots

    # ============ HANDLE "CLOSE" or "CLOSER" LOGIC ============
    if total_spots is not None and total_spots > 0:
        close_index = -1
        for i, p in enumerate(participants):
            if p["spots"] == 0 and re.search(r'\b(close|closer)\b', p["comment"], re.IGNORECASE):
                close_index = i
                break
        
        if close_index >= 0:
            spots_before_close = sum(p["spots"] for i, p in enumerate(participants) if i > close_index)
            remaining_spots = max(0, total_spots - spots_before_close)
            
            participants[close_index]["spots"] = remaining_spots
            participants[close_index]["owed"] = remaining_spots * cost_per_spot
            
            for i in range(close_index):
                participants[i]["spots"] = 0
                participants[i]["owed"] = 0

    return participants

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"ok": False, "error": "Usage: reddit_parser_optimized.py <post_url> <cost_per_spot> [total_spots] [existing_comment_ids_json]"}))
        sys.exit(1)

    try:
        post_url = sys.argv[1]
        cost_per_spot = int(sys.argv[2])
        total_spots = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else None
        
        # Parse existing comment IDs from JSON (if provided as 4th argument)
        existing_comment_ids = None
        if len(sys.argv) > 4:
            try:
                existing_comment_ids = json.loads(sys.argv[4])
            except json.JSONDecodeError:
                print(f"⚠️ Could not parse existing comment IDs, parsing all comments", file=sys.stderr)

        result = parse_reddit_post_optimized(post_url, cost_per_spot, total_spots, existing_comment_ids)

        print(json.dumps({"ok": True, "participants": result}))
    except Exception as e:
        import traceback
        print(json.dumps({"ok": False, "error": str(e), "traceback": traceback.format_exc()}))
        sys.exit(1)
