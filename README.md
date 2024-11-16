# Get Recent Changes from MediaWiki

This script retrieves recent changes from a private MediaWiki instance that requires authentication and sends them via email using Mailgun. It is designed to be run periodically, such as on a Heroku Scheduler.

## Features

- Retrieves recent changes within a specific date range (last week by default).
- Authenticates with the MediaWiki API using username and password.
- Formats changes into an organized HTML report.
- Sends the report via email using Mailgun.

## Requirements

- Python 3.7 or later
- A `.env` file containing the required environment variables (see below)
- Access to the MediaWiki API
- A Mailgun account for sending emails

## Setup

1. **Clone the Repository**

   ```bash
   git clone https://github.com/L235/rc-report.git
   cd rc-report
   ```

2. **Install Dependencies**

   Install the required Python libraries using pip:

   ```bash
   pip install -r requirements.txt
   ```

3. **Obtain a BotPassword**

   To use this script, you'll need a BotPassword from your MediaWiki instance. A BotPassword is a secondary password tied to your MediaWiki account, used specifically for automation and scripts. To obtain one, go to Special:BotPasswords on your wiki instance and follow the instructions. This script does not require any additional permissions beyond the basic access.
   
5. **Create a `.env` File**

   Create a `.env` file in the project root directory with the following content:

   ```plaintext
   MW_USERNAME=<your_mediawiki_username>
   MW_PASSWORD=<your_mediawiki_password>
   MW_DOMAIN=<your_mediawiki_domain> # e.g., "arbcom-en.wikipedia.org"
   RECIPIENT_EMAIL=<recipient_email>
   MAILGUN_API_KEY=<your_mailgun_api_key>
   MAILGUN_DOMAIN=<your_mailgun_domain>
   SENDER_EMAIL=<sender_email_address>
   ```

6. **Run the Script**

   Execute the script to generate and send the email report:

   ```bash
   python get_recent_changes.py
   ```

## How It Works

1. **Authentication**  
   The script logs into the MediaWiki API using the provided credentials to retrieve a login token and authenticate.

2. **Retrieve Recent Changes**  
   Changes are fetched from the MediaWiki API within the defined date range (previous Sunday to Saturday).

3. **Format Changes**  
   The retrieved changes are formatted into an HTML report with grouped edits for easier readability.

4. **Send Email**  
   The report is sent to the specified recipient using the Mailgun API.

## Customization

- **Domain Configuration**  
  Specify the MediaWiki domain in the `.env` file using the `MW_DOMAIN` variable.

- **Date Range**  
  The default date range is the previous week. Adjust the logic in the `main` function if a different range is required.

- **Email Formatting**  
  Customize the `format_changes` and `format_group` functions to change how the HTML report appears.

## Environment Variables

The script uses the following environment variables:

| Variable         | Description                                                  |
|------------------|--------------------------------------------------------------|
| `MW_USERNAME`    | MediaWiki username                                           |
| `MW_PASSWORD`    | MediaWiki password  (BotPassword)                            |
| `MW_DOMAIN`      | MediaWiki domain (e.g., `arbcom-en.wikipedia.org`)           |
| `RECIPIENT_EMAIL`| Email address to send the report to                          |
| `MAILGUN_API_KEY`| Mailgun API key for sending emails                           |
| `MAILGUN_DOMAIN` | Mailgun domain for sending emails                            |
| `SENDER_EMAIL`   | The email address used as the sender                         |

## Error Handling

- The script gracefully handles errors like failed authentication or missing environment variables.
- If no changes are found in the specified date range, the script exits without sending an email.
