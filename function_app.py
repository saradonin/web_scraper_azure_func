import logging
import os
import requests
import csv
import smtplib
from dotenv import load_dotenv, find_dotenv
from bs4 import BeautifulSoup
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import azure.functions as func
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

app = func.FunctionApp()

load_dotenv(find_dotenv())

# load .env data
URL = os.environ.get("URL")
AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
BLOB_CONTAINER_NAME = os.environ.get("BLOB_CONTAINER_NAME")
CSV_BLOB_NAME = os.environ.get("CSV_BLOB_NAME")

logging.basicConfig(level=logging.INFO)
blob_service_client = BlobServiceClient.from_connection_string(
    AZURE_STORAGE_CONNECTION_STRING
)
container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)


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
    try:
        blob_client = container_client.get_blob_client(CSV_BLOB_NAME)
        blob_data = blob_client.download_blob().readall()
        csv_data = blob_data.decode("utf-8").splitlines()
        reader = csv.DictReader(csv_data)
        return [row for row in reader]
    except Exception as e:
        logging.error(f"Failed to load previous list: %s", e)
        return []


def save_list_to_csv(product_list):
    try:
        blob_client = container_client.get_blob_client(CSV_BLOB_NAME)
        csv_data = "name,price,link\n"
        for product in product_list:
            csv_data += f"{product['name']},{product['price']},{product['link']}\n"
        blob_client.upload_blob(csv_data, overwrite=True)
    except Exception as e:
        logging.error(f"Failed to save list to CSV: %s", e)


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


def generate_url_list(base_url, url_range):
    url_list = [base_url]
    for i in range(1, url_range + 1):
        url_list.append(f"{base_url},{i}.html")
    return url_list


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
        url_list = generate_url_list(URL, 8)
        combined_product_list = []

        for url in url_list:
            content = request_content(url)
            product_list = extract_product_info(content)
            combined_product_list.extend(product_list)

        logging.info("Scraped successfully!")

        exclude_words = ["alhambra", "armaf", "lattafa", "paris corner", "zimaya"]
        new_products = [
            item
            for item in combined_product_list
            if item not in prev_list
            and not any(word in item["name"].lower() for word in exclude_words)
        ]

        if new_products:
            send_email(new_products)
            save_list_to_csv(combined_product_list)
        else:
            logging.info("Nothing new.")

    except Exception as error:
        logging.error("An error occurred: %s", error)


def main():
    prev_list = load_prev_list()
    scrape_and_compare(prev_list)
