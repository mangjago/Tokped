import requests
import re
import json
import argparse
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

def check_fake_user(user, review):
    fake_user = False
    if len(user["fullName"]) <= 1:
        fake_user = True
    if len(review["message"]) <= 10:
        fake_user = True
    if review["isAnonymous"]:
        fake_user = True

    return fake_user

def get_original_url(link_product):
    headers = {"User-Agent": UserAgent().random}
    response = requests.get(link_product, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    meta_tag = soup.find("meta", attrs={"property": "og:url"})
    
    if not meta_tag:
        raise ValueError("Original URL not found in the meta tag.")

    ori_url = meta_tag.get("content")
    product_id_pattern = r'utm_campaign=PDP-[^/]*-(\d+)-[^/]*'
    match = re.search(product_id_pattern, response.url)
    
    if not match:
        raise ValueError("Product ID not found in the URL.")
    
    product_id = match.group(1)
    return response.text, ori_url, product_id

def get_product_info(link_product):
    try:
        response_text, url, product_id = get_original_url(link_product)
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    json_pattern = r'window\.__cache=(\{"ROOT_QUERY.*?\});'
    match = re.search(json_pattern, response_text)

    if not match:
        print("JSON data not found on the page.")
        return

    json_text = match.group(1)
    json_data = json.loads(json_text)
    
    basic_info = json_data.get(f"pdpBasicInfo{product_id}")
    tx_stats = json_data.get(f"$pdpBasicInfo{product_id}.txStats")
    stats = json_data.get(f"$pdpBasicInfo{product_id}.stats")

    product_info = {
        "Product Name": basic_info["alias"].replace("-", " "),
        "Created At": basic_info["createdAt"],
        "Product ID": basic_info["productID"],
        "Shop ID": basic_info["shopID"],
        "Shop Name": basic_info["shopName"],
        "Status": basic_info["status"],
        "Transaction Success": tx_stats["transactionSuccess"],
        "Transaction Reject": tx_stats["transactionReject"],
        "Count Sold": tx_stats["countSold"],
        "Payment Verified": tx_stats["paymentVerified"],
        "Count View": stats["countView"],
        "Count Review": stats["countReview"],
        "Rating": stats["rating"],
    }

    for key, value in product_info.items():
        print(f"{key}: {value}")

    return product_id  # Return product_id for use in get_reviews

def get_reviews(link_product):
    try:
        response_text, _, product_id = get_original_url(link_product)
        response_text = check_response(link_product)
    except ValueError as e:
        print(f"Error: {e}")
        return

    json_pattern = r'window\.__cache=(\{"ROOT_QUERY.*?\});'
    match = re.search(json_pattern, response_text)

    if not match:
        print("JSON data not found on the review page.")
        return

    json_text = match.group(1)
    json_data = json.loads(json_text)
    rating_score = json_data.get(f'$ROOT_QUERY.productrevGetProductRatingAndTopics({{"productID":"{product_id}"}}).rating')
    
    user_reviews = json_data.get(f'$ROOT_QUERY.productrevGetProductReviewList({{"filterBy":"","limit":10,"page":1,"productID":"{product_id}","sortBy":"informative_score desc"}})')

    fake_users = []
    real_users = []

    for review in user_reviews['list']:
        user_detail = json_data.get(f"${review.get('id')}.user")
        review_detail = json_data.get(review.get('id'))

        if check_fake_user(user_detail, review_detail):
            fake_users.append(user_detail["fullName"])
        else:
            real_users.append(user_detail["fullName"])

    print(f"\nTotal fake reviews: {len(fake_users)}")
    print(f"Fake users: {', '.join(fake_users)}")
    print(f"Total real reviews: {len(real_users)}")
    print(f"Real users: {', '.join(real_users)}")

def check_response(link_product):
    headers = {"User-Agent": UserAgent().random}
    _, url, _ = get_original_url(link_product)
    response = requests.get(f"{url}/review?", headers=headers)
    return response.text

def main():
    parser = argparse.ArgumentParser(description='Check fake reviews on a Tokopedia product.')
    parser.add_argument('link_product', type=str, help='The link to the product')
    args = parser.parse_args()

    try:
        product_id = get_product_info(args.link_product)
        if product_id:
            get_reviews(args.link_product)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()