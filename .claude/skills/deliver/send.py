#!/usr/bin/env python3
"""
daily-research-report delivery script.
Reads config.yaml to determine the delivery channel, then sends today's report.
"""

import json
import os
import smtplib
import datetime
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import yaml
except ImportError:
    # Fallback: minimal YAML parser for the delivery.channel field
    yaml = None

TODAY = datetime.date.today().strftime("%Y-%m-%d")
ROOT = Path(__file__).parents[3]
REPORTS_DIR = ROOT / "reports"
TODAY_DIR = REPORTS_DIR / TODAY
LOG_FILE = REPORTS_DIR / "log.txt"
CONFIG_FILE = ROOT / "config.yaml"
PURGE_DAYS = 7


def load_config():
    text = CONFIG_FILE.read_text(encoding="utf-8")
    if yaml:
        return yaml.safe_load(text)
    # Minimal fallback: extract delivery channel
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("channel:"):
            value = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            return {"delivery": {"channel": value}, "name": "Daily Brief"}
    return {"delivery": {"channel": "kindle"}, "name": "Daily Brief"}


def log(entry: str):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = LOG_FILE.read_text(encoding="utf-8") if LOG_FILE.exists() else ""
    LOG_FILE.write_text(f"{entry}\n{existing}", encoding="utf-8")
    print(f"[log] {entry}")


def send_kindle(html_path: Path, report_name: str):
    gmail_user = os.environ["KINDLE_GMAIL_USER"]
    gmail_pass = os.environ["KINDLE_GMAIL_APP_PASS"]
    kindle_email = os.environ["KINDLE_EMAIL"]

    msg = MIMEMultipart()
    msg["From"] = gmail_user
    msg["To"] = kindle_email
    msg["Subject"] = f"{report_name} {TODAY}"

    with open(html_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="report-{TODAY}.html"',
        )
        msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, kindle_email, msg.as_string())
    print(f"[deliver] Kindle -> {kindle_email}")


def send_slack(html_path: Path, report_name: str):
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    md_path = html_path.with_suffix(".md")

    if md_path.exists():
        text = md_path.read_text(encoding="utf-8")
    else:
        text = html_path.read_text(encoding="utf-8")

    # Truncate for Slack's 3000-char block limit
    if len(text) > 2900:
        text = text[:2900] + "\n\n... (truncated)"

    payload = json.dumps({
        "text": f"*{report_name} -- {TODAY}*",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{report_name} -- {TODAY}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            },
        ],
    }).encode("utf-8")

    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        print(f"[deliver] Slack -> {resp.status}")


def send_notion(html_path: Path, report_name: str):
    api_key = os.environ["NOTION_API_KEY"]
    database_id = os.environ["NOTION_DATABASE_ID"]
    md_path = html_path.with_suffix(".md")

    if md_path.exists():
        content = md_path.read_text(encoding="utf-8")
    else:
        content = html_path.read_text(encoding="utf-8")

    # Notion blocks have a 2000-char limit per rich_text element.
    # Split into chunks.
    chunks = [content[i : i + 2000] for i in range(0, len(content), 2000)]
    children = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": chunk}}]
            },
        }
        for chunk in chunks[:100]  # Notion caps at 100 blocks per request
    ]

    payload = json.dumps({
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {"title": [{"text": {"content": f"{report_name} -- {TODAY}"}}]},
        },
        "children": children,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        print(f"[deliver] Notion -> {result.get('url', 'created')}")


def send_email(html_path: Path, report_name: str):
    smtp_host = os.environ["EMAIL_SMTP_HOST"]
    smtp_port = int(os.environ.get("EMAIL_SMTP_PORT", "465"))
    smtp_user = os.environ["EMAIL_SMTP_USER"]
    smtp_pass = os.environ["EMAIL_SMTP_PASS"]
    to_addr = os.environ["EMAIL_TO"]

    html_content = html_path.read_text(encoding="utf-8")

    msg = MIMEMultipart("alternative")
    msg["From"] = smtp_user
    msg["To"] = to_addr
    msg["Subject"] = f"{report_name} -- {TODAY}"
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_addr, msg.as_string())
    print(f"[deliver] Email -> {to_addr}")


CHANNELS = {
    "kindle": send_kindle,
    "slack": send_slack,
    "notion": send_notion,
    "email": send_email,
}


def purge_old_reports():
    cutoff = datetime.date.today() - datetime.timedelta(days=PURGE_DAYS)
    if not REPORTS_DIR.exists():
        return
    for d in sorted(REPORTS_DIR.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        try:
            dir_date = datetime.date.fromisoformat(d.name)
        except ValueError:
            continue
        if dir_date < cutoff:
            import shutil
            shutil.rmtree(d)
            print(f"[purge] Removed {d.name}")


def main():
    config = load_config()
    report_name = config.get("name", "Daily Brief")
    channel = config.get("delivery", {}).get("channel", "kindle")

    purge_old_reports()

    report_html = TODAY_DIR / "report.html"
    if not report_html.exists():
        log(f"{TODAY} -- null")
        return

    item_count = report_html.read_text(encoding="utf-8").count('class="item"')

    sender = CHANNELS.get(channel)
    if not sender:
        print(f"[error] Unknown delivery channel: {channel}")
        print(f"[error] Supported channels: {', '.join(CHANNELS)}")
        return

    sender(report_html, report_name)
    log(f"{TODAY} -- {item_count} items ({channel})")


if __name__ == "__main__":
    main()
