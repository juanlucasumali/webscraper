import streamlit as st
from webscraper import AirbnbScraper
import pandas as pd
import json
import os

def main():
    st.title("Airbnb Listing Scraper")
    st.write("Enter an Airbnb search URL and number of pages to scrape.")

    # Input fields
    url = st.text_input("Airbnb Search URL", "")
    num_pages = st.number_input("Number of pages to scrape", min_value=1, max_value=20, value=5)

    # Create empty DataFrame with all columns
    empty_df = pd.DataFrame(columns=[
        "Link", "Name", "Bedrooms", "Beds", "Bathrooms", "Guest Limit", 
        "Stars", "Price/Night in May", "AirBnB Location Rating", "Source", 
        "Amenities", "TV", "Pool", "Jacuzzi", "Historical House", 
        "Billiards Table", "Large Yard", "Balcony", "Laundry", "Home Gym",
        "Guest Favorite Status"
    ])

    # Create containers for output - table first, then terminal
    st.write("Real-time Results (data will appear as listings are scraped):")
    table_container = st.empty()
    
    # Display empty table with column configurations
    table_container.dataframe(
        empty_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Link": st.column_config.LinkColumn("Link"),
            "TV": st.column_config.CheckboxColumn("TV"),
            "Pool": st.column_config.CheckboxColumn("Pool"),
            "Jacuzzi": st.column_config.CheckboxColumn("Jacuzzi"),
            "Historical House": st.column_config.CheckboxColumn("Historical House"),
            "Billiards Table": st.column_config.CheckboxColumn("Billiards Table"),
            "Large Yard": st.column_config.CheckboxColumn("Large Yard"),
            "Balcony": st.column_config.CheckboxColumn("Balcony"),
            "Laundry": st.column_config.CheckboxColumn("Laundry"),
            "Home Gym": st.column_config.CheckboxColumn("Home Gym"),
            "Guest Favorite Status": st.column_config.CheckboxColumn("Guest Favorite")
        }
    )

    st.write("Real-time Scraping Log:")
    terminal_container = st.empty()
    
    # Initialize session state for messages and listings
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'listings' not in st.session_state:
        st.session_state.listings = []

    if st.button("Start Scraping"):
        if not url:
            st.error("Please enter a valid Airbnb search URL")
            return

        try:
            # Clear previous data
            st.session_state.messages = []
            st.session_state.listings = []
            
            def update_status(message):
                # If message is a tuple or multiple arguments, join them with a space
                if isinstance(message, tuple):
                    message = ' '.join(str(m) for m in message)
                
                # Add new message to the list
                st.session_state.messages.append(message)
                
                # Create a terminal-like display with all messages
                terminal_html = f"""
                <div style="
                    background-color: black;
                    color: #32CD32;
                    padding: 10px;
                    border-radius: 5px;
                    font-family: monospace;
                    height: 400px;
                    overflow-y: scroll;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                ">
                    {'<br>'.join(st.session_state.messages)}
                </div>
                """
                terminal_container.markdown(terminal_html, unsafe_allow_html=True)

            def update_table(listing_details):
                # Add new listing to the session state with all CSV columns
                st.session_state.listings.append({
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
                })
                
                # Create DataFrame from all listings
                df = pd.DataFrame(st.session_state.listings)
                
                # Update the table with column configurations
                table_container.dataframe(
                    df,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Link": st.column_config.LinkColumn("Link"),
                        "TV": st.column_config.CheckboxColumn("TV"),
                        "Pool": st.column_config.CheckboxColumn("Pool"),
                        "Jacuzzi": st.column_config.CheckboxColumn("Jacuzzi"),
                        "Historical House": st.column_config.CheckboxColumn("Historical House"),
                        "Billiards Table": st.column_config.CheckboxColumn("Billiards Table"),
                        "Large Yard": st.column_config.CheckboxColumn("Large Yard"),
                        "Balcony": st.column_config.CheckboxColumn("Balcony"),
                        "Laundry": st.column_config.CheckboxColumn("Laundry"),
                        "Home Gym": st.column_config.CheckboxColumn("Home Gym"),
                        "Guest Favorite Status": st.column_config.CheckboxColumn("Guest Favorite")
                    }
                )

            # Initialize scraper with both update functions
            scraper = AirbnbScraper(update_status=update_status)
            
            # Monkey patch the update_output_files method to also update the table
            original_update_output_files = scraper.update_output_files
            def new_update_output_files(listing_details):
                original_update_output_files(listing_details)
                update_table(listing_details)
            scraper.update_output_files = new_update_output_files
            
            listings = scraper.scrape_url(url, num_pages=num_pages)
            
            if listings:
                # Show results
                st.success(f"Successfully scraped {len(listings)} listings!")
                
                # Display run directory information
                st.write(f"Results saved in: {scraper.run_dir}")
                st.write(f"JSON file: {scraper.json_file}")
                st.write(f"CSV file: {scraper.csv_file}")

                # Add download buttons
                if os.path.exists(scraper.csv_file):
                    df = pd.read_csv(scraper.csv_file)
                    st.download_button(
                        label="Download CSV",
                        data=df.to_csv(index=False),
                        file_name="airbnb_listings.csv",
                        mime="text/csv"
                    )

                    with open(scraper.json_file, 'r') as f:
                        json_str = json.dumps(json.load(f), indent=2)
                        st.download_button(
                            label="Download JSON",
                            data=json_str,
                            file_name="airbnb_listings.json",
                            mime="application/json"
                        )

            else:
                st.error("Please refresh the page and try again.")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
        
        finally:
            try:
                scraper.close()
            except:
                pass

if __name__ == "__main__":
    main() 