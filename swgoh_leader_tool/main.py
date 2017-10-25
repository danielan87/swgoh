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


test_file = ocr_space_file(filename=os.path.join('static', 'img', 'screenshot1.jpg'), api_key=OCR_API_KEY)
old = json.loads(test_file)
result = old['ParsedResults'][0]['ParsedText']
print(old['ParsedResults'][0])
if 'INVITE ALLIES' in result:
    result = result.split('INVITE ALLIES')[1]
else:
    result = result.split('ALL')[1]
delimiters = "RAID TICKETS (DAILY)", "RAID TICKETS (LIFETIME)"
regexPattern = '|'.join(map(re.escape, delimiters))
names, tickets = re.split(regexPattern, result)
names = [n.strip() for n in names.splitlines() if n.strip() and n.strip() not in
         ['85', 'Officer', 'Member', 'PENDING INVITES', 'ALL', 'MY GUILD']]
print(names)

tickets = [t for t in tickets.splitlines() if represents_int(t)]
print(tickets)

if len(names) > len(tickets):
    names = names[:-1]
elif len(names) < len(tickets):
    tickets = tickets[1:]
print(pd.DataFrame(tickets, index=names, columns=['Tickets']))
