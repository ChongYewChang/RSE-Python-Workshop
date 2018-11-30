import requests
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
import re
import os
import pickle
import sqlalchemy
import json
import datetime
import re
from collections import defaultdict
import sys

def web_scrape(root):
    """This function is the main web scraping method, it generates a dictionary of key = rooms & values = class times.

    Args:
        root (str):  The url index to use
        result (list): A mutable which stores thread output
        num (int): index of result output
    """
    rawHtml = simple_get(root)
    campus = filter_campus(rawHtml)
    links = get_subject_links(campus[0])
    # only select semester 2 units
    subj_links = list(filter(lambda x: "T1" in x,links))
    schedule = defaultdict(list)
    for val in subj_links:
        timetable = simple_get(root + val)
        extract_timetable(timetable,schedule)
#         print("Completed extracting course")
    # index result for accessing thread return value
    return schedule

def filter_campus(rawHtml):
    """This function allows you to filter the results of the web scraper by university campus

    Args:
        rawHtml (String): raw string HTML from requests

    Return:
        Table data for campus in list form

    Notes:
        0 = KENS, 1 = PADDINGTON, 2 = AFDA
    """
    html = BeautifulSoup(rawHtml,'html.parser')
    regex = 'class="cutabhead"'
    campus = re.split(regex,str(html.select('table')[1]))
    return campus[1:]

def get_subject_links(rawHtml):
    """This function allows you to filter the results of the web scraper by university campus

    Args:
        rawHtml (String): raw string HTML from requests

    Return:
        List of links for all subjects for a particular campus

    Notes:
        links for subjects look like this 'SOCF_S1.html'
    """
    html = BeautifulSoup(rawHtml,'html.parser')
    links = [k.get('href') for k in html.find_all('a')]
    subjectLinks = list(filter(lambda x: "http" not in x,links))
    return subjectLinks

def extract_timetable(rawHtml,schedule):
    """This function allows you to extract the timetable data for a course and add it to a dictionary

    Args:
        rawHtml (String): raw string HTML from requests
        schedule (Dictionary): maintains global state of extraction

    """
    html = BeautifulSoup(rawHtml,'html.parser')
    # 1-> subject list, 2-> course table
    table = html.select('table')[2]
    subj_table = str(table.find("tr"))
    # remove subject list from html, probs dont need to replace table if parsing on highlight/lowlight tr cells
    table = "".join(list(map(str,table.descendants))).replace(subj_table,"")
    #try refine regex or pass in better data
    regex = "<tr>.+?name=\"\w+?\".+?valign=\"center\">.+?</tr>"
    subjects = re.split(regex,table,flags=re.DOTALL | re.MULTILINE)
    # split the subject code into courses
    for data in subjects[1:]:
        html = BeautifulSoup(data,"html.parser")
        classes = html.find_all(class_ = ("rowLowlight","rowHighlight"))
        name = extract_name(html)
        # add each session for a course
        for item in classes:
            cols = list(item.stripped_strings)
            # if list is too long then trim
            if len(cols) > 8:
                cols = cols[:8]
            # add to dict with primary key room -> [{}]
            if check_valid_course(cols):
                add_session(cols,schedule,name)


def check_valid_course(cols):
    """This function allows you to filter if a course should be added to a schedule

    Args:
        cols (List): list of data for a course offering
    
    Returns:
        Boolean: If true then a course is valid and should be added to a schedule

    Notes:
        a valid course is one that will be stored in db
        course is valid if status = full | open
        course is valid if COMP = LEC | TUT | SEM | TLB | OTH
    """
    # web streams?
    if cols[4] not in ["Full","Open"]:
        return False
    elif cols[0] not in ["LEC", "TUT","SEM", "TLB", "OTH"]:
        return False
    else:
        return True

def add_session(cols,schedule,name):
    """This function creates the mapping for rooms and course timetables

    Args:
        cols (List): list of data for a course offering from a column in a html table
        schedule (Dictionary): Maintains state for all courses
        name (String): Name of a course

    Notes:
        Sample data 'Mon 11-14 (w1-6, BUS 105); Mon 11-14 (w7-9,10-12, PioneerTh)
    """
    try:
        '''
        ACCT2522  	
        Management Accounting 1, LEC, W09A, Wed 09-10:30 (w1-10, SEB B25)
        '''
        info = (name[0],cols[0],cols[1],cols[-1])
    except:
        # seminars dont have rooms, deviant data can be ignored
        pass
    else:
        # default dict lambda lists !!
        schedule[name[1]].append(info)

def extract_name(html):
    """This function extracts the name of a course in a html table column

    Args:
        html (String): raw Html response
    
    Returns:
        Tuple: course name, course code

    """
    # get cucourse strings
    name = html.findAll(class_="cucourse")
    # Course codes have semster offerings inside
    code = name[0].a['name'].replace("T1","")
    course_name = name[1].string
    return (course_name,code)

def simple_get(url):
    try:
        with closing(requests.get(url)) as resp:
            # if request is ok
            if resp.status_code == 200:
                return resp.content
            else:
                return None
    except RequestException as e:
        print(f"Error during requests to {url}: {e}")


if __name__ == "__main__":
    
#     print (sys.getrecursionlimit())
#     sys.setrecursionlimit(50000) 
    timetable = web_scrape("http://classutil.unsw.edu.au/")
#     print (json.dumps(timetable,sort_keys=True, indent=4))
    sys.getsizeof(timetable)
#     with open('timetable.pickle', 'wb') as handle:
#         pickle.dump(timetable, handle, protocol=pickle.HIGHEST_PROTOCOL)
#         print("Saving completed")
#     with open('timetable.pickle', 'rb') as handle:
#         b = pickle.load(handle)
#     print(timetable == b)
#     print(b)

#     while True:
#         course = input("Please enter a course code\n")
#         print(timetable[course])