import requests
from lxml import html
import pandas as pd
import numpy as np
import os
import glob

LISTINGS_PER_PAGE = 30

def get_email(listing_url, headers):
    business_page_response = requests.get(listing_url, verify=True, headers=headers)
    if business_page_response.status_code == 200:
        parser = html.fromstring(business_page_response.text)
        base_url = "https://www.yellowpages.com"
        parser.make_links_absolute(base_url)
        email = parser.xpath("//a[@class='email-business']//@href")
        if len(email) > 0:
            return email[0][7:]
    return None


def parse_listing(keyword, city, state, start=1, sortby='distance'):
    url = "https://www.yellowpages.com/search?search_terms={}&geo_location_terms={}%2C+{}&s={}&page={}"
    url = url.format(
        keyword.replace(" ", "+"),
        city.replace(" ", "+"),
        state,
        sortby,
        "{}"
    )
    headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
               'Accept-Encoding': 'gzip, deflate, br',
               'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,ml;q=0.7',
               'Cache-Control': 'max-age=0',
               'Connection': 'keep-alive',
               'Host': 'www.yellowpages.com',
               'Upgrade-Insecure-Requests': '1',
               'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36'}
    print("Starting Category: {}".format(keyword))
    scraped_results = []
    page_num = start

    while True:
        page_results = process_page(url.format(page_num), headers, page_num)
        if page_results:
            scraped_results.extend(page_results)
            page_num += 1
        else:
            return pd.DataFrame(scraped_results)


def process_page(url, headers, page):
    for retry in range(10):
        try:
            response = requests.get(url, verify=True, headers=headers)
            print("parsing page: {}".format(url))
            if response.status_code == 200:
                parser = html.fromstring(response.text)
                base_url = "https://www.yellowpages.com"
                parser.make_links_absolute(base_url)

                if page > np.ceil(int(parser.xpath("//div[@class='pagination']//text()")[1]) / LISTINGS_PER_PAGE):
                    print("Reached final page (final page: {})".format(np.ceil(int(parser.xpath("//div[@class='pagination']//text()")[1]) / LISTINGS_PER_PAGE)))
                    break

                XPATH_LISTINGS = "//div[@class='search-results organic']//div[@class='v-card']"
                listings = parser.xpath(XPATH_LISTINGS)
                scraped_results = []

                for results in listings:
                    XPATH_BUSINESS_NAME = ".//a[@class='business-name']//text()"
                    XPATH_BUSSINESS_PAGE = ".//a[@class='business-name']//@href"
                    XPATH_TELEPHONE = ".//div[@class='info-section info-secondary']//div[@class='phones phone primary']//text()"
                    XPATH_ADDRESS = ".//div[@class='info-section info-secondary']//div[@class='street-address']//text()"
                    XPATH_LOCALITY = ".//div[@class='info-section info-secondary']//div[@class='locality']//text()"
                    XPATH_REGION = ".//div[@class='info']//div//p[@itemprop='address']//span[@itemprop='addressRegion']//text()"
                    XPATH_ZIP_CODE = ".//div[@class='info']//div//p[@itemprop='address']//span[@itemprop='postalCode']//text()"
                    XPATH_RANK = ".//div[@class='info']//h2[@class='n']/text()"
                    XPATH_CATEGORIES = ".//div[@class='info']//div[contains(@class,'info-section')]//div[@class='categories']//text()"
                    XPATH_WEBSITE = ".//div[@class='info']//div[contains(@class,'info-section')]//div[@class='links']//a[contains(@class,'website')]/@href"
                    XPATH_RATING = ".//div[@class='info']//div[contains(@class,'info-section')]//div[contains(@class,'result-rating')]//span//text()"

                    raw_business_name = results.xpath(XPATH_BUSINESS_NAME)
                    raw_business_telephone = results.xpath(XPATH_TELEPHONE)
                    raw_business_page = results.xpath(XPATH_BUSSINESS_PAGE)
                    raw_categories = results.xpath(XPATH_CATEGORIES)
                    raw_website = results.xpath(XPATH_WEBSITE)
                    raw_rating = results.xpath(XPATH_RATING)
                    raw_address = results.xpath(XPATH_ADDRESS)
                    raw_locality = results.xpath(XPATH_LOCALITY)
                    raw_region = results.xpath(XPATH_REGION)
                    raw_zip_code = results.xpath(XPATH_ZIP_CODE)
                    raw_rank = results.xpath(XPATH_RANK)

                    business_name = ''.join(raw_business_name).strip() if raw_business_name else None
                    telephone = ''.join(raw_business_telephone).strip() if raw_business_telephone else None
                    business_page = ''.join(raw_business_page).strip() if raw_business_page else None
                    rank = ''.join(raw_rank).replace('.\xa0','') if raw_rank else None
                    category = ','.join(raw_categories).strip() if raw_categories else None
                    website = ''.join(raw_website).strip() if raw_website else None
                    rating = ''.join(raw_rating).replace("(","").replace(")","").strip() if raw_rating else None
                    street = ''.join(raw_address).strip() if raw_address else None
                    locality = ''.join(raw_locality).replace(',\xa0','').strip() if raw_locality else None
                    region = ''.join(raw_region).strip() if raw_region else None
                    zipcode = ''.join(raw_zip_code).strip() if raw_zip_code else None
                    email = get_email(business_page, headers) if business_page else None

                    business_details = {
                        'business_name': business_name,
                        'telephone': telephone,
                        'email': email,
                        'business_page': business_page,
                        'rank': rank,
                        'category': category,
                        'website': website,
                        'rating': rating,
                        'street': street,
                        'locality': locality,
                        'region': region,
                        'zipcode': zipcode,
                        'listing_url': response.url
                    }
                    scraped_results.append(business_details)

                return scraped_results

            elif response.status_code == 404:
                print("404: Could not find url: {}".format(url))
                break
            else:
                print("{}: Failed to process page {}".format(response.status_code, page))
                return []

        except Exception as e:
            print(e)
            print("Failed to get response on page {}".format(page))
            return []


def parse_categories(category_keywords, city, state, seperate=False, start=1, sortby="distance"):
    results = [parse_listing(kw, city, state, start, sortby) for kw in category_keywords]

    if seperate:
        return results

    df_master = pd.concat(results)

    print(len(df_master))
    df_master.drop_duplicates()
    df_master.drop_duplicates("telephone")
    print(len(df_master))

    df_master = df_master.sort_values("rank")
    df_master = df_master.reset_index(drop=True)
    return df_master
