from functions import *


load_dotenv()
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")



options = Options()
options.add_experimental_option("detach", True) 
driver = webdriver.Chrome(options=options)
driver.maximize_window() 
wait = WebDriverWait(driver, 10)


#get_all_course_links()
#login()