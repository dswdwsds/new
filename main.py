from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

options = Options()
options.headless = True
driver = webdriver.Chrome(options=options)

url = "https://4g.r5t6y7.shop/episode/akujiki-reijou-to-kyouketsu-koushaku-%d8%a7%d9%84%d8%ad%d9%84%d9%82%d8%a9-3/"
driver.get(url)

try:
    iframe = driver.find_element(By.XPATH, '/html/body/div/div/div[3]/div[2]/div[1]/div[2]/div[2]/div/div/div/div/iframe')
    print("رابط السيرفر:", iframe.get_attribute("src"))
except:
    print("لم يتم العثور على رابط السيرفر")

driver.quit()
