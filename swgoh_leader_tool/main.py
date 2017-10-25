import os
import json
import re
from PIL import Image
import pandas as pd

from ocr_space_helper.ocr_space_helper import *

OCR_API_KEY = '10aa254e3788957'

# in percentage, ratio to crop the text we want (tickets + name)
x1 = 0.39340102
y1 = 0.27067669
x2 = 0.95600677
y2 = 0.95488722


def RepresentsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


im = Image.open(os.path.join('static', 'img', 'maegor.png'))
# im = im.crop((im.size[0]*x1, im.size[1]*y1, im.size[0]*x2, im.size[1]*y2))
# im.save('temp.jpg')


test_file = ocr_space_file(filename='static/img/eng.png', api_key=OCR_API_KEY)
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

tickets = [t for t in tickets.splitlines() if RepresentsInt(t)]
print(tickets)


# names = result.split('Daily Raid Tickets')[0]
# names = [n.strip() for n in names.split('Member ') if n.strip()]
# tickets = "".join(result.split('Daily Raid Tickets')[1:])
# tickets = [t.strip() for t in tickets.split('Produced:') if t.strip()]
# if len(names) > len(tickets):
#     names = names[:-1]
# elif len(names) < len(tickets):
#     tickets = tickets[1:]
# df = pd.DataFrame(tickets, index=names, columns=['Tickets'])
# print(result)
# print(names)
# print(tickets)
# print(test_file)
# print(df)

