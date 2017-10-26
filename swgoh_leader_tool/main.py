import os
import json
import re
import pandas as pd

from ocr_space_helper.ocr_space_helper import *

OCR_API_KEY = '10aa254e3788957'


def represents_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def get_tickets_from_image(image_path):
    # test_file = ocr_space_file(filename=os.path.join('static', 'img', 'screenshot1.jpg'), api_key=OCR_API_KEY)
    file = ocr_space_file(filename=image_path, api_key=OCR_API_KEY)
    text_content = json.loads(file)
    text_content = text_content['ParsedResults'][0]['ParsedText']
    if 'INVITE ALLIES' in text_content:
        text_content = text_content.split('INVITE ALLIES')[1]
    else:
        text_content = text_content.split('ALL')[1]
    delimiters = "RAID TICKETS (DAILY)", "RAID TICKETS (LIFETIME)"
    regex_pattern = '|'.join(map(re.escape, delimiters))
    names, tickets = re.split(regex_pattern, text_content)
    names = [n.strip() for n in names.splitlines() if n.strip() and n.strip() not in
             ['85', 'Officer', 'Member', 'PENDING INVITES', 'ALL', 'MY GUILD']]
    tickets = [t for t in tickets.splitlines() if represents_int(t)]
    if len(names) > len(tickets):
        names = names[:-1]
    elif len(names) < len(tickets):
        tickets = tickets[1:]
    return pd.DataFrame(tickets, index=names, columns=['Tickets'])


if __name__ == "__main__":
    print(get_tickets_from_image(os.path.join('static', 'img', 'screenshot1.jpg')))
