import logging
import os
from dotenv import load_dotenv, find_dotenv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

load_dotenv(find_dotenv())
logging.basicConfig(level=logging.INFO)

SENDER_EMAIL = os.environ.get("EMAIL_LOGIN")
SENDER_PASWORD = os.environ.get("EMAIL_PASSWORD")


def generate_email_content(items):

    list_items_html = "".join(
        f'<li>{item["name"]} - {item["price"]} - <a href="{item["link"]}">LINK</a></li>'
        for item in items
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
                {list_items_html}
            </ul>
            <br>
            <p>Email sent from Azure Function Web Scraper by saradonin</p>
        </body>
    </html>
    """
    return html_content


def send_email(receiver_emails, list):

    html_content = generate_email_content(list)

    try:
        with smtplib.SMTP_SSL("smtp.googlemail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASWORD)
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
