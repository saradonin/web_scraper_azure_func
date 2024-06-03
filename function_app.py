import logging
import os
import requests
from dotenv import load_dotenv, find_dotenv
from bs4 import BeautifulSoup

import azure.functions as func
from email_utils import send_email
from csv_utils import load_prev_list, save_list_to_csv
from misc_utils import (
    dicts_equal,
    filter_unwanted_products,
    filter_wanted_products,
    generate_url_list,
)


app = func.FunctionApp()
load_dotenv(find_dotenv())
logging.basicConfig(level=logging.INFO)

# load environment variables
URL = os.environ.get("URL")
EMAIL_RECIPENTS_GENERAL = os.environ.get("EMAIL_RECIPENTS_GENERAL").split(",")
EMAIL_RECIPENTS_WISHLIST = os.environ.get("EMAIL_RECIPENTS_WISHLIST").split(",")
EXCLUDE_LIST = os.environ.get("EXCLUDE_LIST").split(",")
INCLUDE_LIST = os.environ.get("INCLUDE_LIST").split(",")


@app.schedule(
    schedule="0 */30 * * * *",
    arg_name="myTimer",
    run_on_startup=True,
    use_monitor=False,
)
def func_scraper_timer_trigger(myTimer: func.TimerRequest) -> None:
    """
    Azure Function that triggers on a schedule to scrape and process data.
    """
    if myTimer.past_due:
        logging.info("The timer is past due!")

    logging.info("Python timer trigger function executed.")

    try:
        main()
    except Exception as e:
        logging.error("An error occurred while running the scraper: %s", e)


def request_content(url):
    """
    Request and parse the content of the given URL using BeautifulSoup.
    """
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "html.parser")
    return soup


def extract_product_info(content):
    """
    Extract product information from the parsed HTML content.
    """
    s = content.find("div", class_="listning-boxes container-fluid")
    products = s.find_all("div", class_="product-info row")
    product_list = []

    for item in products:
        name_h2 = item.find("h2", class_="product-name")
        name_a = name_h2.find("a")
        price_1 = item.find("span", class_="price_1")
        price_2 = item.find("span", class_="price_2")

        name_title = (
            name_a.get("title", "N/A").strip().replace(",", " ") if name_a else "N/A"
        )
        name_href = name_a.get("href", "N/A") if name_a else "N/A"
        price_1_text = price_1.get_text(strip=True) if price_1 else "N/A"
        price_2_text = price_2.get_text(strip=True) if price_2 else "N/A"
        price_text = (price_1_text + price_2_text).replace(",", ".")

        product = {"name": name_title, "price": price_text, "link": name_href}
        product_list.append(product)

    return product_list


def scrape_and_compare(prev_list):
    """
    Scrape the website and compare the results with the previous list.
    """
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

        new_products = filter_unwanted_products(new_products_unfiltered, EXCLUDE_LIST)

        if new_products:
            send_email(EMAIL_RECIPENTS_GENERAL, new_products)
            save_list_to_csv(combined_product_list)

            wishlist_products = filter_wanted_products(new_products, INCLUDE_LIST)

            if wishlist_products:
                send_email(EMAIL_RECIPENTS_WISHLIST, wishlist_products)

            return new_products
        else:
            logging.info("Nothing new.")

    except Exception as error:
        logging.error("An error occurred: %s", error)


def main():
    """
    Main function to load the previous list and initiate scraping and comparison.
    """
    prev_list = load_prev_list()
    scrape_and_compare(prev_list)
