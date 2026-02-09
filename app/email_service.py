"""
Email Service for TCG Nakama
Handles sending daily analytics reports via SMTP.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import pytz


def get_smtp_config() -> dict:
    """Get SMTP configuration from environment variables."""
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "email": os.getenv("SMTP_EMAIL", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "recipient": os.getenv("REPORT_RECIPIENT", os.getenv("ADMIN_EMAIL", "")),
    }


def send_email(subject: str, html_content: str, to_email: str = None) -> bool:
    """
    Send an email using SMTP.
    
    Args:
        subject: Email subject line
        html_content: HTML body of the email
        to_email: Recipient email (defaults to REPORT_RECIPIENT)
    
    Returns:
        True if sent successfully, False otherwise
    """
    config = get_smtp_config()
    
    if not config["email"] or not config["password"]:
        print("[EMAIL] SMTP credentials not configured. Skipping email send.")
        return False
    
    recipient = to_email or config["recipient"]
    if not recipient:
        print("[EMAIL] No recipient specified. Skipping email send.")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config["email"]
        msg["To"] = recipient
        
        # Attach HTML content
        html_part = MIMEText(html_content, "html")
        msg.attach(html_part)
        
        # Connect and send
        with smtplib.SMTP(config["host"], config["port"]) as server:
            server.starttls()
            server.login(config["email"], config["password"])
            server.sendmail(config["email"], recipient, msg.as_string())
        
        print(f"[EMAIL] Report sent successfully to {recipient}")
        return True
        
    except Exception as e:
        print(f"[EMAIL] Failed to send email: {e}")
        return False


def generate_daily_report_html(data: dict) -> str:
    """
    Generate HTML content for daily analytics report.
    
    Args:
        data: Dictionary containing analytics data
    
    Returns:
        HTML string for the email body
    """
    jst = pytz.timezone("Asia/Tokyo")
    now = datetime.now(jst)
    date_str = now.strftime("%Y年%m月%d日")
    
    # Build top products section
    top_products_html = ""
    for i, product in enumerate(data.get("top_products", [])[:5], 1):
        top_products_html += f"<tr><td>{i}</td><td>{product['title']}</td><td>¥{product['price']:,}</td></tr>"
    
    if not top_products_html:
        top_products_html = "<tr><td colspan='3' style='text-align:center;color:#888;'>No products sold</td></tr>"
    
    # Build top spenders section
    top_spenders_html = ""
    for i, spender in enumerate(data.get("top_spenders", [])[:3], 1):
        top_spenders_html += f"<tr><td>{i}</td><td>{spender['name']}</td><td>¥{spender['total']}</td></tr>"
    
    if not top_spenders_html:
        top_spenders_html = "<tr><td colspan='3' style='text-align:center;color:#888;'>No customer data</td></tr>"
    
    # Build trending searches section
    trending_html = ""
    for search in data.get("trending_searches", [])[:5]:
        trending_html += f"<span style='display:inline-block;background:#f0f0f0;padding:4px 12px;border-radius:20px;margin:4px;'>{search['query']} ({search['count']})</span>"
    
    if not trending_html:
        trending_html = "<span style='color:#888;'>No search data yet</span>"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, #0A0A0A 0%, #1a1a2e 100%); color: white; padding: 30px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 24px; letter-spacing: 2px; }}
            .header p {{ margin: 10px 0 0; opacity: 0.7; font-size: 14px; }}
            .content {{ padding: 30px; }}
            .section {{ margin-bottom: 30px; }}
            .section-title {{ font-size: 12px; text-transform: uppercase; letter-spacing: 2px; color: #888; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
            .metric {{ display: inline-block; text-align: center; padding: 15px 25px; background: #f8f9fa; border-radius: 8px; margin: 5px; }}
            .metric-value {{ font-size: 28px; font-weight: bold; color: #257bf4; }}
            .metric-label {{ font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 1px; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
            th {{ font-size: 11px; text-transform: uppercase; color: #888; }}
            .footer {{ background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #888; }}
            .psa-badge {{ display: inline-block; background: linear-gradient(135deg, #ffd700, #ff9500); color: #000; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 TCG NAKAMA</h1>
                <p>Daily Analytics Report · {date_str}</p>
            </div>
            <div class="content">
                <div class="section">
                    <div class="section-title">Summary</div>
                    <div style="text-align: center;">
                        <div class="metric">
                            <div class="metric-value">{data.get('total_products', 0)}</div>
                            <div class="metric-label">Products</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{data.get('total_orders', 0)}</div>
                            <div class="metric-label">Orders</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{data.get('total_graded', 0)}</div>
                            <div class="metric-label">Graded</div>
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-title">Top 5 Products</div>
                    <table>
                        <tr><th>#</th><th>Product</th><th>Price</th></tr>
                        {top_products_html}
                    </table>
                </div>
                
                <div class="section">
                    <div class="section-title">Top Spenders</div>
                    <table>
                        <tr><th>#</th><th>Customer</th><th>Total</th></tr>
                        {top_spenders_html}
                    </table>
                </div>
                
                <div class="section">
                    <div class="section-title">Trending Searches</div>
                    <div>{trending_html}</div>
                </div>
                
                <div class="section">
                    <div class="section-title">🏆 PSA 10 Candidates</div>
                    <p style="color:#888;font-size:13px;">Cards with highest grading potential:</p>
                    {"".join([f"<p><span class='psa-badge'>{c['score']}%</span> {c['title']} (Grade: {c['grade']})</p>" for c in data.get('psa_candidates', [])[:3]]) or "<p style='color:#888;'>No candidates yet</p>"}
                </div>
            </div>
            <div class="footer">
                <p>This is an automated report from TCG Nakama Admin Dashboard</p>
                <p>ログイン: <a href="http://localhost:8001/admin">Admin Dashboard</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html
