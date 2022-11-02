from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from multiprocessing import Queue
from threading import Thread
from bs4 import BeautifulSoup
import logging
import re
import mysql.connector


updateEmail="""UPDATE kontak SET Email=%s WHERE Website=%s"""

getURLs="""SELECT Website FROM kontak WHERE (Email='' OR Email IS NULL) AND Website!='' ORDER BY RAND()"""


db = mysql.connector.connect(
  host="",
  user="",
  password="",
  database=""
) 

crs = db.cursor()
crs.autocommit = True

crs.execute(getURLs)
urllist=crs.fetchall()
urllist.append('STOP')

db.close
crs.close

options = Options()
options.headless = True
options.add_argument("--window-size=1920,1080")
options.add_argument('--ignore-certificate-errors')
options.add_argument('--allow-running-insecure-content')
options.add_argument("--log-level=3")
user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36'
options.add_argument(f'user-agent={user_agent}')

logger = logging.getLogger(__name__)

selenium_data_queue = Queue()
worker_queue = Queue()

worker_ids = list(range(4)) #cpu_count()
selenium_workers = {i: webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()),options=options) for i in worker_ids}
for worker_id in worker_ids:
    worker_queue.put(worker_id)

def get_html_from_url(worker, url):
    response = ''
    worker.get(url)
    response = worker.page_source
    return response

def find_emails(html):
    parser = 'html.parser'
    soup = BeautifulSoup(html, parser)
    email_list = set()
    email_regex = re.compile(r"[\w.-]+(?:\[at\]|@)[\w.-]+\.\w+") #### AI kısmı ^[\w.-]+@[\w.-]+\.\w+$
    tags_with_email = soup.find_all(string=email_regex)
    links_with_email = [link for link in map(str, soup.find_all(href=email_regex))]
    text_with_email = tags_with_email + links_with_email
    for item in text_with_email:
        for email in email_regex.findall(item):
            email_list.add(email)
    return email_list

def extractsite(worker, url):
    try:
        db = mysql.connector.connect(
    host="fleecyminimal.com",
    user="admin",
    password="alpalp123",
    database="beverwijk",
    ) 
        crs = db.cursor()
        crs.autocommit = True  
        print('URL: {}'.format(url))
        html = get_html_from_url(worker, url)
        #print('Building email address list...')
        email_list = find_emails(html)
        if email_list:
            #print(list(email_list))
            print(u"\u001b[32m["+str(len(list(email_list)))+"] Got "+list(email_list)[0]+" from "+format(url)+"\u001b[0m")
            updateval=(list(email_list)[0], format(url))
            crs.execute(updateEmail, updateval)
            db.commit()
    except:
        print(u"\u001b[30mError\u001b[0m")



def selenium_queue_listener(data_queue, worker_queue):
    
    logger.info("Selenium func worker started")
    while True:
        current_data = data_queue.get()
        if current_data == 'STOP':

            logger.warning("STOP encountered, killing worker thread")
            data_queue.put(current_data)
            break
        else:
            logger.info(f"Got the item {current_data} on the data queue")

        worker_id = worker_queue.get()
        worker = selenium_workers[worker_id]
        extractsite(worker, current_data[0])

        worker_queue.put(worker_id)
    return


logger.info("Starting selenium background processes")

selenium_processes = [Thread(target=selenium_queue_listener,
                             args=(selenium_data_queue, worker_queue)) for _ in worker_ids]
for p in selenium_processes:
    p.daemon = True
    p.start()

logger.info("Adding data to data queue")
for d in urllist:
    selenium_data_queue.put(d)

logger.info("Waiting for Queue listener threads to complete")
for p in selenium_processes:
    p.join()

logger.info("Tearing down web workers")
for b in selenium_workers.values():
    b.quit()
