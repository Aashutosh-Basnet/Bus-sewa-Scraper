import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Start the WebDriver (make sure the correct driver is installed and in the PATH)
driver = webdriver.Chrome()


def get_source_destination_combinations_from_json():
    try:
        # Load the dropdown options from the JSON file
        with open('dropdown_options.json', 'r') as file:
            dropdown_options = json.load(file)

        # Extract the place names from the JSON
        places = [option['text'] for option in dropdown_options if option.get('text')]

        # Generate all source-destination pairs (excluding pairs where source == destination)
        source_dest_combinations = [(source, destination) for source in places for destination in places if
                                    source != destination]

        return source_dest_combinations

    except Exception as e:
        print(f"An error occurred while reading the JSON file: {e}")
        return []


def scrape_buses(source, destination):
    bus_data = []  # Ensure that partial data can be stored even if an error occurs

    try:
        # Open the BusSewa website
        driver.get('https://bussewa.com')

        # Select source and destination from dropdowns
        source_dropdown = Select(WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'search_from_destination'))
        ))
        destination_dropdown = Select(WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'search_to'))
        ))

        # Select the source and destination by visible text
        source_dropdown.select_by_visible_text(source)
        time.sleep(1)  # To ensure the destination dropdown is populated
        destination_dropdown.select_by_visible_text(destination)

        # Click the date button (make sure the correct class name is used)
        date_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, 'TV0VZ'))  # Update class name as needed
        )
        date_button.click()

        # Click search button (make sure the correct class name is used)
        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, 'btn_1'))  # Update class name as needed
        )
        search_button.click()

        # Wait for the results page to load and scrape the data for up to 5 days
        for day in range(5):
            time.sleep(5)  # Wait for the page to load

            # Collect the date at the top (ensure the correct class name is used)
            date = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'current-date'))  # Update class name as needed
            ).text

            try:
                # Find all the bus cards (ensure the correct class name is used)
                bus_cards = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, 'trip-infos'))  # Update class name as needed
                )

                # Extract information from each bus card
                for bus_card in bus_cards:
                    bus_info = {
                        'from': bus_card.find_element(By.CLASS_NAME, 'trip-fromstationpoint').text,  # Update as needed
                        'to': bus_card.find_element(By.CLASS_NAME, 'trip-tostationpoint').text,  # Update as needed
                        'date': date,
                        'bus_name': bus_card.find_element(By.CLASS_NAME, 'trip-operator').text,  # Update as needed
                        'bus_type': bus_card.find_element(By.CLASS_NAME, 'trip-bustype').text,  # Update as needed
                        'price': bus_card.find_element(By.CLASS_NAME, 'trip-fare').text,  # Update as needed
                        'departure_time': bus_card.find_element(By.CLASS_NAME, 'trip-starttime').text,
                        'arrival_time': bus_card.find_element(By.CLASS_NAME, 'trip-endtime').text
                    }
                    bus_data.append(bus_info)

            # If no buses are found for today, catch the timeout
            except TimeoutException:
                print(f"No buses found for {source} to {destination} on {date}. Checking next day.")

            # Try to click the "Next day" button using the correct ID, unless it's the last day of scraping
            if day < 4:  # Only try to move to the next day if we're not on the last day
                try:
                    next_button = WebDriverWait(driver, 15).until(
                        EC.element_to_be_clickable((By.ID, 'next-day-btn'))  # Using the ID instead of class name
                    )
                    next_button.click()
                except (TimeoutException, NoSuchElementException):
                    print(f"No 'Next day' button found for {date}. Ending scrape for this route.")
                    break

    except Exception as e:
        print(f"An error occurred while scraping {source} to {destination}: {e}")
        driver.save_screenshot(f"error_screenshot_{source}_to_{destination}.png")  # Save a screenshot for debugging

    finally:
        # If no bus data was found, return a message indicating no buses
        if not bus_data:
            return [{'message': f"No buses available for {source} to {destination} for the next 5 days."}]
        return bus_data  # Return the collected data even if there was an error


def main():
    # Automatically get all source-destination combinations from the JSON file
    source_dest_combinations = get_source_destination_combinations_from_json()

    # Dictionary to hold the scraped bus data
    all_bus_data = {}

    try:
        for source, destination in source_dest_combinations:
            print(f"Scraping buses from {source} to {destination}...")
            bus_data = scrape_buses(source, destination)

            # Add the bus data for the current source-destination pair to the dictionary
            all_bus_data[f"{source}_to_{destination}"] = bus_data

            # Save the data to JSON after every iteration to ensure partial data is saved
            with open('bus_data.json', 'w') as json_file:
                json.dump(all_bus_data, json_file, indent=4)

            print(f"Completed scraping {source} to {destination}")

        print("Scraping complete. All data saved to bus_data.json.")

    except Exception as e:
        print(f"An error occurred in main: {e}")

    finally:
        # Ensure the browser quits only at the end
        driver.quit()


if __name__ == "__main__":
    main()
