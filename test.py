from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# Setup ChromeDriver
options = Options()
options.add_argument("--headless")
service = Service("C:\chromedriver_win32\chromedriver.exe")  # Update with your path

# Test ChromeDriver
driver = webdriver.Chrome(service=service, options=options)
driver.get("https://www.google.com")
print(driver.title)  # Should print "Google"
driver.quit()
