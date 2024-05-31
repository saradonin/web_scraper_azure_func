import logging
import os
import requests
import csv
import smtplib
from dotenv import load_dotenv, find_dotenv
from bs4 import BeautifulSoup
import azure.functions as func
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

app = func.FunctionApp()

load_dotenv(find_dotenv())

URL = os.environ.get("URL")
CSV_FILE = "prev_product_list.csv"
logging.basicConfig(level=logging.INFO)


@app.schedule(
    schedule="0 */30 * * * *",
    arg_name="myTimer",
    run_on_startup=True,
    use_monitor=False,
)
def func_scraper_timer_trigger(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info("The timer is past due!")

    logging.info("Python timer trigger function executed.")

    try:
        main()
    except Exception as e:
        logging.error("An error occurred while running the scraper: %s", e)


def load_prev_list():
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            return [row for row in reader]
    return []


def save_list_to_csv(product_list):
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["name", "price", "link"])
        writer.writeheader()
        writer.writerows(product_list)


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
            <p>Email sent from Web Scraper App by saradonin</p>
        </body>
    </html>
    """
    return html_content


def send_email(list):

    sender_email = os.environ.get("EMAIL_LOGIN")
    sender_password = os.environ.get("EMAIL_PASSWORD")
    receiver_emails = os.environ.get("EMAIL_RECIPENTS").split(",")

    html_content = generate_email_content(list)

    try:
        with smtplib.SMTP_SSL("smtp.googlemail.com", 465) as server:
            server.login(sender_email, sender_password)
            for receiver_email in receiver_emails:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = "New items in stock"
                msg["From"] = formataddr(("Luxury Web Scraper", sender_email))
                msg["To"] = receiver_email

                msg.attach(MIMEText(html_content, "html"))
                server.sendmail(sender_email, receiver_email, msg.as_string())

        logging.info("Email sent successfully.")
    except Exception as error:
        logging.error("Failed to send email: %s", error)


def request_content(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "html.parser")
    return soup


def extract_product_info(content):
    s = content.find("div", class_="listning-boxes container-fluid")
    products = s.find_all("div", class_="product-info row")
    product_list = []

    for item in products:
        name_h2 = item.find("h2", class_="product-name")
        name_a = name_h2.find("a")
        price_1 = item.find("span", class_="price_1")
        price_2 = item.find("span", class_="price_2")

        name_title = name_a.get("title", "N/A").strip() if name_a else "N/A"
        name_href = name_a.get("href", "N/A") if name_a else "N/A"
        price_1_text = price_1.get_text(strip=True) if price_1 else "N/A"
        price_2_text = price_2.get_text(strip=True) if price_2 else "N/A"
        price_text = price_1_text + price_2_text

        product = {"name": name_title, "price": price_text, "link": name_href}
        product_list.append(product)

    return product_list


def scrape_and_compare(prev_list):
    try:
        content = request_content(URL)
        product_list = extract_product_info(content)
        logging.info("Scraped successfully!")

        exclude_words = ["alhambra", "armaf", "paris corner", "zimaya"]
        new_products = [
            item
            for item in product_list
            if item not in prev_list
            and not any(word in item["name"].lower() for word in exclude_words)
        ]

        if new_products:
            send_email(new_products)
            save_list_to_csv(product_list)
        else:
            logging.info("Nothing new.")

    except Exception as error:
        logging.error("An error occurred: %s", error)


def main():
    prev_list = load_prev_list()
    scrape_and_compare(prev_list)
