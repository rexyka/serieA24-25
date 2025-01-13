from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver():
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())  # Automatically downloads the correct ChromeDriver
    return webdriver.Chrome(service=service, options=options)

# Scraping Function
def scrape_fbref_table_selenium(url, table_id, output_file):
    try:
        # Initialize the driver
        driver = setup_driver()

        # Navigate to the URL
        st.info(f"Connecting to {url}...")
        driver.get(url)

        # Wait for the table to load
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, table_id)))

        # Parse the page with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.find("table", {"id": table_id})
        if not table:
            st.error(f"Table with ID '{table_id}' not found on page {url}.")
            driver.quit()
            return None

        # Extract headers
        thead = table.find("thead")
        header_row = thead.find_all("tr")[-1]
        headers = [cell["data-stat"] for cell in header_row.find_all("th") if "data-stat" in cell.attrs]

        # Extract rows
        tbody = table.find("tbody")
        rows = [
            [cell.get_text(strip=True) for cell in row.find_all(["th", "td"])]
            for row in tbody.find_all("tr")
        ]

        # Normalize rows
        normalized_rows = []
        for row in rows:
            if len(row) < len(headers):
                row += [""] * (len(headers) - len(row))
            elif len(row) > len(headers):
                row = row[:len(headers)]
            normalized_rows.append(row)

        # Create and save DataFrame
        df = pd.DataFrame(normalized_rows, columns=headers)
        df.to_excel(output_file, index=False)
        st.success(f"Data saved to {output_file}!")

        driver.quit()  # Close the browser
        return df

    except Exception as e:
        st.error(f"Error during scraping: {e}")
        return None

# Streamlit App
st.title("FBref Serie A Scraper & Analysis")

# URLs, table IDs, and output files
datasets = {
    "Basic Stats": {"url": "https://fbref.com/en/comps/11/stats/Serie-A-Stats", "table_id": "stats_standard", "output": "basic_stats.xlsx"},
    "Advanced Goalkeeper Stats": {"url": "https://fbref.com/en/comps/11/keepersadv/Serie-A-Stats", "table_id": "stats_keeper_adv", "output": "adv_goalkeeper_stats.xlsx"},
    "Defensive Stats": {"url": "https://fbref.com/en/comps/11/defense/Serie-A-Stats", "table_id": "stats_defense", "output": "defensive_stats.xlsx"},
    "Possession Stats": {"url": "https://fbref.com/en/comps/11/possession/Serie-A-Stats", "table_id": "stats_possession", "output": "possession_stats.xlsx"},
    "Shooting Stats": {"url": "https://fbref.com/en/comps/11/shooting/Serie-A-Stats", "table_id": "stats_shooting", "output": "shooting_stats.xlsx"},
    "Passing Stats": {"url": "https://fbref.com/en/comps/11/passing/Serie-A-Stats", "table_id": "stats_passing", "output": "passing_stats.xlsx"},
    "Passing Types Stats": {"url": "https://fbref.com/en/comps/11/passing_types/Serie-A-Stats", "table_id": "stats_passing_types", "output": "passing_types_stats.xlsx"},
}

# Option to Scrape All Datasets
st.write("### Scrape All Datasets")
scrape_all_button = st.button("Scrape All Datasets")

if scrape_all_button:
    for name, dataset in datasets.items():
        st.info(f"Scraping {name}...")
        df = scrape_fbref_table_selenium(dataset["url"], dataset["table_id"], dataset["output"])
        if df is not None:
            st.write(f"Preview of {name}:")
            # Format the DataFrame with 2 decimal places
            st.dataframe(df.style.format(precision=2))
    st.success("All datasets scraped successfully!")
