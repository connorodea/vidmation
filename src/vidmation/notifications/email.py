"""Email notifier — sends HTML-formatted notifications via Resend or SMTP.

Configuration (env vars with VIDMATION_ prefix):
    VIDMATION_EMAIL_PROVIDER: "resend" | "smtp"  (default: "resend")
    VIDMATION_EMAIL_FROM: sender address
    VIDMATION_EMAIL_TO: comma-separated recipient addresses
    VIDMATION_RESEND_API_KEY: Resend API key (if provider=resend)
    VIDMATION_SMTP_HOST / _PORT / _USER / _PASSWORD: SMTP config
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("vidmation.notifications.email")


# ---------------------------------------------------------------------------
# HTML Templates
# ---------------------------------------------------------------------------

_BASE_STYLE = """
<style>
    body { margin: 0; padding: 0; background: #0a0a0f; color: #e5e7eb; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    .container { max-width: 600px; margin: 0 auto; padding: 32px 24px; }
    .header { text-align: center; padding-bottom: 24px; border-bottom: 1px solid rgba(255,255,255,0.06); margin-bottom: 24px; }
    .logo { display: inline-block; background: linear-gradient(135deg, #6366f1, #4f46e5); color: white; font-weight: bold; font-size: 14px; width: 40px; height: 40px; line-height: 40px; border-radius: 12px; text-align: center; }
    .brand { font-size: 20px; font-weight: 700; color: white; margin-left: 8px; vertical-align: middle; }
    .card { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; padding: 24px; margin-bottom: 16px; }
    .card-title { font-size: 18px; font-weight: 600; color: white; margin: 0 0 8px 0; }
    .card-text { font-size: 14px; color: #9ca3af; line-height: 1.6; margin: 0; }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
    .badge-success { background: rgba(34,197,94,0.15); color: #22c55e; }
    .badge-error { background: rgba(239,68,68,0.15); color: #ef4444; }
    .badge-warning { background: rgba(234,179,8,0.15); color: #eab308; }
    .badge-info { background: rgba(99,102,241,0.15); color: #818cf8; }
    .btn { display: inline-block; padding: 10px 24px; background: #6366f1; color: white; text-decoration: none; border-radius: 10px; font-size: 14px; font-weight: 600; }
    .footer { text-align: center; padding-top: 24px; border-top: 1px solid rgba(255,255,255,0.06); margin-top: 32px; font-size: 12px; color: #6b7280; }
    .stat { display: inline-block; text-align: center; margin: 0 16px; }
    .stat-value { font-size: 24px; font-weight: 700; color: white; }
    .stat-label { font-size: 12px; color: #6b7280; }
</style>
"""

_TEMPLATES: dict[str, str] = {
    "video_complete": """
<!DOCTYPE html><html><head>{style}</head><body>
<div class="container">
    <div class="header">
        <span class="logo">V</span>
        <span class="brand">VIDMATION</span>
    </div>
    <div class="card">
        <h2 class="card-title">{title}</h2>
        <p class="card-text">{message}</p>
        {extra}
    </div>
    <div style="text-align:center; margin-top:24px;">
        <span class="badge badge-success">Video Ready</span>
    </div>
    <div class="footer">VIDMATION &mdash; AI Video Automation</div>
</div>
</body></html>
""",
    "job_failed": """
<!DOCTYPE html><html><head>{style}</head><body>
<div class="container">
    <div class="header">
        <span class="logo">V</span>
        <span class="brand">VIDMATION</span>
    </div>
    <div class="card">
        <h2 class="card-title">{title}</h2>
        <p class="card-text">{message}</p>
        {extra}
    </div>
    <div style="text-align:center; margin-top:24px;">
        <span class="badge badge-error">Job Failed</span>
    </div>
    <div class="footer">VIDMATION &mdash; AI Video Automation</div>
</div>
</body></html>
""",
    "upload_complete": """
<!DOCTYPE html><html><head>{style}</head><body>
<div class="container">
    <div class="header">
        <span class="logo">V</span>
        <span class="brand">VIDMATION</span>
    </div>
    <div class="card">
        <h2 class="card-title">{title}</h2>
        <p class="card-text">{message}</p>
        {extra}
    </div>
    <div style="text-align:center; margin-top:24px;">
        <span class="badge badge-success">Upload Complete</span>
    </div>
    <div class="footer">VIDMATION &mdash; AI Video Automation</div>
</div>
</body></html>
""",
    "cost_alert": """
<!DOCTYPE html><html><head>{style}</head><body>
<div class="container">
    <div class="header">
        <span class="logo">V</span>
        <span class="brand">VIDMATION</span>
    </div>
    <div class="card">
        <h2 class="card-title">{title}</h2>
        <p class="card-text">{message}</p>
        {extra}
    </div>
    <div style="text-align:center; margin-top:24px;">
        <span class="badge badge-warning">Cost Alert</span>
    </div>
    <div class="footer">VIDMATION &mdash; AI Video Automation</div>
</div>
</body></html>
""",
    "default": """
<!DOCTYPE html><html><head>{style}</head><body>
<div class="container">
    <div class="header">
        <span class="logo">V</span>
        <span class="brand">VIDMATION</span>
    </div>
    <div class="card">
        <h2 class="card-title">{title}</h2>
        <p class="card-text">{message}</p>
        {extra}
    </div>
    <div class="footer">VIDMATION &mdash; AI Video Automation</div>
</div>
</body></html>
""",
}


def _render_html(event: str, title: str, message: str, data: dict | None = None) -> str:
    """Render an HTML email from a template."""
    template = _TEMPLATES.get(event, _TEMPLATES["default"])

    extra_parts: list[str] = []
    if data:
        if "youtube_url" in data:
            extra_parts.append(
                f'<p style="margin-top:16px;"><a class="btn" href="{data["youtube_url"]}">View on YouTube</a></p>'
            )
        if "video_id" in data:
            extra_parts.append(
                f'<p style="margin-top:8px; font-size:12px; color:#6b7280;">Video ID: {data["video_id"]}</p>'
            )
        if "current_cost" in data and "budget" in data:
            pct = round((data["current_cost"] / data["budget"]) * 100, 1) if data["budget"] else 0
            extra_parts.append(
                f'<div style="margin-top:16px;">'
                f'<div class="stat"><div class="stat-value">${data["current_cost"]:.2f}</div><div class="stat-label">Current Spend</div></div>'
                f'<div class="stat"><div class="stat-value">${data["budget"]:.2f}</div><div class="stat-label">Budget</div></div>'
                f'<div class="stat"><div class="stat-value">{pct}%</div><div class="stat-label">Used</div></div>'
                f'</div>'
            )

    return template.format(
        style=_BASE_STYLE,
        title=title,
        message=message,
        extra="\n".join(extra_parts),
    )


# ---------------------------------------------------------------------------
# EmailNotifier
# ---------------------------------------------------------------------------

class EmailNotifier:
    """Send email notifications via Resend API or SMTP fallback.

    Reads configuration from environment variables (prefixed VIDMATION_).
    """

    def __init__(self) -> None:
        self.provider = os.getenv("VIDMATION_EMAIL_PROVIDER", "resend").lower()
        self.from_address = os.getenv("VIDMATION_EMAIL_FROM", "noreply@vidmation.io")
        self.to_addresses = [
            addr.strip()
            for addr in os.getenv("VIDMATION_EMAIL_TO", "").split(",")
            if addr.strip()
        ]
        self._resend_api_key = os.getenv("VIDMATION_RESEND_API_KEY", "")
        self._smtp_host = os.getenv("VIDMATION_SMTP_HOST", "")
        self._smtp_port = int(os.getenv("VIDMATION_SMTP_PORT", "587"))
        self._smtp_user = os.getenv("VIDMATION_SMTP_USER", "")
        self._smtp_password = os.getenv("VIDMATION_SMTP_PASSWORD", "")

    @property
    def is_configured(self) -> bool:
        """Check if enough config exists to send emails."""
        if not self.to_addresses:
            return False
        if self.provider == "resend":
            return bool(self._resend_api_key)
        return bool(self._smtp_host)

    def send(
        self,
        event: str,
        title: str,
        message: str,
        data: dict | None = None,
    ) -> bool:
        """Send an email notification.

        Returns True on success, False on failure.
        """
        if not self.is_configured:
            logger.debug("Email notifier not configured, skipping")
            return False

        html_body = _render_html(event, title, message, data)

        try:
            if self.provider == "resend":
                return self._send_resend(title, html_body)
            else:
                return self._send_smtp(title, html_body)
        except Exception:
            logger.error("Failed to send email notification", exc_info=True)
            return False

    def _send_resend(self, subject: str, html_body: str) -> bool:
        """Send via Resend HTTP API."""
        import httpx

        response = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {self._resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": self.from_address,
                "to": self.to_addresses,
                "subject": f"[VIDMATION] {subject}",
                "html": html_body,
            },
            timeout=15.0,
        )
        if response.status_code in (200, 201):
            logger.info("Email sent via Resend to %s", self.to_addresses)
            return True

        logger.error(
            "Resend API error %d: %s", response.status_code, response.text[:500]
        )
        return False

    def _send_smtp(self, subject: str, html_body: str) -> bool:
        """Send via SMTP (TLS)."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[VIDMATION] {subject}"
        msg["From"] = self.from_address
        msg["To"] = ", ".join(self.to_addresses)
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            if self._smtp_user:
                server.login(self._smtp_user, self._smtp_password)
            server.sendmail(self.from_address, self.to_addresses, msg.as_string())

        logger.info("Email sent via SMTP to %s", self.to_addresses)
        return True
