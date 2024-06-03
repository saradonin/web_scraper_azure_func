# Azure Web Scraper

This project is an Azure Function App designed to scrape product information from a given list of URLs and send an email notification when new products are found. The scraper periodically runs, checks for new products, and updates a CSV file stored in Azure Blob Storage.

## Features

- Scrapes product information from multiple URLs.
- Compares the scraped data with previously stored data.
- Sends email notifications for new products.
- Stores and retrieves data from Azure Blob Storage.

## Prerequisites

- Azure Subscription
- Python 3.7 or higher
- Azure Functions Core Tools
- Azure CLI
- A Storage Account in Azure


