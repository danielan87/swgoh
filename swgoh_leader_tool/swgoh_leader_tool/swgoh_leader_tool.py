import os
import json
import re
import pandas as pd
import datetime
import redis
import ocr_space_helper.ocr_space_helper as ocr_space_helper

OCR_API_KEY = '10aa254e3788957'
r = redis.StrictRedis(host='142.44.161.160', port=6379, db=0)


def represents_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def check_if_ticket_image(author, image_path, mode='local'):
    """
    Check if the given image is a "ticket" image. If it is, return True and save to database.
    :param author:
    :param image_path:
    :param mode:
    :return:
    """
    if mode == 'local':
        file = ocr_space_helper.ocr_space_file(filename=image_path, api_key=OCR_API_KEY)
    else:
        file = ocr_space_helper.ocr_space_url(image_path, api_key=OCR_API_KEY)
    text_content = json.loads(file)
    text_content = text_content['ParsedResults'][0]['ParsedText']
    if 'RAID TICKETS (' in text_content:
        print("{} is a 'ticket' image! Saving to database.".format(image_path))
        now = datetime.datetime.now()
        r.sadd("{}:ticket:{}".format(author, now.strftime('%Y%m%d')), text_content)
        r.expire("{}:ticket:{}".format(author, now.strftime('%Y%m%d')), 2592000)
        r.set("{}:ticket:lastdate".format(author), now.strftime('%Y%m%d'))
        r.expire("{}:ticket:lastdate".format(author), 2592000)
        return True
    return False


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
              "RAID TICKETS (LIFETIME)", 'Lifetime Raid', 'Litetime Raid', 'Daily Raid Tickets', 'Produced:',
              'ua11Y Hald llCKets']
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
