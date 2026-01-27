#!/usr/bin/env python3
"""
Quick test script to verify Gmail SMTP password reset email functionality
Run this to test if your EMAIL_PASSWORD is configured correctly
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load from environment or set manually for testing
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USER = os.environ.get("EMAIL_USER", "takobot.donotreply@gmail.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "oyrgpyematbmjyjk")  # Set your 16-char app password
EMAIL_FROM = os.environ.get("EMAIL_FROM", EMAIL_USER)
TEST_TO_EMAIL = "takobot.donotreply@gmail.com"  # Change this to your test email

def test_email():
    """Send a test password reset email"""
    print("=" * 70)
    print("🧪 TESTING PASSWORD RESET EMAIL")
    print("=" * 70)
    
    if not EMAIL_PASSWORD:
        print("❌ ERROR: EMAIL_PASSWORD is not set!")
        print("")
        print("Set it in your environment:")
        print("  export EMAIL_PASSWORD='your_16_char_app_password'")
        print("")
        print("Or edit this script and set it manually")
        return False
    
    try:
        # Create test message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "�� PokemonRaffles - Password Reset Test"
        msg['From'] = EMAIL_FROM
        msg['To'] = TEST_TO_EMAIL
        
        # Test reset URL
        test_token = "TEST_TOKEN_12345"
        reset_url = f"http://localhost:8000/reset-password?token={test_token}"
        
        # Email HTML
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto;">
              <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2px; border-radius: 12px;">
                <div style="background: white; padding: 40px 30px; border-radius: 10px;">
                  <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #667eea; margin: 0; font-size: 28px;">🎮 PokemonRaffles</h1>
                    <p style="color: #764ba2; margin: 5px 0 0 0; font-size: 14px;">Test Email - Password Reset System</p>
                  </div>
                  
                  <h2 style="color: #333; margin-bottom: 20px;">✅ Email Configuration Test</h2>
                  
                  <p style="color: #666; line-height: 1.6;">
                    Hello <strong>Test User</strong>,
                  </p>
                  
                  <p style="color: #666; line-height: 1.6;">
                    This is a test email to verify your Gmail SMTP configuration is working correctly.
                  </p>
                  
                  <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="display: inline-block; 
                              background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; 
                              padding: 14px 40px; 
                              text-decoration: none; 
                              border-radius: 8px; 
                              font-weight: bold;
                              font-size: 16px;
                              box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);">
                      Test Reset Button
                    </a>
                  </div>
                  
                  <div style="background: #f8f9ff; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="color: #667eea; margin: 0; font-size: 14px;">
                      <strong>✅ Configuration Details:</strong>
                    </p>
                    <ul style="color: #666; font-size: 13px;">
                      <li>SMTP Host: {EMAIL_HOST}</li>
                      <li>SMTP Port: {EMAIL_PORT}</li>
                      <li>From Email: {EMAIL_FROM}</li>
                      <li>Test Token: {test_token}</li>
                    </ul>
                  </div>
                  
                  <div style="margin-top: 30px; text-align: center;">
                    <p style="color: #999; font-size: 12px; margin: 0;">
                      PokemonRaffles Password Reset Test 🐙<br>
                      If you received this, your email configuration is working!
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        # Connect and send
        print(f"")
        print(f"📧 Connecting to {EMAIL_HOST}:{EMAIL_PORT}...")
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        
        print(f"🔐 Logging in as {EMAIL_USER}...")
        print(f"    (Password: {EMAIL_PASSWORD[:4]}****)")
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        
        print(f"📨 Sending test email to {TEST_TO_EMAIL}...")
        server.sendmail(EMAIL_FROM, TEST_TO_EMAIL, msg.as_string())
        
        server.quit()
        
        print("")
        print("=" * 70)
        print("✅ SUCCESS! Email sent successfully!")
        print("=" * 70)
        print("")
        print(f"📬 Check your inbox: {TEST_TO_EMAIL}")
        print("🎉 Your password reset email system is working!")
        print("")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print("")
        print("=" * 70)
        print("❌ SMTP AUTHENTICATION FAILED")
        print("=" * 70)
        print("")
        print(f"Error: {e}")
        print("")
        print("Troubleshooting:")
        print("1. Make sure you're using a Gmail App Password, not your regular password")
        print("2. Generate one here: https://myaccount.google.com/apppasswords")
        print("3. The password should be 16 characters without spaces")
        print("")
        print(f"Current EMAIL_PASSWORD: {EMAIL_PASSWORD[:4]}****")
        print("")
        return False
        
    except Exception as e:
        print("")
        print("=" * 70)
        print("❌ ERROR")
        print("=" * 70)
        print("")
        print(f"Error: {e}")
        print("")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("")
    print("🚀 Starting password reset email test...")
    print("")
    print("Configuration:")
    print(f"  EMAIL_HOST: {EMAIL_HOST}")
    print(f"  EMAIL_PORT: {EMAIL_PORT}")
    print(f"  EMAIL_USER: {EMAIL_USER}")
    print(f"  EMAIL_PASSWORD: {'SET (' + EMAIL_PASSWORD[:4] + '****)' if EMAIL_PASSWORD else 'NOT SET!'}")
    print(f"  TEST_TO_EMAIL: {TEST_TO_EMAIL}")
    print("")
    
    success = test_email()
    
    if success:
        print("Next steps:")
        print("1. Run the database migration: psql -U postgres -d raffle_manager -f add_password_reset_tokens.sql")
        print("2. Add email to your test user: UPDATE users SET email = 'test@example.com' WHERE username = 'testuser';")
        print("3. Restart FastAPI: uvicorn app.main:app --reload --port 8000")
        print("4. Test the forgot password flow at http://localhost:8000/forgot-password")
        print("")
    else:
        print("Fix the EMAIL_PASSWORD issue and try again!")
        print("")
