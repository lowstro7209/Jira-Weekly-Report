"""
Jira Weekly Filter Report
This version reads credentials from environment variables (GitHub Secrets).
Do NOT put your real passwords or tokens directly in this file.
"""

import requests
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ============================================================
# CONFIG — reads from GitHub Secrets (do not edit this part)
# ============================================================

JIRA_SITE       = os.environ["JIRA_SITE"]
JIRA_EMAIL      = os.environ["JIRA_EMAIL"]
JIRA_API_TOKEN  = os.environ["JIRA_API_TOKEN"]
JIRA_FILTER_ID  = os.environ["JIRA_FILTER_ID"]
SENDER_EMAIL    = os.environ["SENDER_EMAIL"]
SENDER_PASSWORD = os.environ["SENDER_PASSWORD"]
RECIPIENT_EMAILS = os.environ["RECIPIENT_EMAILS"].split(",")  # comma-separated in secret


# ============================================================
# FUNCTIONS
# ============================================================

def fetch_jira_issues():
    """Fetch issues from your Jira saved filter."""
    url = f"{JIRA_SITE}/rest/api/3/filter/{JIRA_FILTER_ID}"
    auth = (JIRA_EMAIL, JIRA_API_TOKEN)

    filter_response = requests.get(url, auth=auth)
    filter_response.raise_for_status()
    jql = filter_response.json().get("jql", "")
    filter_name = filter_response.json().get("name", "Jira Filter")

    search_url = f"{JIRA_SITE}/rest/api/3/search"
    params = {
        "jql": jql,
        "maxResults": 100,
        "fields": "summary,status,assignee,priority,updated,issuetype"
    }
    issues_response = requests.get(search_url, auth=auth, params=params)
    issues_response.raise_for_status()

    data = issues_response.json()
    return data.get("issues", []), filter_name, data.get("total", 0)


def build_html_report(issues, filter_name, total):
    """Build a nicely formatted HTML email."""
    today = datetime.now().strftime("%B %d, %Y")

    rows = ""
    for issue in issues:
        key = issue["key"]
        fields = issue["fields"]
        summary    = fields.get("summary", "N/A")
        status     = fields.get("status", {}).get("name", "N/A")
        assignee   = (fields.get("assignee") or {}).get("displayName", "Unassigned")
        priority   = (fields.get("priority") or {}).get("name", "N/A")
        updated    = fields.get("updated", "")[:10]
        issue_url  = f"{JIRA_SITE}/browse/{key}"

        status_colors = {
            "To Do": "#6b7280", "In Progress": "#2563eb",
            "Done": "#16a34a", "Blocked": "#dc2626", "In Review": "#d97706"
        }
        status_color = status_colors.get(status, "#6b7280")

        rows += f"""
        <tr>
            <td style="padding:10px 12px; border-bottom:1px solid #e5e7eb;">
                <a href="{issue_url}" style="color:#2563eb; font-weight:600; text-decoration:none;">{key}</a>
            </td>
            <td style="padding:10px 12px; border-bottom:1px solid #e5e7eb;">{summary}</td>
            <td style="padding:10px 12px; border-bottom:1px solid #e5e7eb;">
                <span style="background:{status_color}; color:#fff; padding:2px 8px; border-radius:12px; font-size:12px;">{status}</span>
            </td>
            <td style="padding:10px 12px; border-bottom:1px solid #e5e7eb;">{assignee}</td>
            <td style="padding:10px 12px; border-bottom:1px solid #e5e7eb;">{priority}</td>
            <td style="padding:10px 12px; border-bottom:1px solid #e5e7eb;">{updated}</td>
        </tr>
        """

    html = f"""
    <html><body style="font-family: Arial, sans-serif; background:#f9fafb; margin:0; padding:20px;">
    <div style="max-width:900px; margin:auto; background:#fff; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.08); overflow:hidden;">
        <div style="background:#0052cc; padding:24px 32px;">
            <h1 style="color:#fff; margin:0; font-size:22px;">📋 {filter_name}</h1>
            <p style="color:#b3d4ff; margin:6px 0 0;">{today} &nbsp;·&nbsp; {total} issue(s) found</p>
        </div>
        <div style="padding:24px 32px;">
            <table style="width:100%; border-collapse:collapse; font-size:14px;">
                <thead>
                    <tr style="background:#f3f4f6;">
                        <th style="padding:10px 12px; text-align:left; color:#374151;">Key</th>
                        <th style="padding:10px 12px; text-align:left; color:#374151;">Summary</th>
                        <th style="padding:10px 12px; text-align:left; color:#374151;">Status</th>
                        <th style="padding:10px 12px; text-align:left; color:#374151;">Assignee</th>
                        <th style="padding:10px 12px; text-align:left; color:#374151;">Priority</th>
                        <th style="padding:10px 12px; text-align:left; color:#374151;">Updated</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            {"<p style='color:#6b7280; text-align:center; margin-top:20px;'>No issues found in this filter.</p>" if not issues else ""}
        </div>
        <div style="background:#f3f4f6; padding:16px 32px; font-size:12px; color:#9ca3af; text-align:center;">
            Auto-generated by Jira Weekly Report &nbsp;·&nbsp; <a href="{JIRA_SITE}" style="color:#2563eb;">Open Jira</a>
        </div>
    </div>
    </body></html>
    """
    return html


def send_email(html_body):
    """Send the HTML report via Microsoft 365 email."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Weekly Jira Report – {datetime.now().strftime('%b %d, %Y')}"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = ", ".join(RECIPIENT_EMAILS)
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP("smtp.office365.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAILS, msg.as_string())

    print(f"✅ Report sent successfully to: {', '.join(RECIPIENT_EMAILS)}")


def run_report():
    print("⏳ Fetching Jira issues...")
    issues, filter_name, total = fetch_jira_issues()
    print(f"✅ Found {total} issues in filter: {filter_name}")
    html = build_html_report(issues, filter_name, total)
    print("📧 Sending email...")
    send_email(html)


if __name__ == "__main__":
    run_report()
