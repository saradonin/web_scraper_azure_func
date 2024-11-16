import logging
import os
from dotenv import load_dotenv, find_dotenv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr


load_dotenv(find_dotenv())
logging.basicConfig(level=logging.INFO)

# load environment variables
SENDER_EMAIL = os.environ.get("EMAIL_LOGIN")
SENDER_PASSWORD = os.environ.get("EMAIL_PASSWORD")


def generate_email_content(new_items,all_items):
    """
    Generate HTML content for the email.
    """
    list_new_items_html = "".join(
        f'<li>{item["name"]} - {item["price"]} - <a href="{item["link"]}">LINK</a></li>'
        for item in new_items
    )
    list_all_items_html = "".join(
        f'<li>{item["name"]} - {item["price"]} - <a href="{item["link"]}">LINK</a></li>'
        for item in all_items
    )

    html_content = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>New items in stock!</title>
        </head>
        <body>
            <h1>New items available:</h1>
            <ul>
                {list_new_items_html}
            </ul>
            <br>
            <h1>All items available in presale:</h1>
            <ul>
                {list_all_items_html}
            </ul>
            <br>
            <p>Email sent from Azure Web Scraper by saradonin</p>
        </body>
    </html>
    """
    return html_content


def send_email(receiver_emails, new_items, all_items):
    """
    Send an email with the list of items to the specified receivers.
    """
    html_content = generate_email_content(new_items, all_items)

    try:
        with smtplib.SMTP_SSL("smtp.googlemail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            for receiver_email in receiver_emails:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = "New items in stock"
                msg["From"] = formataddr(("Luxury Web Scraper", SENDER_EMAIL))
                msg["To"] = receiver_email

                msg.attach(MIMEText(html_content, "html"))
                server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())

        logging.info("Email sent successfully.")
    except Exception as error:
        logging.error("Failed to send email: %s", error)
