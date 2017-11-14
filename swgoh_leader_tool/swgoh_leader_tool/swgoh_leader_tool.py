import os
import json
import re
import pandas as pd
import datetime
import redis
import ocr_space_helper.ocr_space_helper as ocr_space_helper
import cv2
import numpy as np
import urllib
import math
import requests
from PIL import Image
import uuid
from .settings import REDIS_CONN_INFO, OCR_API_KEY
r = redis.StrictRedis(host=REDIS_CONN_INFO.get('host'), port=REDIS_CONN_INFO.get('port'), db=REDIS_CONN_INFO.get('db'))


def represents_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def read_and_classify_image(author, image_path, mode='local'):
    """
    Check if the given image is a "ticket" image. If it is, return True and save to database.
    :param author:
    :param image_path:
    :param mode:
    :return:
    """
    temp_image_file_name = "{}.jpg".format(uuid.uuid4())
    if mode == 'remote':
        img_data = requests.get(image_path).content
        with open(temp_image_file_name, 'wb') as handler:
            handler.write(img_data)

        if os.stat(temp_image_file_name).st_size > 1024000:
            with Image.open(temp_image_file_name) as im:
                im.save(temp_image_file_name, format="JPEG", quality=int(1000000 / os.stat(temp_image_file_name).st_size * 100))
    file = ocr_space_helper.ocr_space_file(filename=temp_image_file_name, api_key=OCR_API_KEY)
    os.remove(temp_image_file_name)
    text_content = json.loads(file)
    text_content = text_content['ParsedResults'][0]['ParsedText']
    if 'RAID TICKETS (' in text_content:
        print("{} is a 'ticket' image! Saving to database.".format(image_path))
        now = datetime.datetime.now()
        r.sadd("{}:ticket:{}".format(author, now.strftime('%Y%m%d')), text_content)
        r.expire("{}:ticket:{}".format(author, now.strftime('%Y%m%d')), 2592000)
        r.set("{}:ticket:lastdate".format(author), now.strftime('%Y%m%d'))
        r.expire("{}:ticket:lastdate".format(author), 2592000)
        return 'tickets', None, None
    if 'Platoon' in text_content or 'SQUADRON' in text_content:
        regexp = re.compile(r'\d-Star')
        result = regexp.search(text_content)
        positions = result.regs[0]
        star = int(text_content[int(positions[0])])
        t = 'platoon' if 'Platoon' in text_content else 'squadron'
        final_count = get_toon_list_from_icon_img(image_path, mode, t)
        return 'platoons', final_count, star
    return False, None, None


def get_toon_list_from_icon_img(url, mode, t='platoon'):
    if mode == 'local':
        return "Error"
    user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
    headers = {'User-Agent': user_agent, }
    request = urllib.request.Request(url, None, headers)
    resp = urllib.request.urlopen(request)
    img_rgb = np.asarray(bytearray(resp.read()), dtype="uint8")
    img_rgb = cv2.imdecode(img_rgb, cv2.IMREAD_COLOR)
    img_rgb = cv2.resize(img_rgb, (1334, 750))
    total_count = 0
    if t == 'platoon':
        icons_path = os.path.join(os.getcwd(), 'static', 'img', 'platoon_icons')
    else:
        icons_path = os.path.join(os.getcwd(), 'static', 'img', 'squadron_icons')
    icons = os.listdir(icons_path)
    final_count = {}
    for i in icons:
        template = cv2.imread(os.path.join(icons_path, i))
        h, w = template.shape[:-1]
        res = cv2.matchTemplate(img_rgb, template, cv2.TM_CCOEFF_NORMED)
        threshold = .9
        loc = np.where(res >= threshold)
        loc_x = list(loc[0])
        loc_y = list(loc[1])
        new_x = []
        new_y = []
        while loc_x:
            new_x.append(loc_x[0])
            loc_x = [i for i in loc_x if not math.isclose(new_x[-1], i, abs_tol=5)]
        while loc_y:
            new_y.append(loc_y[0])
            loc_y = [i for i in loc_y if not math.isclose(new_y[-1], i, abs_tol=5)]
        loc = (tuple(new_x), tuple(new_y))
        if len(loc[0]) > 0:
            final_count[i.split('.')[0]] = len(loc[0])
            total_count += len(loc[0])
            if total_count > 15:
                break
    return final_count


def get_ticket_content(author, date):
    """
    Return ticket data for an author/date
    :param author:
    :param date:
    :return:
    """
    if date:
        if r.exists('{}:ticket:{}'.format(author, date)):
            return [l.decode('utf-8') for l in r.smembers('{}:ticket:{}'.format(author, date))], date
    else:
        if r.exists('{}:ticket:lastdate'.format(author)):
            date = r.get('{}:ticket:lastdate'.format(author)).decode('utf-8')
            return [l.decode('utf-8') for l in r.smembers('{}:ticket:{}'.format(author, date))], date
    return [], date


def get_tickets_from_image(text_content):
    """
    Parse an image data and get the list of names/tickets
    :param text_content:
    :return:
    """
    if 'INVITE ALLIES' in text_content:
        text_content = text_content.split('INVITE ALLIES')[1]
    if 'ALL' in text_content:
        text_content = text_content.split('ALL')[1]
    # might be some stuff left..
    if '/50' in text_content:
        text_content = text_content.split('/50')[1]
    try:
        delimiters = "Tickets Produced", "Daily Raid Tickets"
        regex_pattern = '|'.join(map(re.escape, delimiters))
        names, tickets = re.split(regex_pattern, text_content, 1)
        tickets = 'Daily Raid Tickets' + tickets
    except ValueError as ve:
        print("Error when unpacking names and tickets.")
        return pd.DataFrame()
    names = [n.strip() for n in names.splitlines() if n.strip() and n.strip() not in
             ['Leader', 'Officer', 'Member', 'Memher', 'PENDING INVITES', 'ALL', 'MY GUILD', "RAID TICKETS (DAILY)",
              "RAID TICKETS (LIFETIME)", "RAID TICKETS (LIFETIME) e", 'Lifetime Raid', 'Litetime Raid',
              'Daily Raid Tickets', 'Produced:', 'ua11Y Hald llCKets']
             and not represents_int(n.strip())]
    temp = tickets.splitlines()
    tickets = []
    for i in range(len(temp)):
        tickets.append(temp[i])
        if i + 1 < len(temp) and temp[i] in ['Produced: '] and temp[i + 1] in ['Daily Raid Tickets ']:
            tickets.append('0')
    tickets = [t for t in tickets if represents_int(t)]
    if len(names) > len(tickets):
        names = names[:-1]
    elif len(names) < len(tickets):
        tickets = tickets[1:]
    if len(names) > len(tickets):
        tickets = tickets + ['0']
    try:
        result = pd.DataFrame(tickets, index=names, columns=['Tickets'])
    except Exception as e:
        print("Error when trying to create the DataFrame: \n{}.".format(e))
        return pd.DataFrame()
    return result


def get_available_ticket_dates(author):
    keys = r.keys('{}:*'.format(author))
    keys = [l.decode('utf-8').split(':')[-1] for l in keys if 'lastdate' not in l.decode('utf-8')]
    return keys


def register_guild_leader(author):
    r.sadd('guild_leaders', author)


def is_registered_guild_leader(author):
    gls = r.smembers('guild_leaders')
    for g in gls:
        if g.decode('utf-8') == author:
            return True
    return False
