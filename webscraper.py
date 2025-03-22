from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
import os
from datetime import datetime
import re
# from groq import Groq
from dotenv import load_dotenv
import csv

class AirbnbScraper:
    def __init__(self, update_status=None):
        self.update_status = update_status or print  # Use provided update function or fallback to print
        self.setup_driver()
        self.results = []
        # self.setup_groq()
        
        # Create run-specific directory
        self.run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = os.path.join("runs", self.run_timestamp)
        if not os.path.exists(self.run_dir):
            os.makedirs(self.run_dir)
        
        # Initialize output files
        self.json_file = os.path.join(self.run_dir, "listings.json")
        self.csv_file = os.path.join(self.run_dir, "listings.csv")
        
        # Create empty JSON file
        with open(self.json_file, 'w') as f:
            json.dump([], f)
        
        # Create CSV with headers
        headers = [
            "Link", "Name", "Bedrooms", "Beds", "Bathrooms", "Guest Limit", 
            "Stars", "Price/Night in May", "AirBnB Location Rating", "Source", 
            "Amenities", "TV", "Pool", "Jacuzzi", "Historical House", 
            "Billiards Table", "Large Yard", "Balcony", "Laundry", "Home Gym",
            "Guest Favorite Status"
        ]
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        
    def setup_driver(self):
        """Set up the Chrome driver with appropriate options"""
        chrome_options = Options()
        # chrome_options.add_argument("--headless")  # Run in headless mode
        # chrome_options.add_argument("--headless=new")  # Run in headless mode
        # chrome_options.add_argument("--no-sandbox")
        # chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        # chrome_options.add_argument("--start-maximized")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        # self.driver = webdriver.Chrome(options=chrome_options)
        
    # def setup_groq(self):
    #     """Set up the Groq client"""
    #     load_dotenv()
    #     self.groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        
    def handle_popups(self):
        """Handle any popups that might appear"""
        try:
            # Reduced wait time for popup
            got_it_button = WebDriverWait(self.driver, 2).until(  # Reduced from 5 to 2
                EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Got it')]"))
            )
            got_it_button.click()
            # time.sleep(0.5)  # Reduced from 1 to 0.5
        except (TimeoutException, ElementClickInterceptedException, NoSuchElementException):
            pass

    def scroll_to_element(self, element):
        """Scroll to a specific element using JavaScript with better reliability"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            # time.sleep(1)  # Reduced from 2 to 1
            
            self.driver.execute_script("window.scrollBy(0, -100);")
            # time.sleep(0.5)  # Reduced from 1 to 0.5
            
            return element.is_displayed()
        except:
            return False

    # def check_amenities_with_groq(self, amenities_text):
        # """Use Groq to analyze amenities text"""
        # target_amenities = ["TV", "Pool", "Jacuzzi", "Billiards/Pool Table", 
        #                   "Large Yard", "Balcony", "Laundry", "Home Gym"]
        
        # prompt = f"""
        # Given the following amenities text from an Airbnb listing:
        # {amenities_text}
        
        # Please analyze if the following amenities are present (exactly or similar terms):
        # {', '.join(target_amenities)}
        
        # Return ONLY a JSON object in this exact format, with no additional text:
        # {{
        #     "TV": true/false,
        #     "Pool": true/false,
        #     "Jacuzzi": true/false,
        #     "Billiards/Pool Table": true/false,
        #     "Large Yard": true/false,
        #     "Balcony": true/false,
        #     "Laundry": true/false,
        #     "Home Gym": true/false
        # }}
        
        # Consider similar terms (e.g., "Swimming pool" for "Pool", "Hot tub" for "Jacuzzi", etc.)
        # """
        
        # try:
        #     chat_completion = self.groq_client.chat.completions.create(
        #         messages=[
        #             {
        #                 "role": "system",
        #                 "content": "You are a JSON-only assistant. You must respond with valid JSON objects only, no additional text or explanation."
        #             },
        #             {
        #                 "role": "user",
        #                 "content": prompt
        #             }
        #         ],
        #         model="llama-3.3-70b-versatile",
        #     )
            
        #     response = chat_completion.choices[0].message.content.strip()
        #     self.update_status(f"\nGroq response: {response}")  # Debug print
            
        #     # Try to clean the response if it's not pure JSON
        #     try:
        #         return json.loads(response)
        #     except:
        #         # Try to extract JSON if there's additional text
        #         import re
        #         json_match = re.search(r'\{.*\}', response, re.DOTALL)
        #         if json_match:
        #             return json.loads(json_match.group())
        #         raise Exception("Could not extract valid JSON from response")
            
        # except Exception as e:
        #     self.update_status(f"Error analyzing amenities with Groq: {str(e)}")
        #     # Return a default structure instead of None
        #     return {
        #         "TV": False,
        #         "Pool": False,
        #         "Jacuzzi": False,
        #         "Billiards/Pool Table": False,
        #         "Large Yard": False,
        #         "Balcony": False,
        #         "Laundry": False,
        #         "Home Gym": False,
        #         "error": str(e)
        #     }

    def get_amenities_text(self):
        """Get amenities text from modal or fall back to page text"""
        try:
            self.update_status("\nTrying to access amenities...")
            
            # First make sure we're on the right part of the page
            self.driver.execute_script("window.scrollBy(0, 500);")
            
            # Try multiple selectors for the button
            selectors = [
                '//*[@id="site-content"]/div/div[1]/div[3]/div/div[1]/div/div[7]/div/div[2]/section/div[3]/button',
                "//button[contains(., 'Show all amenities')]",
                "//button[contains(@aria-label, 'amenities')]",
                "//div[contains(@data-section-id, 'AMENITIES')]//button",
                "//button[.//span[contains(text(), 'Show all')]]"
            ]
            
            show_all_button = None
            for selector in selectors:
                try:
                    show_all_button = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    if show_all_button:
                        self.update_status(f"Found button using selector: {selector}")
                        break
                except:
                    continue
            
            if not show_all_button:
                raise Exception("Could not find 'Show all amenities' button with any selector")
            
            self.update_status("Found button, scrolling to it...")
            self.scroll_to_element(show_all_button)
            
            self.update_status("Attempting to click button...")
            try:
                show_all_button.click()
            except:
                self.driver.execute_script("arguments[0].click();", show_all_button)
            
            self.update_status("Button clicked, waiting for modal...")
            
            # Try multiple selectors for the modal content
            modal_selectors = [
                '/html/body/div[9]/div/div/section/div/div/div[2]/div/div[3]/div/div/div/section/section',  # Original XPath
                "div[role='dialog'] section",  # CSS selector
                "//div[@role='dialog']//div[@role='group']",  # Role-based XPath
                "//div[contains(@aria-label, 'amenities')]"  # Aria label
            ]
            
            modal = None
            for selector in modal_selectors:
                try:
                    if selector.startswith("//"):
                        modal = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                    else:
                        modal = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                    if modal:
                        self.update_status(f"Found modal using selector: {selector}")
                        break
                except:
                    continue
            
            if not modal:
                self.update_status("Could not access modal, falling back to page text...")
                # Get amenities section from the main page
                amenities_section = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        '//*[@id="site-content"]/div/div[1]/div[3]/div/div[1]/div/div[7]/div/div[2]/section'
                    ))
                )
                amenities_text = amenities_section.text
                if amenities_text:
                    self.update_status("Successfully retrieved amenities from page")
                    return amenities_text
            
            # If modal was found, use its text
            amenities_text = modal.text
            if amenities_text:
                self.update_status(f"\nFound amenities text from modal")
                # print(f"\nFound amenities text from modal: {amenities_text[:100]}...")
                return amenities_text
            
            self.update_status("Warning: No amenities text found in either modal or page")
            return None
            
        except Exception as e:
            self.update_status(f"Error getting amenities from modal, falling back to page text...")
            try:
                # Final fallback: try to get the entire page content
                full_content = self.driver.find_element(
                    By.XPATH,
                    '//*[@id="site-content"]/div/div[1]'
                ).text
                self.update_status("Using full page content for amenities analysis")
                return full_content
            except:
                self.update_status("Could not get any amenities text")
                return None

    def check_historical_house(self, page_text):
        """Check if the listing is a historical house using simple text matching"""
        try:
            # Get description directly from the element with updated XPath
            description_element = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    '//*[@id="site-content"]/div/div[1]/div[3]/div/div[1]/div/div[5]/div/div[2]/div[1]'  # Updated XPath
                ))
            )
            description_text = description_element.text
            if description_text:
                page_text = f"{page_text}\n{description_text}"
                self.update_status("Added description text to analysis")

        except Exception as e:
            self.update_status(f"Warning: Could not access description: {str(e)}")
            # Continue with existing page_text if we can't get the description
            pass

        historical_terms = [
            'historic', 'historical', 'history'
        ]
        
        # Convert to lowercase for case-insensitive matching
        page_text_lower = page_text.lower()
        
        # Find all matches with some context
        evidence = []
        for term in historical_terms:
            # Find the term in the text
            index = page_text_lower.find(term)
            if index != -1:
                # Get some context around the match (100 chars before and after)
                start = max(0, index - 100)
                end = min(len(page_text), index + len(term) + 100)
                context = page_text[start:end].strip()
                evidence.append(context)
        
        return {
            "is_historical": len(evidence) > 0,
            "evidence": "; ".join(evidence) if evidence else "No historical evidence found"
        }

    # def extract_missing_details(self, full_content, missing_fields):
    #     """Use Groq to extract missing details from the full page content"""
    #     prompt = f"""
    #     Given the following Airbnb listing content:
    #     {full_content}
        
    #     Extract these missing fields: {', '.join(missing_fields)}
    #     Return ONLY a JSON object with the found values, like:
    #     {{
    #         "field_name": "extracted value"
    #     }}
    #     """
        
    #     try:
    #         chat_completion = self.groq_client.chat.completions.create(
    #             messages=[
    #                 {
    #                     "role": "system",
    #                     "content": "You are a JSON-only assistant. Respond with valid JSON only."
    #                 },
    #                 {
    #                     "role": "user",
    #                     "content": prompt
    #                 }
    #             ],
    #             model="llama-3.3-70b-versatile",
    #         )
            
    #         response = chat_completion.choices[0].message.content.strip()
    #         self.update_status(f"\nGroq missing details response: {response}")  # Debug print
            
    #         # Try to clean the response if it's not pure JSON
    #         try:
    #             return json.loads(response)
    #         except:
    #             # Try to extract JSON if there's additional text
    #             import re
    #             json_match = re.search(r'\{.*\}', response, re.DOTALL)
    #             if json_match:
    #                 return json.loads(json_match.group())
    #             raise Exception("Could not extract valid JSON from response")
            
    #     except Exception as e:
    #         self.update_status(f"Error extracting missing details: {str(e)}")
    #         return {}

    def get_next_page_link(self):
        """Find and return the next page link if available"""
        try:
            # Try to find the Next button specifically
            next_button_xpath = '//*[@id="site-content"]/div/div[3]/div/div/div/nav/div/a[last()]'  # Last <a> tag in nav
            
            try:
                next_button = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, next_button_xpath))
                )
                
                self.update_status(f"\nFound next button: {next_button.get_attribute('aria-label')}")
                
                # Check if the button is disabled
                aria_disabled = next_button.get_attribute('aria-disabled')
                if aria_disabled == 'true':
                    self.update_status("Next button is disabled, no more pages")
                    return None
                    
                # Make sure it's actually the "Next" button
                if 'Next' in next_button.get_attribute('aria-label'):
                    self.update_status("Found active Next button")
                    return next_button
                
                self.update_status("Button found but it's not a Next button")
                return None
                
            except Exception as e:
                self.update_status(f"Could not find Next button: {str(e)}")
                return None
                
        except Exception as e:
            self.update_status(f"Error in get_next_page_link: {str(e)}")
            return None

    def update_output_files(self, listing_details):
        """Update both JSON and CSV files with new listing data"""
        try:
            # Prepare the reformatted data
            reformatted_data = {
                "Link": listing_details.get("url", ""),
                "Name": listing_details.get("name", ""),
                "Bedrooms": listing_details.get("bedrooms", ""),
                "Beds": listing_details.get("beds", ""),
                "Bathrooms": listing_details.get("bathrooms", ""),
                "Guest Limit": listing_details.get("guest_limit", ""),
                "Stars": listing_details.get("stars", ""),
                "Price/Night in May": listing_details.get("price_per_night", ""),
                "AirBnB Location Rating": listing_details.get("location_rating", ""),
                "Source": "Airbnb",
                "Amenities": "",  # Blank as requested
                "TV": "TRUE" if listing_details.get("amenities_analysis", {}).get("TV", False) else "FALSE",
                "Pool": "TRUE" if listing_details.get("amenities_analysis", {}).get("Pool", False) else "FALSE",
                "Jacuzzi": "TRUE" if listing_details.get("amenities_analysis", {}).get("Jacuzzi", False) else "FALSE",
                "Historical House": "TRUE" if listing_details.get("is_historical", False) else "FALSE",
                "Billiards Table": "TRUE" if listing_details.get("amenities_analysis", {}).get("Billiards/Pool Table", False) else "FALSE",
                "Large Yard": "TRUE" if listing_details.get("amenities_analysis", {}).get("Large Yard", False) else "FALSE",
                "Balcony": "TRUE" if listing_details.get("amenities_analysis", {}).get("Balcony", False) else "FALSE",
                "Laundry": "TRUE" if listing_details.get("amenities_analysis", {}).get("Laundry", False) else "FALSE",
                "Home Gym": "TRUE" if listing_details.get("amenities_analysis", {}).get("Home Gym", False) else "FALSE",
                "Guest Favorite Status": "TRUE" if listing_details.get("is_guest_favorite", False) else "FALSE"
            }
            
            # Update JSON file
            with open(self.json_file, 'r') as f:
                current_data = json.load(f)
            
            current_data.append(reformatted_data)
            
            with open(self.json_file, 'w') as f:
                json.dump(current_data, f, indent=2)
            
            # Update CSV file
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    reformatted_data["Link"],
                    reformatted_data["Name"],
                    reformatted_data["Bedrooms"],
                    reformatted_data["Beds"],
                    reformatted_data["Bathrooms"],
                    reformatted_data["Guest Limit"],
                    reformatted_data["Stars"],
                    reformatted_data["Price/Night in May"],
                    reformatted_data["AirBnB Location Rating"],
                    reformatted_data["Source"],
                    reformatted_data["Amenities"],
                    reformatted_data["TV"],
                    reformatted_data["Pool"],
                    reformatted_data["Jacuzzi"],
                    reformatted_data["Historical House"],
                    reformatted_data["Billiards Table"],
                    reformatted_data["Large Yard"],
                    reformatted_data["Balcony"],
                    reformatted_data["Laundry"],
                    reformatted_data["Home Gym"],
                    reformatted_data["Guest Favorite Status"]
                ])
            
            self.update_status(f"\nUpdated output files in {self.run_dir}")
            
        except Exception as e:
            self.update_status(f"Error updating output files: {str(e)}")

    def scrape_url(self, url, num_pages=5):
        """
        Scrape Airbnb listings from a direct URL with pagination
        Args:
            url (str): Complete Airbnb search URL
            num_pages (int): Number of pages to scrape
        """
        try:
            current_page = 1
            all_listings = []
            
            # Add page parameter to URL if not present
            if 'page=' not in url:
                url = f"{url}&page=1" if '?' in url else f"{url}?page=1"
            
            while current_page <= num_pages:
                self.update_status(f"\n{'='*50}")
                self.update_status(f"Processing page {current_page} of {num_pages}")
                self.update_status(f"{'='*50}")
                
                # Load the page
                self.update_status(f"\nLoading URL: {url}")
                self.driver.get(url)
                # time.sleep(1.5)
                
                # Handle popups
                self.handle_popups()
                
                try:
                    # Get number of nights from the date range in header
                    date_range_xpath = '/html/body/div[5]/div/div/div[1]/div/div[3]/header/div[1]/div/div/div/div/div[2]/div[1]/div/span[2]/button[2]/div'
                    try:
                        date_element = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, date_range_xpath))
                        )
                        date_text = date_element.text.strip()
                        self.update_status(f"Found date range: {date_text}")
                        
                        # Extract dates and calculate nights
                        # Format example: "Apr 18 – 20"
                        dates = re.findall(r'\d+', date_text)
                        if len(dates) >= 2:
                            num_nights = str(int(dates[1]) - int(dates[0]))
                            self.update_status(f"Calculated {num_nights} nights from date range")
                        else:
                            num_nights = "2"  # Default if we can't parse the dates
                            self.update_status("Could not parse dates, using default 2 nights")
                    except Exception as e:
                        self.update_status(f"Error getting date range: {str(e)}, using default 2 nights")
                        num_nights = "2"

                    # Process grid items (existing code)
                    self.update_status("Waiting for listings grid to load...")
                    grid_items = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_all_elements_located((
                            By.XPATH, 
                            '//*[@id="site-content"]/div/div[2]/div/div/div/div/div/div'
                        ))
                    )
                    self.update_status(f"Found {len(grid_items)} listings to process")
                    
                    original_window = self.driver.current_window_handle
                    
                    # Iterate through each grid item
                    for index, item in enumerate(grid_items, 1):
                        try:
                            self.update_status(f"\n{'='*50}")
                            self.update_status(f"Processing listing {index} of {len(grid_items)}")
                            self.update_status(f"{'='*50}")
                            
                            # Get rating and price info from grid item first
                            try:
                                # Get rating and reviews
                                rating_element = WebDriverWait(item, 3).until(
                                    EC.presence_of_element_located((
                                        By.XPATH, 
                                        '//*[@id="site-content"]/div/div[2]/div/div/div/div/div/div[1]/div/div[2]/div/div/div/div/div/div[2]/div[5]/span/span[3]'
                                    ))
                                )
                                rating_text = rating_element.get_attribute("innerText")
                                rating_match = re.match(r"([\d.]+)\s*\((\d+)\)", rating_text)
                                if rating_match:
                                    rating = rating_match.group(1)
                                    review_count = rating_match.group(2)
                                    self.update_status(f"Found rating: {rating} with {review_count} reviews")
                                else:
                                    rating = "N/A"
                                    review_count = "0"
                                    self.update_status("Could not parse rating text")

                                # Multiple possible XPaths for price element
                                price_xpaths = [
                                    '//*[@id="site-content"]/div/div[2]/div/div/div/div/div/div[1]/div/div[2]/div/div/div/div/div/div[2]/div[4]/div[2]/div/div/span/div[1]/div/span/div/button/span[1]',
                                    '//*/html/body/div[5]/div/div/div[1]/div/div[3]/div[1]/main/div[2]/div/div[2]/div/div/div/div/div/div[5]/div/div[2]/div/div/div/div/div/div[2]/div[4]/div[2]/div/div/span/div/span/div/button/span[1]',
                                    "//span[@class='_hb913q']"  # CSS class-based selector as fallback
                                ]
                                
                                # Try each price XPath until we find one that works
                                price_element = None
                                for xpath in price_xpaths:
                                    try:
                                        price_element = WebDriverWait(item, 3).until(
                                            EC.presence_of_element_located((By.XPATH, xpath))
                                        )
                                        if price_element:
                                            break
                                    except:
                                        continue

                                if not price_element:
                                    raise Exception("Could not find price element with any XPath")

                                price_text = price_element.text.strip()
                                total_price = ''.join(filter(str.isdigit, price_text))
                                self.update_status(f"Found price: ${total_price}")

                                # Calculate price per night using the number of nights from header
                                try:
                                    price_per_night = str(int(total_price) // int(num_nights))
                                    self.update_status(f"Calculated ${price_per_night} per night for {num_nights} nights")
                                except:
                                    price_per_night = total_price
                                    self.update_status("Could not calculate price per night, using total price")

                            except Exception as e:
                                self.update_status(f"Warning: Could not extract price information: {str(e)}")
                                total_price = "N/A"
                                num_nights = "N/A"
                                price_per_night = "N/A"

                            self.update_status("\nClicking listing and waiting for new tab...")
                            item.click()
                            
                            # Switch to new tab with shorter timeout
                            WebDriverWait(self.driver, 5).until(lambda d: len(d.window_handles) > 1)
                            new_window = [window for window in self.driver.window_handles if window != original_window][0]
                            self.driver.switch_to.window(new_window)
                            self.update_status("Successfully switched to new tab")

                            # Define XPaths
                            xpaths = {
                                "name": '//*[@id="site-content"]/div/div[1]/div[1]/div[1]/div/div/div/div/div/section/div/div[1]/div/h1',
                                "guests": '//*[@id="site-content"]/div/div[1]/div[3]/div/div[1]/div/div[1]/div/div/div/section/div[2]/ol/li[1]',
                                "bedrooms": '//*[@id="site-content"]/div/div[1]/div[3]/div/div[1]/div/div[1]/div/div/div/section/div[2]/ol/li[2]',
                                "beds": '//*[@id="site-content"]/div/div[1]/div[3]/div/div[1]/div/div[1]/div/div/div/section/div[2]/ol/li[3]',
                                "baths": '//*[@id="site-content"]/div/div[1]/div[3]/div/div[1]/div/div[1]/div/div/div/section/div[2]/ol/li[4]',
                                "location_rating": '//*[@id="site-content"]/div/div[1]/div[4]/div/div/div/div[2]/div/section/div[2]/div/div/div[3]/div/div/div/div/div[6]/div/div/div[2]/div[2]'
                            }

                            # Get listing details using existing XPaths and logic
                            
                            # Find and scroll to location rating element (it's usually at the bottom)
                            try:
                                location_element = WebDriverWait(self.driver, 10).until(
                                    EC.presence_of_element_located((By.XPATH, xpaths["location_rating"]))
                                )
                                self.scroll_to_element(location_element)
                            except:
                                self.update_status("Warning: Could not find location rating section")

                            # Extract all details
                            details = {}
                            self.update_status("\nExtracting listing details:")
                            self.update_status("-" * 30)
                            for key, xpath in xpaths.items():
                                try:
                                    element = WebDriverWait(self.driver, 5).until(  # Reduced from 10 to 5
                                        EC.presence_of_element_located((By.XPATH, xpath))
                                    )
                                    details[key] = element.text
                                    self.update_status(f"{key}: {details[key]}")
                                except:
                                    details[key] = "N/A"
                                    self.update_status(f"{key}: N/A (not found)")
                            
                            # Process details and create listing object
                            listing_details = {
                                "name": details["name"],
                                "guest_limit": self._extract_number(details["guests"]),
                                "bedrooms": self._extract_number(details["bedrooms"]),
                                "beds": self._extract_number(details["beds"]),
                                "bathrooms": self._extract_number(details["baths"]),
                                "stars": rating,
                                "review_count": review_count,
                                "price_per_night": price_per_night,
                                "total_price": total_price,
                                "number_of_nights": num_nights,
                                "location_rating": details.get("location_rating", "N/A"),
                                "url": self.driver.current_url
                            }
                            
                            try:
                                # Check for Guest Favorite badge
                                try:
                                    guest_favorite = self.driver.find_element(
                                        By.XPATH,
                                        '//*[@id="site-content"]/div/div[1]/div[4]/div/div/div/div[2]/div/section/div[1]/div[2]'
                                    ).is_displayed()
                                    self.update_status(f"Guest Favorite: {guest_favorite}")
                                except:
                                    guest_favorite = False
                                    self.update_status("Guest Favorite badge not found")

                                # Get full page content for historical analysis
                                full_content = self.driver.find_element(
                                    By.XPATH,
                                    '//*[@id="site-content"]/div/div[1]'
                                ).text
                                
                                # Check for historical house using simple text matching
                                historical_analysis = self.check_historical_house(full_content)
                                self.update_status(f"\nHistorical analysis: {json.dumps(historical_analysis, indent=2)}")

                                # Update listing_details with new information
                                listing_details.update({
                                    "is_guest_favorite": guest_favorite,
                                    "is_historical": historical_analysis["is_historical"],
                                    "historical_evidence": historical_analysis["evidence"]
                                })

                                # Get amenities text
                                amenities_text = self.get_amenities_text()
                                if amenities_text:
                                    self.update_status("\nAnalyzing amenities with text matching...")
                                    amenities_analysis = self.check_amenities_with_text_matching(amenities_text)
                                    if amenities_analysis:
                                        listing_details["amenities_analysis"] = amenities_analysis
                                        # print("\nAmenities analysis:")
                                        # print(json.dumps(amenities_analysis, indent=2))
                            except Exception as e:
                                self.update_status(f"Error processing amenities: {str(e)}")
                                listing_details["amenities_analysis"] = {}
                            
                            self.update_status("\nProcessed listing details:")
                            self.update_status("-" * 30)
                            self.update_status(json.dumps(listing_details, indent=2))
                            
                            # After all extractions, check for missing fields
                            missing_fields = [k for k, v in listing_details.items() if v == "N/A"]
                            if missing_fields:
                                self.update_status(f"\nAttempting to extract missing fields: {missing_fields}")
                                # additional_details = self.extract_missing_details(full_content, missing_fields)
                                # for field, value in additional_details.items():
                                #     if field in missing_fields and value:
                                #         listing_details[field] = value
                                #         self.update_status(f"Updated {field} to: {value}")

                            all_listings.append(listing_details)
                            self.update_output_files(listing_details)  # Update files in real-time

                            # After all processing is done, close current tab and switch back to grid
                            self.update_status("\nClosing listing tab and returning to grid...")
                            self.driver.close()
                            self.driver.switch_to.window(original_window)
                            self.update_status("Successfully returned to grid view")
                        
                        except Exception as e:
                            self.update_status(f"\nError processing listing {index}: {str(e)}")
                            # Make sure we're back on the original window
                            if len(self.driver.window_handles) > 1 and self.driver.current_window_handle != original_window:
                                self.update_status("Closing error tab and switching back to main window...")
                                self.driver.close()
                                self.driver.switch_to.window(original_window)
                    
                    self.update_status(f"\n{'='*50}")
                    self.update_status(f"Final Results - Successfully processed {len(all_listings)} listings")
                    self.update_status(f"{'='*50}")
                    self.update_status(json.dumps(all_listings, indent=2))
                    
                    # After processing all items in the current page
                    if current_page < num_pages:
                        # Find and click next page link
                        next_page = self.get_next_page_link()
                        if next_page:
                            url = next_page.get_attribute('href')
                            current_page += 1
                            self.update_status(f"\nMoving to page {current_page}...")
                            continue
                        else:
                            self.update_status("\nNo more pages available, ending scrape")
                    break
                    
                    current_page += 1
                    
                except Exception as e:
                    self.update_status(f"Error processing page {current_page}: {str(e)}")
                    break
                    
                except TimeoutException:
                    self.update_status("Timeout waiting for listings to load")
                except Exception as e:
                    self.update_status(f"Error processing listings: {str(e)}")
                
        except Exception as e:
            self.update_status(f"Error in scrape_url: {str(e)}")
        
        return all_listings
    
    def _calculate_price_per_night(self, details):
        """Helper method to calculate price per night"""
        try:
            total_price = self._clean_price(details["price"])
            nights_text = details["nights"].lower()
            num_nights = int(''.join(filter(str.isdigit, nights_text)))
            return str(int(total_price) // num_nights) if num_nights > 0 else total_price
        except:
            return "N/A"
    
    def _parse_page(self):
        """Parse the current page and extract listing information"""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        listings = soup.find_all("div", {"itemprop": "itemListElement"})
        
        for listing in listings:
            try:
                # Extract listing data
                listing_data = {
                    'title': self._get_text(listing, "meta[itemprop='name']", attr='content'),
                    'url': self._get_text(listing, "meta[itemprop='url']", attr='content'),
                    'price': self._clean_price(listing.find("span", {"class": "_tyxjp1"}).text if listing.find("span", {"class": "_tyxjp1"}) else "N/A"),
                    'rating': self._get_text(listing, "span[class*='r1dxllyb']"),
                    'reviews': self._get_text(listing, "span[class*='r1dxllyb']").split(' ')[0] if listing.find("span", {"class": "r1dxllyb"}) else "0",
                    'type': self._get_text(listing, "div[class*='t1jojoys']"),
                    'amenities': self._get_text(listing, "div[class*='f15liw5s']"),
                    'scraped_date': datetime.now().strftime("%Y-%m-%d")
                }
                
                self.results.append(listing_data)
                
            except Exception as e:
                self.update_status(f"Error parsing listing: {str(e)}")
                continue
    
    def _get_text(self, element, selector, attr=None):
        """Helper method to safely extract text or attribute from an element"""
        try:
            found = element.select_one(selector)
            if found:
                return found[attr] if attr else found.text.strip()
            return "N/A"
        except:
            return "N/A"
    
    def _clean_price(self, price_str):
        """Clean price string to extract only the number"""
        try:
            return ''.join(filter(str.isdigit, price_str))
        except:
            return "N/A"
    
    def save_results(self, filename=None):
        """This method is now deprecated since we're saving in real-time"""
        self.update_status(f"Results are being saved in real-time to: {self.run_dir}")
        self.update_status(f"JSON file: {self.json_file}")
        self.update_status(f"CSV file: {self.csv_file}")
    
    def close(self):
        """Close the browser"""
        self.driver.quit()

    def _extract_number(self, text):
        """Helper method to extract numeric values including decimals from text"""
        try:
            # Find all numbers including decimals in the text
            numbers = re.findall(r'\d*\.?\d+', text)
            return numbers[0] if numbers else "N/A"
        except:
            return "N/A"

    def check_amenities_with_text_matching(self, amenities_text):
        """Check amenities using text matching with comprehensive variations"""
        amenity_variations = {
            "TV": [
                "tv", "television", "smart tv", "cable tv", "hdtv", "roku", 
                "netflix", "streaming", "apple tv", "flat screen"
            ],
            "Pool": [
                "pool", "swimming pool", "outdoor pool", "indoor pool", 
                "heated pool", "lap pool", "plunge pool"
            ],
            "Jacuzzi": [
                "jacuzzi", "hot tub", "whirlpool", "jetted tub", 
                "soaking tub", "spa tub"
            ],
            "Billiards/Pool Table": [
                "pool table", "billiards", "billiard table", "game table", 
                "gaming table", "pool cue"
            ],
            "Large Yard": [
                "yard", "garden", "backyard", "outdoor space", "patio", 
                "lawn", "courtyard", "grounds"
            ],
            "Balcony": [
                "balcony", "deck", "terrace", "porch", "veranda", 
                "outdoor deck", "private balcony"
            ],
            "Laundry": [
                "laundry", "washer", "dryer", "washing machine", "laundromat",
                "clothes washer", "clothes dryer", "washer/dryer"
            ],
            "Home Gym": [
                "gym", "fitness", "exercise", "workout", "weight", 
                "treadmill", "exercise equipment", "fitness room"
            ]
        }
        
        # Convert amenities text to lowercase for case-insensitive matching
        amenities_text_lower = amenities_text.lower()
        
        # Initialize results dictionary
        results = {
            amenity: False for amenity in amenity_variations.keys()
        }
        
        # Store evidence of matches
        evidence = {}
        
        # Check each amenity
        for amenity, variations in amenity_variations.items():
            matches = []
            for variation in variations:
                if variation in amenities_text_lower:
                    matches.append(variation)
            
            if matches:
                results[amenity] = True
                # Get some context around the first match
                first_match = matches[0]
                index = amenities_text_lower.find(first_match)
                start = max(0, index - 50)
                end = min(len(amenities_text), index + len(first_match) + 50)
                context = amenities_text[start:end].strip()
                evidence[amenity] = {
                    "matched_terms": matches,
                    "context": context
                }
        
        # Add evidence to results
        # results["_evidence"] = evidence
        
        return results

def main():
    # Example usage
    scraper = AirbnbScraper()
    
    try:
        # Get the Airbnb search URL from user
        url = input("Enter the complete Airbnb search URL: ")
        num_pages = int(input("Enter number of pages to scrape (default 5): ") or 5)
        
        print(f"\nScraping Airbnb listings...")
        scraper.scrape_url(url, num_pages=num_pages)
        
        # Save results
        scraper.save_results()
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
