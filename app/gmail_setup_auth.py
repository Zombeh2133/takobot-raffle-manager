"""
Gmail OAuth Setup Script (Run once per user)
Generates the gmail_token.json file needed for headless scanning
"""

import sys
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def setup_gmail_auth(username: str):
    """
    Interactive OAuth setup for Gmail (run this on your local machine or via SSH with X11 forwarding)
    """
    base_dir = Path(__file__).resolve().parent / "data" / "users" / username
    creds_file = base_dir / "gmail_credentials.json"
    token_file = base_dir / "gmail_token.json"
    
    if not creds_file.exists():
        print(f"❌ Error: Gmail credentials not found at {creds_file}")
        print("Please upload gmail_credentials.json in Settings first.")
        return False
    
    print(f"🔐 Starting Gmail OAuth setup for user: {username}")
    print(f"📂 Credentials: {creds_file}")
    
    try:
        # Try local server flow first
        flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
        
        try:
            # Try to run local server (works if you have X11 forwarding or local GUI)
            print("\n🌐 Opening browser for authentication...")
            creds = flow.run_local_server(port=0)
        except Exception as e:
            # Fallback to console-based flow
            print("\n⚠️  Could not open browser. Using console-based authentication.")
            print("\n📋 Follow these steps:")
            print("1. Open this URL in your browser:")
            
            # Generate auth URL
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
            auth_url, _ = flow.authorization_url(prompt='consent')
            print(f"\n{auth_url}\n")
            
            print("2. Authorize the application")
            print("3. Copy the authorization code from the browser")
            
            auth_code = input("\n4. Paste the authorization code here: ").strip()
            
            if not auth_code:
                print("❌ No authorization code provided")
                return False
            
            # Exchange code for credentials
            flow.fetch_token(code=auth_code)
            creds = flow.credentials
        
        # Save credentials
        token_file.write_text(creds.to_json())
        
        print(f"\n✅ Success! Gmail authentication token saved to:")
        print(f"   {token_file}")
        print(f"\n🎉 You can now use the 'Scan Email' feature!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during authentication: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 -m app.gmail_setup_auth <username>")
        print("Example: python3 -m app.gmail_setup_auth maki")
        sys.exit(1)
    
    username = sys.argv[1]
    success = setup_gmail_auth(username)
    sys.exit(0 if success else 1)
