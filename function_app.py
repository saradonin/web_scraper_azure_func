import logging
import os
import requests
from dotenv import load_dotenv, find_dotenv
from bs4 import BeautifulSoup

import azure.functions as func
from email_utils import send_email
from csv_utils import load_prev_list, save_list_to_csv


app = func.FunctionApp()
load_dotenv(find_dotenv())
logging.basicConfig(level=logging.INFO)

URL = os.environ.get("URL")


@app.schedule(
    schedule="0 */45 * * * *",
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

        name_title = name_a.get("title", "N/A").strip().replace(",", " ") if name_a else "N/A"
        name_href = name_a.get("href", "N/A") if name_a else "N/A"
        price_1_text = price_1.get_text(strip=True) if price_1 else "N/A"
        price_2_text = price_2.get_text(strip=True) if price_2 else "N/A"
        price_text = (price_1_text + price_2_text).replace(",", ".")

        product = {"name": name_title, "price": price_text, "link": name_href}
        product_list.append(product)

    return product_list


def dicts_equal(dict1, dict2):
    return all(dict1[key] == dict2[key] for key in dict1)


def filter_new_products(products_unfiltered, exclude_words):
    filtered_products = []
    for product in products_unfiltered:
        if not any(word in product["name"].lower() for word in exclude_words):
            filtered_products.append(product)
    return filtered_products


def scrape_and_compare(prev_list):
    try:
        url_list = generate_url_list(URL, 8)
        combined_product_list = []

        for url in url_list:
            content = request_content(url)
            product_list = extract_product_info(content)
            combined_product_list.extend(product_list)

        logging.info("Scraped successfully!")

        new_products_unfiltered = [
            item
            for item in combined_product_list
            if not any(dicts_equal(item, prev_item) for prev_item in prev_list)
        ]
        exclude_words = os.environ.get("EXCLUDE_LIST").split(",")
        new_products = filter_new_products(new_products_unfiltered, exclude_words)

        if new_products:
            send_email(new_products)
            save_list_to_csv(combined_product_list)
            return new_products
        else:
            logging.info("Nothing new.")

    except Exception as error:
        logging.error("An error occurred: %s", error)


def main():
    prev_list = load_prev_list()
    scrape_and_compare(prev_list)
