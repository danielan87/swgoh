import os
import json
import pytesseract
from PIL import Image

from ocr_space_helper.ocr_space_helper import *

OCR_API_KEY = '10aa254e3788957'

pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'

im = Image.open(os.path.join('static', 'img', 'screenshot1.jpg'))
im = im.crop((465, 180, 1130, 635))
im.save('temp.jpg')
print(pytesseract.image_to_string(im))
print(pytesseract.image_to_string(im))

test_file = ocr_space_file(filename='temp.jpg', api_key=OCR_API_KEY)
result = json.loads(test_file)
result = result['ParsedResults'][0]['ParsedText']
print(test_file)
