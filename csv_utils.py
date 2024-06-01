import os
import csv
import logging
from dotenv import load_dotenv, find_dotenv
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient


load_dotenv(find_dotenv())
logging.basicConfig(level=logging.INFO)

AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
BLOB_CONTAINER_NAME = os.environ.get("BLOB_CONTAINER_NAME")
CSV_BLOB_NAME = os.environ.get("CSV_BLOB_NAME")
blob_service_client = BlobServiceClient.from_connection_string(
    AZURE_STORAGE_CONNECTION_STRING
)
container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)


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
