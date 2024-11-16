#!/usr/bin/python3

"""
get_recent_changes.py

Get recent changes within the last week from a private MediaWiki wiki that requires authentication,
and send them via email using Mailgun. Designed to be run periodically, e.g., on Heroku Scheduler.
"""

import os
import sys
import requests
import datetime
import logging
from requests.exceptions import RequestException
from dotenv import load_dotenv
import html  # Importing here to escape comments


# Load environment variables from a .env file if present
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_login_token(session, url):
    """Retrieve a login token."""
    params = {
        "action": "query",
        "meta": "tokens",
        "type": "login",
        "format": "json"
    }
    try:
        response = session.get(url=url, params=params)
        data = response.json()
        return data['query']['tokens']['logintoken']
    except (RequestException, KeyError) as e:
        logger.error("Failed to retrieve login token: %s", e)
        sys.exit(1)

def login(session, url, login_token, username, password):
    """Log in to the wiki."""
    params = {
        "action": "login",
        "lgname": username,
        "lgpassword": password,
        "format": "json",
        "lgtoken": login_token
    }
    try:
        response = session.post(url, data=params)
        data = response.json()
        if data['login']['result'] != "Success":
            reason = data['login'].get('reason', 'No reason provided')
            logger.error("Login failed: %s", reason)
            sys.exit(1)
        else:
            logger.info("Logged in as %s", username)
    except (RequestException, KeyError) as e:
        logger.error("Login failed: %s", e)
        sys.exit(1)

def get_recent_changes(session, url, start_date, end_date):
    """Retrieve recent changes within the specified date range."""
    # Use timezone-aware datetime objects
    rcstart = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    rcend = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')

    changes = []

    params = {
        "action": "query",
        "list": "recentchanges",
        "rcprop": "title|timestamp|user|comment|ids",
        "rclimit": "max",
        "rcstart": rcstart,
        "rcend": rcend,
        "rcdir": "older",
        "format": "json"
    }

    while True:
        try:
            response = session.get(url=url, params=params)
            data = response.json()
            changes.extend(data['query']['recentchanges'])

            if 'continue' in data:
                params.update(data['continue'])
            else:
                break
        except (RequestException, KeyError) as e:
            logger.error("Failed to retrieve recent changes: %s", e)
            sys.exit(1)

    return changes

def format_changes(changes, base_url, start_date, end_date, title):
    """Format the recent changes for HTML output, grouping consecutive edits."""
    output_lines = []

    # Add header text with date range
    start_str = start_date.strftime('%b %d')
    end_str = end_date.strftime('%b %d')
    header = f"<h1>Weekly {title} report: {start_str} - {end_str}</h1>"
    output_lines.append(header)
    output_lines.append(f"<p>Here are the recent changes on {title} for the past week:</p>")

    # Sort changes by timestamp descending (more recent up top)
    changes.sort(key=lambda x: x['timestamp'], reverse=True)

    current_date = None
    last_user = None
    last_page = None
    group = []


    for idx, rc in enumerate(changes):
        # Parse timestamp into timezone-aware datetime
        timestamp = rc['timestamp']
        ts = datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)
        date_str = ts.strftime('%Y-%m-%d')
        day_of_week = ts.strftime('%A')

        # Start a new date section if the date has changed
        if current_date != date_str:
            current_date = date_str
            # Flush any remaining group
            if group:
                output_lines.extend(format_group(group, base_url))
                group = []
            heading = f"<h2>{current_date} ({day_of_week})</h2>"
            output_lines.append(heading)
            last_user = None
            last_page = None

        # Check if this edit should be grouped with the previous one
        user = rc['user']
        page_title = rc['title']

        if (user == last_user and page_title == last_page):
            # Add to current group
            group.append(rc)
        else:
            # Flush the previous group if it exists
            if group:
                output_lines.extend(format_group(group, base_url))
                group = []
            # Start a new group
            group.append(rc)
            last_user = user
            last_page = page_title

    # Flush any remaining group
    if group:
        output_lines.extend(format_group(group, base_url))

    # Combine all lines into a single HTML string
    html_output = "\n".join(output_lines)
    return html_output

def format_group(group, base_url):
    """Format a group of consecutive edits for output."""
    output = []
    first_edit = group[0]
    last_edit = group[-1]

    # Time range
    first_ts = datetime.datetime.strptime(first_edit['timestamp'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)
    last_ts = datetime.datetime.strptime(last_edit['timestamp'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)
    time_range = f"[{last_ts.strftime('%H:%M')} - {first_ts.strftime('%H:%M')}]"

    # User and page
    page_title = first_edit['title']
    username = first_edit['user']

    # Prepare links
    from urllib.parse import quote
    page_title_encoded = quote(page_title.replace(' ', '_'))
    page_url = f"{base_url}/wiki/{page_title_encoded}"
    user_url = f"{base_url}/wiki/User:{quote(username)}"

    # Header for the group
    group_header = (
        f"<p><strong>{time_range} "
        f"<a href='{page_url}'><strong>{html.escape(page_title)}</strong></a> "
        f"[<a href='{user_url}'>{html.escape(username)}</a>]</strong></p>"
    )
    output.append(group_header)

    # List of edits
    output.append("<ul>")
    for rc in group:
        ts = datetime.datetime.strptime(rc['timestamp'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)
        time_str = ts.strftime('%H:%M')
        comment = html.escape(rc.get('comment', ''))
        diff_link = f"{base_url}/w/index.php?diff={rc['revid']}&oldid={rc.get('old_revid', 0)}"

        edit_entry = (
            f"<li>"
            f"[<a href='{diff_link}'>diff</a>] "
            f"[{time_str}] "
            f"('{comment}') "
            f"</li>"
        )
        output.append(edit_entry)
    output.append("</ul>")

    return output

def send_email(subject, html_content, recipient_email):
    """Send the email using Mailgun."""
    MAILGUN_API_KEY = os.getenv('MAILGUN_API_KEY')
    MAILGUN_DOMAIN = os.getenv('MAILGUN_DOMAIN')
    SENDER_EMAIL = os.getenv('SENDER_EMAIL')

    if not MAILGUN_API_KEY or not MAILGUN_DOMAIN or not SENDER_EMAIL:
        logger.error("Mailgun configuration is missing.")
        sys.exit(1)

    return requests.post(
        f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
        auth=("api", MAILGUN_API_KEY),
        data={
            "from": SENDER_EMAIL,
            "to": recipient_email,
            "subject": subject,
            "html": html_content
        }
    )

def main():
    # Load credentials from environment variables
    username = os.getenv('MW_USERNAME')
    password = os.getenv('MW_PASSWORD')
    recipient_email = os.getenv('RECIPIENT_EMAIL')

    if not username or not password:
        logger.error("Username or password not set in environment variables.")
        sys.exit(1)

    if not recipient_email:
        logger.error("Recipient email not set in environment variables.")
        sys.exit(1)

    S = requests.Session()
    BASE_DOMAIN = os.getenv('BASE_DOMAIN')
    URL = f"https://{BASE_DOMAIN}/w/api.php"
    BASE_URL = f"https://{BASE_DOMAIN}"

    # Step 1: Retrieve a login token
    login_token = get_login_token(S, URL)

    # Step 2: Log in
    login(S, URL, login_token, username, password)

    # Step 3: Define date range for the past week (previous Sunday to Saturday)
    today = datetime.datetime.now(datetime.timezone.utc).date()
    last_saturday = today - datetime.timedelta(days=today.weekday() + 2)
    last_sunday = last_saturday - datetime.timedelta(days=6)
    start_date = datetime.datetime.combine(last_sunday, datetime.time.min, tzinfo=datetime.timezone.utc)
    end_date = datetime.datetime.combine(last_saturday, datetime.time.max, tzinfo=datetime.timezone.utc)

    # Step 4: Get recent changes
    changes = get_recent_changes(S, URL, end_date, start_date)

    if not changes:
        logger.info("No recent changes found in the last week.")
        sys.exit(0)

    # Step 5: Format the output
    title = BASE_DOMAIN.split('.')[0]
    html_output = format_changes(changes, BASE_URL, end_date, start_date, title)

    # Step 6: Send the email using Mailgun
    subject = f"Weekly {BASE_DOMAIN} report: {start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}"
    response = send_email(subject, html_output, recipient_email)

    if response.status_code == 200:
        logger.info("Email sent successfully.")
    else:
        logger.error(f"Failed to send email: {response.text}")
        sys.exit(1)

if __name__ == "__main__":
    main()
