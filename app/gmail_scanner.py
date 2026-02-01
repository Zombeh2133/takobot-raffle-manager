#!/usr/bin/env python3
"""
Gmail PayPal Payment Scanner
Scans Gmail for PayPal payment notifications and matches them to raffle participants
"""

import os
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
from email import message_from_bytes

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# PostgreSQL connection
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:makii@localhost:5432/raffle_manager")

def get_pg_connection():
    """Get PostgreSQL connection"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def get_gmail_service(username: str):
    """
    Authenticate with Gmail API using stored credentials
    
    Args:
        username: The username whose credentials to use
        
    Returns:
        Gmail API service object
    """
    # Paths for this user's credentials
    base_dir = Path(__file__).resolve().parent / "data" / "users" / username
    creds_file = base_dir / "gmail_credentials.json"
    token_file = base_dir / "gmail_token.json"
    
    if not creds_file.exists():
        raise FileNotFoundError(f"Gmail credentials not found for user '{username}'. Please upload credentials in Settings.")
    
    creds = None
    
    # Load existing token
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    
    # If no valid credentials, refresh or get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed credentials
            token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        else:
            # Need to do initial OAuth flow - this should be done via browser
            raise Exception("Gmail OAuth token not found or expired. Please complete OAuth authorization in Settings.")
    
    return build('gmail', 'v1', credentials=creds)


def get_oauth_url(username: str, redirect_uri: str = "http://localhost:8080") -> dict:
    """
    Generate OAuth authorization URL for browser-based flow
    
    Args:
        username: The username whose credentials to use
        redirect_uri: The redirect URI (should match OAuth client config)
        
    Returns:
        Dict with authorization URL
    """
    base_dir = Path(__file__).resolve().parent / "data" / "users" / username
    creds_file = base_dir / "gmail_credentials.json"
    
    if not creds_file.exists():
        raise FileNotFoundError(f"Gmail credentials not found for user '{username}'. Please upload credentials in Settings.")
    
    # Use out-of-band (OOB) flow - Google will display the code on their page
    flow = InstalledAppFlow.from_client_secrets_file(
        str(creds_file), 
        SCOPES,
        redirect_uri='urn:ietf:wg:oauth:2.0:oob'
    )
    
    # Generate authorization URL
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    return {
        'auth_url': auth_url,
        'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob'
    }


def complete_oauth_flow(username: str, authorization_response: str) -> dict:
    """
    Complete OAuth flow using authorization code from browser redirect
    
    Args:
        username: The username whose credentials to use
        authorization_response: Full redirect URL with authorization code OR just the code
        
    Returns:
        Dict with success status
    """
    base_dir = Path(__file__).resolve().parent / "data" / "users" / username
    creds_file = base_dir / "gmail_credentials.json"
    token_file = base_dir / "gmail_token.json"
    
    if not creds_file.exists():
        raise FileNotFoundError(f"Gmail credentials not found for user '{username}'.")
    
    # Use OOB flow to match the get_oauth_url configuration
    flow = InstalledAppFlow.from_client_secrets_file(
        str(creds_file), 
        SCOPES,
        redirect_uri='urn:ietf:wg:oauth:2.0:oob'
    )
    
    # For OOB flow, the authorization_response is just the code (not a URL)
    # But we need to handle both cases for backward compatibility
    if authorization_response.startswith('http'):
        # It's a URL, extract the code
        import urllib.parse
        parsed = urllib.parse.urlparse(authorization_response)
        params = urllib.parse.parse_qs(parsed.query)
        code = params.get('code', [None])[0]
        if not code:
            raise ValueError("No authorization code found in URL")
    else:
        # It's just the code
        code = authorization_response.strip()
    
    # Exchange authorization code for access token
    flow.fetch_token(code=code)
    creds = flow.credentials
    
    # Save credentials
    token_file.parent.mkdir(parents=True, exist_ok=True)
    with open(token_file, 'w') as token:
        token.write(creds.to_json())
    
    return {'success': True, 'message': 'OAuth flow completed successfully'}


def extract_paypal_info(body: str, subject: str) -> dict:
    """
    Extract PayPal payment information from email body
    
    Args:
        body: Email body text
        subject: Email subject line
        
    Returns:
        Dict with payer_name and amount (no transaction_id)
    """
    info = {
        'payer_name': None,
        'amount': None
    }
    
    # Extract payer name (from subject or body)
    # Subject patterns: "John Doe sent you $5.00"
    subject_patterns = [
        r'^(.+?)\s+sent\s+you',
        r'^(.+?)\s+paid\s+you',
        r'Payment\s+from\s+(.+?)\s*[-–]'
    ]
    
    for pattern in subject_patterns:
        match = re.search(pattern, subject, re.IGNORECASE)
        if match:
            info['payer_name'] = match.group(1).strip()
            break
    
    # If not in subject, try body
    if not info['payer_name']:
        body_patterns = [
            r'From:\s*([A-Za-z\s]+)\s*\n',
            r'Sender:\s*([A-Za-z\s]+)',
            r'Name:\s*([A-Za-z\s]+)'
        ]
        
        for pattern in body_patterns:
            match = re.search(pattern, body)
            if match:
                info['payer_name'] = match.group(1).strip()
                break
    
    # Extract amount
    # Look for patterns like: "$5.00", "5.00 USD", "Amount: $5.00"
    amount_patterns = [
        r'\$(\d+\.\d{2})\s*USD',
        r'Amount:\s*\$(\d+\.\d{2})',
        r'sent\s+you\s+\$(\d+\.\d{2})',
        r'paid\s+you\s+\$(\d+\.\d{2})',
        r'\$(\d+\.\d{2})'
    ]
    
    for pattern in amount_patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            try:
                info['amount'] = float(match.group(1))
                break
            except ValueError:
                continue
    
    return info

def get_paypal_emails(service, days_back: int = None, since_timestamp: str = None):
    """
    Fetch PayPal notification emails from Gmail
    
    Args:
        service: Gmail API service
        days_back: How many days back to search (optional, used if since_timestamp not provided)
        since_timestamp: ISO 8601 timestamp to search from (optional, preferred over days_back)
        
    Returns:
        List of email data dicts
    """
    # Calculate date filter
    if since_timestamp:
        # Parse ISO timestamp and convert to Gmail format (YYYY/MM/DD)
        # Handle ISO 8601 format with 'Z' or timezone offset
        dt_str = since_timestamp.replace('Z', '+00:00')
        dt = datetime.fromisoformat(dt_str)
        after_date = dt.strftime('%Y/%m/%d')
    elif days_back:
        after_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')
    else:
        # Default to 7 days
        after_date = (datetime.now() - timedelta(days=7)).strftime('%Y/%m/%d')
    
    # Search query for PayPal emails
    query = f'from:service@paypal.com after:{after_date} subject:(sent you OR received OR paid you)'
    
    try:
        results = service.users().messages().list(userId='me', q=query, maxResults=100).execute()
        messages = results.get('messages', [])
        
        emails = []
        
        for msg in messages:
            # Get full message
            message = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            
            # Extract headers
            headers = message['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
            date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
            
            # Parse email body
            body = ''
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        if 'data' in part['body']:
                            body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                            break
            elif 'body' in message['payload'] and 'data' in message['payload']['body']:
                body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8', errors='ignore')
            
            # Extract PayPal info
            paypal_info = extract_paypal_info(body, subject)
            
            if paypal_info['amount'] is not None:
                emails.append({
                    'subject': subject,
                    'date': date_str,
                    'body': body[:500],  # First 500 chars for debugging
                    'payer_name': paypal_info['payer_name'],
                    'amount': paypal_info['amount'],
                    'message_id': msg['id']  # Use Gmail message ID instead
                })
        
        return emails
        
    except Exception as e:
        raise Exception(f"Failed to fetch emails: {str(e)}")

def match_payment_to_participant(payment: dict, participants: list) -> dict:
    """
    Match a payment to a participant
    
    Matching rules:
    - If participant has a name: MUST match both amount AND name
    - If participant has no name: Match by amount only
    
    Returns dict with:
        - matched: bool
        - participant: dict or None
        - confidence: int (0-100)
        - reason: str
    """
    amount = payment['amount']
    payer_name = payment['payer_name'] or ''
    
    # Normalize payer name for comparison
    payer_name_lower = payer_name.lower().strip()
    
    # Try to find exact matches first
    best_match = None
    best_confidence = 0
    best_reason = ''
    
    for participant in participants:
        # Skip already paid participants
        if participant.get('paid', False):
            continue
        
        # Calculate expected amount
        expected_amount = participant.get('spots', 0) * participant.get('costPerSpot', 0)
        
        # Check if amount matches (within $0.50 tolerance for fees)
        amount_match = abs(amount - expected_amount) <= 0.50
        
        if not amount_match:
            continue
        
        # Check if participant has a name
        participant_name = participant.get('name', '').strip()
        
        if participant_name:
            # MUST match both amount AND name
            participant_name_lower = participant_name.lower()
            
            # Check for name match (exact, contains, or reverse contains)
            name_match = (
                payer_name_lower == participant_name_lower or
                payer_name_lower in participant_name_lower or
                participant_name_lower in payer_name_lower
            )
            
            if name_match:
                confidence = 95  # High confidence - both amount and name match
                reason = f"Amount (${amount}) and name ({payer_name}) match"
                if confidence > best_confidence:
                    best_match = participant
                    best_confidence = confidence
                    best_reason = reason
        else:
            # No name - match by amount only (lower confidence)
            confidence = 70  # Medium confidence - amount only
            reason = f"Amount (${amount}) matches, no name verification"
            if confidence > best_confidence:
                best_match = participant
                best_confidence = confidence
                best_reason = reason
    
    return {
        'matched': best_match is not None,
        'participant': best_match,
        'confidence': best_confidence,
        'reason': best_reason
    }

def scan_and_match_payments(username: str, raffle_id: int, days_back: int = None, since_timestamp: str = None):
    """
    Main function: Scan Gmail for PayPal payments and match to raffle participants
    
    Args:
        username: Username of the raffle host
        raffle_id: Active raffle ID to match payments for
        days_back: How many days back to search emails (optional)
        since_timestamp: ISO 8601 timestamp to search from (optional, preferred)
        
    Returns:
        Dict with results
    """
    try:
        # Get Gmail service
        service = get_gmail_service(username)
        
        # Fetch PayPal emails
        emails = get_paypal_emails(service, days_back=days_back, since_timestamp=since_timestamp)
        
        if not emails:
            if since_timestamp:
                msg = f'No PayPal payment emails found since raffle creation'
            else:
                msg = 'No PayPal payment emails found in the specified time range'
            return {
                'ok': True,
                'message': msg,
                'matched': 0,
                'processed': 0
            }
        
        # Get raffle data from PostgreSQL
        conn = get_pg_connection()
        cur = conn.cursor()
        
        # Get user_id
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_row = cur.fetchone()
        if not user_row:
            conn.close()
            return {'ok': False, 'error': f"User '{username}' not found"}
        
        user_id = user_row['id']
        
        # Get active raffle
        cur.execute("""
            SELECT id, participants, cost_per_spot, total_spots 
            FROM active_raffle 
            WHERE id = %s
        """, (raffle_id,))
        
        raffle = cur.fetchone()
        if not raffle:
            conn.close()
            return {'ok': False, 'error': f"Raffle {raffle_id} not found"}
        
        participants = raffle['participants'] or []
        cost_per_spot = raffle.get('cost_per_spot', 0)
        
        # Add cost_per_spot to each participant for matching logic
        for p in participants:
            p['costPerSpot'] = cost_per_spot
        
        # Calculate time threshold for duplicate checking
        if since_timestamp:
            # Parse ISO timestamp - handle 'Z' timezone notation
            dt_str = since_timestamp.replace('Z', '+00:00')
            time_threshold = datetime.fromisoformat(dt_str)
        elif days_back:
            time_threshold = datetime.now() - timedelta(days=days_back)
        else:
            time_threshold = datetime.now() - timedelta(days=7)
        
        # Process each email
        matched_count = 0
        processed_count = 0
        results = []
        
        for email in emails:
            # Check if payment already processed (by payer name, amount, and raffle_id)
            # This prevents duplicate processing without needing transaction_id
            cur.execute("""
                SELECT id FROM paypal_transactions 
                WHERE user_id = %s 
                  AND raffle_id = %s
                  AND payer_name = %s 
                  AND amount = %s
                  AND email_date >= %s
            """, (user_id, raffle_id, email['payer_name'], email['amount'], time_threshold))
            
            if cur.fetchone():
                results.append({
                    'payer_name': email['payer_name'],
                    'amount': email['amount'],
                    'status': 'skipped',
                    'reason': 'Already processed (duplicate payment detected)'
                })
                continue
            
            # Try to match payment
            match_result = match_payment_to_participant(email, participants)
            
            if match_result['matched']:
                participant = match_result['participant']
                
                # Mark participant as paid in participants array
                for p in participants:
                    if p['redditUser'] == participant['redditUser']:
                        p['paid'] = True
                        break
                
                # Store transaction in database (without transaction_id - it's optional)
                cur.execute("""
                    INSERT INTO paypal_transactions (
                        user_id, raffle_id, payer_name, amount,
                        participant_reddit_user, participant_name,
                        email_subject, email_date, match_confidence
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s)
                """, (
                    user_id, raffle_id,
                    email['payer_name'], email['amount'],
                    participant['redditUser'], participant.get('name', ''),
                    email['subject'], match_result['confidence']
                ))
                
                matched_count += 1
                results.append({
                    'payer_name': email['payer_name'],
                    'status': 'matched',
                    'reddit_user': participant['redditUser'],
                    'amount': email['amount'],
                    'confidence': match_result['confidence'],
                    'reason': match_result['reason']
                })
            else:
                # DON'T store unmatched transactions - they should be rescanned later
                # Only store matched transactions so unmatched emails can be processed again
                results.append({
                    'payer_name': email['payer_name'],
                    'status': 'unmatched',
                    'amount': email['amount'],
                    'reason': 'No matching participant found'
                })
            
            processed_count += 1
        
        # Update raffle participants in database
        cur.execute("""
            UPDATE active_raffle 
            SET participants = %s, updated_at = NOW()
            WHERE id = %s
        """, (json.dumps(participants), raffle_id))
        
        conn.commit()
        conn.close()
        
        return {
            'ok': True,
            'message': f'Processed {processed_count} payments, matched {matched_count}',
            'processed': processed_count,
            'matched': matched_count,
            'results': results
        }
        
    except FileNotFoundError as e:
        return {'ok': False, 'error': str(e)}
    except Exception as e:
        import traceback
        return {
            'ok': False, 
            'error': f'Scanner error: {str(e)}',
            'trace': traceback.format_exc()
        }

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 3:
        print(json.dumps({
            'ok': False,
            'error': 'Usage: python gmail_scanner.py <username> <raffle_id> [days_back]'
        }))
        sys.exit(1)
    
    username = sys.argv[1]
    raffle_id = int(sys.argv[2])
    days_back = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    
    result = scan_and_match_payments(username, raffle_id, days_back)
    print(json.dumps(result, indent=2))
