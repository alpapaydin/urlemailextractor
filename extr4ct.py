try:
    from selenium import webdriver
    from webdriver_manager.chrome import ChromeDriverManager
    NO_SELENIUM = False                 
except ImportError:
    NO_SELENIUM = True
from requests import get                  
from bs4 import BeautifulSoup
import sys
import re
import mysql.connector

db = mysql.connector.connect(
  host="localhost",
  user="root",
  password="",
  database="beverwijk"
) 

crs = db.cursor()
crs.autocommit = True
crs2 = db.cursor()
crs2.autocommit = True

getURLs="""SELECT Website FROM kontak WHERE Email=''"""
updateEmail="""UPDATE kontak SET Email=%s WHERE Website=%s"""

crs.execute(getURLs)
urllist=crs.fetchall()

def get_html_from_url(url, render_js=False):
    response = ''
    if render_js:
        if NO_SELENIUM:
            print('Selenium module not installed!')
        else:
            with webdriver.Chrome(ChromeDriverManager().install()) as browser:
                browser.get(url)
                response = browser.page_source
    else: 
        response = get(url).text 
    return response

def find_emails(html):
    parser = 'html.parser'
    soup = BeautifulSoup(html, parser)
    email_list = set()
    email_regex = re.compile(r"^[\w.-]+@[\w.-]+\.\w+$")
    tags_with_email = soup.find_all(string=email_regex)
    links_with_email = [link for link in map(str, soup.find_all(href=email_regex))]
    text_with_email = tags_with_email + links_with_email
    for item in text_with_email:
        for email in email_regex.findall(item):
            email_list.add(email)
    return email_list

def extractsite(url):

    print('URL: {}'.format(url))
    if '-js' in args:
        render_js = True
        print('Rendering with Selenium...')
    else:
        render_js = False
        print('Getting static HTML...')
    html = get_html_from_url(url, render_js=render_js)
    print('Building email address list...')
    email_list = find_emails(html)
    print('Writing email addresses to SQL...')
    if email_list:
        print(format(url))
        print(list(email_list)[0])
        updateval=(list(email_list)[0], format(url))
        crs2.execute(updateEmail, updateval)
        db.commit()

    print('Done!')

def LoopUrlFile():
    for link in urllist:
        try:
            extractsite(link[0])
        except:
            print("Error")

if __name__ == "__main__":

    args = sys.argv
    
    LoopUrlFile()