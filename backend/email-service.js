const nodemailer = require('nodemailer');
require('dotenv').config();

// Production email service using Gmail SMTP
class EmailService {
  constructor() {
    this.transporter = null;
    this.init();
  }

  async init() {
    // Check if Gmail credentials are configured
    if (!process.env.EMAIL_USER || !process.env.EMAIL_PASSWORD) {
      console.error('❌ EMAIL_USER and EMAIL_PASSWORD must be set in .env file');
      throw new Error('Email credentials not configured');
    }

    // Use Gmail SMTP from environment variables
    this.transporter = nodemailer.createTransport({
      host: process.env.EMAIL_HOST || 'smtp.gmail.com',
      port: parseInt(process.env.EMAIL_PORT || '587'),
      secure: false, // true for 465, false for other ports
      auth: {
        user: process.env.EMAIL_USER,
        pass: process.env.EMAIL_PASSWORD,
      },
    });

    // Verify connection
    try {
      await this.transporter.verify();
      console.log('✅ Email service initialized successfully with Gmail SMTP');
      console.log(`📧 Sending from: ${process.env.EMAIL_USER}`);
    } catch (error) {
      console.error('❌ Email service verification failed:', error.message);
      throw error;
    }
  }

  async sendPasswordResetEmail(email, username, resetToken) {
    const resetUrl = `http://34.228.57.164:8000/reset-password.html?token=${resetToken}`;

    const mailOptions = {
      from: `"TakoBot" <${process.env.EMAIL_USER}>`,
      to: email,
      subject: 'Password Reset Request - TakoBot',
      html: `
        <!DOCTYPE html>
        <html>
        <head>
          <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .container { max-width: 600px; margin: 0 auto; padding: 20px; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
            .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
            .button { display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }
            .footer { text-align: center; margin-top: 20px; color: #666; font-size: 12px; }
            .warning { background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 20px 0; }
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1>🔐 Password Reset Request</h1>
            </div>
            <div class="content">
              <p>Hi <strong>${username}</strong>,</p>
              <p>We received a request to reset your password for your TakoBot account.</p>
              <p>Click the button below to reset your password:</p>
              <p style="text-align: center;">
                <a href="${resetUrl}" class="button">Reset Password</a>
              </p>
              <p>Or copy and paste this link into your browser:</p>
              <p style="word-break: break-all; background: #fff; padding: 10px; border-radius: 5px;"><a href="${resetUrl}">${resetUrl}</a></p>
              <div class="warning">
                <strong>⏱️ This link will expire in 1 hour.</strong>
              </div>
              <p>If you didn't request this password reset, please ignore this email. Your password will remain unchanged.</p>
              <p>For security reasons, this link can only be used once.</p>
            </div>
            <div class="footer">
              <p>- The TakoBot Team 🐙</p>
              <p>This is an automated message. Please do not reply to this email.</p>
            </div>
          </div>
        </body>
        </html>
      `,
    };

    try {
      const info = await this.transporter.sendMail(mailOptions);
      console.log('✅ Password reset email sent successfully');
      console.log(`📧 To: ${email}`);
      console.log(`📬 Message ID: ${info.messageId}`);
      return info;
    } catch (error) {
      console.error('❌ Failed to send password reset email:', error.message);
      throw error;
    }
  }
}

module.exports = new EmailService();
