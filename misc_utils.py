def dicts_equal(dict1, dict2):
    """
    Check if all key-value pairs in dict1 are equal to those in dict2.
    """
    return all(dict1[key] == dict2[key] for key in dict1)


def filter_unwanted_products(products_unfiltered, exclude_words):
    """
    Filter out products whose names contain any of the exclude words.
    """
    filtered_products = []
    for product in products_unfiltered:
        if not any(word in product["name"].lower() for word in exclude_words):
            filtered_products.append(product)
    return filtered_products


def filter_wanted_products(products_unfiltered, include_words):
    """
    Filter products to include only those whose names contain any of the include words.
    """
    filtered_products = []
    for product in products_unfiltered:
        if any(word in product["name"].lower() for word in include_words):
            filtered_products.append(product)
    return filtered_products


def generate_url_list(base_url, url_range):
    """
    Generate a list of URLs by appending a range of numbers to the base URL.
    """
    url_list = [base_url]
    for i in range(1, url_range + 1):
        url_list.append(f"{base_url},{i}.html")
    return url_list
