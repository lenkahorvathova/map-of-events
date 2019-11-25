import sys
import lxml
import time
import requests
from lxml import etree
import io
from urllib.parse import urljoin, unquote
from dateutil import parser as dparser
from bs4 import UnicodeDammit

types = set()
with open("types") as typesf:
    for line in typesf:
        t = line.strip()
        if t:
            types.add(t)

keywords_dict = dict()
keywords = set()
with open("keywords") as keywordsf:
    for line in keywordsf:
        l = line.strip()
        if '\t' in l:
            k, klemma = l.split('\t')
            keywords.add(klemma)
            keywords_dict[k] = klemma
        else:
            keywords.add(l)

def path_to_root(el):
    path = []
    while el is not el.getparent():
        s = el.tag
        classes = el.attrib.get('class', '').split()
        id = el.attrib.get('id', '')
        if classes:
            s += '.' + '.'.join(classes)
        if id:
            s += '#' + id
        path.append(s)
        el = el.getparent()
        if el is None: break
    return '/'.join(reversed(path))

def find_base(root):
    """
    Finds an element which has multiple children where each child has some repeating text.
    Returns a list of items in the form:
    XPATH1   V1_1   V1_2   V1_3
    XPATH2   V2_1   V2_2   V2_3
    Where Vx_y is a value found at XPATHx in y-th child.
    """

    for el in root.iter():
        d = {}
        for child in el.getchildren():
            if child.tag in d:
                d[child.tag] += 1
            else:
                d[child.tag] = 1
        if d:
            l = sorted([(y, x) for x, y in d.items()])
        else:
            continue
        if el.tag in ['ul', 'div', 'table', 'ol'] and l[0][0] > 1:
            id = el.attrib.get('id', '')
            if id.strip():
                id = '#' + id
            else:
                id = ''
            cl = el.attrib.get('class', '').split()
            if cl:
                cl = '.' + '.'.join(cl)
            else:
                cl = ''
            print(el.tag + cl + id)
            d2 = {}
            for subel in el.iter():
                if len(subel.getchildren()) == 0:
                    subel_path = path_to_root(subel)
                    if subel.text and subel.text.strip():
                        d2.setdefault(subel_path, []).append(subel.text.strip())
            for k in d2:
                print("\t", k)
                print("\t\t", d2[k])

def find_elements(base):
    # find elements containing individual actions
    return None

def element2data(element):
    # extract info about actions from element
    return None

def parse_date(s):
    repl = ["leden|01", "únor|02", "březen|03", "duben|04", "květen|05", "červenec|07", "červen|06", "srpen|08", "září|09", "říjen|10", "listopad|11", "prosinec|12"]
    for k in repl:
        a, b = k.split('|')
        s = s.replace(a, b)
    if ' - ' in s:
        od, do = s.split(' - ', 1)
    elif '&nbsp;-&nbsp;' in s:
        od, do = s.split('&nbsp;-&nbsp;')
    elif ' až ' in s:
        od, do = s.split(' až ', 1)
    elif '--' in s:
        od, do = s.split('--', 1)
    elif '–' in s:
        od, do = s.split('–', 1)
    else:
        print("unsplitable", s)
        od = s
        do = s
    try:
        odparse = dparser.parse(od)
        od = odparse.strftime('%Y-%m-%d %H:%M:%S') 
    except ValueError:
        pass
    try:
        doparse = dparser.parse(do)
        od = doparse.strftime('%Y-%m-%d %H:%M:%S') 
    except ValueError:
        pass
    return od, do

def location2gps(s):
    # desambiguate location
    return

def text2keywords(s):
    k = set()
    for token in s.lower().split(): # TODO: tokenizer
        if token in keywords:
            k.add(token)
        elif token in keywords_dict:
            k.add(keywords_dict[token])
    return k or set(["ostatní"])

def text2types(s):
    t = set()
    for token in s.lower().split(): # TODO: tokenizer
        if token in types:
            t.add(token)
    return t or set(["ostatní"])

def get_header():
    return {
        "Accept": "text/html",
        "User-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:21.0) Gecko/20100101 Firefox/21.0"
    }

def get_xpaths(fn):
    r = {}
    with open(fn) as f:
        for line in f:
            what, xpath = line.split(' ', 1)
            r[what] = xpath.strip()
    return r

def parse(url, conf=""):
    xpaths = get_xpaths("xpaths/" + conf)
    html = UnicodeDammit(requests.get(url, headers=get_header()).text, is_html=True).unicode_markup
    parser = etree.HTMLParser()
    root = etree.parse(io.StringIO(html), parser)
    base = root.xpath(xpaths["base"])[0]
    types_text = ""
    date_text = ""
    keywords_text = ""
    items = 0
    for el in base.xpath(xpaths["element"]):
        items += 1
        o = {}
        title_xpath = xpaths.get('title', None)
        if title_xpath:
            title_text = el.xpath(title_xpath)[0].strip()
            o["title"] = title_text
        else:
            o["title"] = ""
        date_xpath = xpaths.get('date', None)
        if date_xpath:
            date_text = el.xpath(date_xpath)
            if type(date_text) == type([]):
                o["beg"] = []
                o["end"] = []
                for item in date_text:
                    b, e = parse_date(item.strip('/').strip().replace('\u00A0', ' '))
                    o["beg"].append(b)
                    o["end"].append(e)
            else:
                date_text = date_text.strip().strip('/').replace('\u00A0', ' ')
                o["beg"], o["end"] = parse_date(date_text)
        else:
            o["beg"] = ""
            o["end"] = ""
        text_xpath = xpaths.get('text', None)
        if text_xpath:
            o["text"] = el.xpath(text_xpath)[0].strip()
        else:
            o["text"] = ""
        url_xpath = xpaths.get('url', None)
        if url_xpath:
            o["url"] = urljoin(url, unquote(el.xpath(url_xpath)[0].strip()))
        else:
            o["url"] = ""
        types_xpath = xpaths.get('types', None)
        if types_xpath:
            types_text = el.xpath(types_xpath)[0].strip()
            o["types"] = text2types(types_text + " " + o["title"] + ' ' + o["text"])
        else:
            o["types"] = set(["ostatní"])
        keywords_xpath = xpaths.get('keywords', None)
        if keywords_xpath:
            keywords_text = el.xpath(keywords_xpath)[0].strip()
            o["keywords"] = text2keywords(keywords_text + " " + o["title"] + ' ' + o["text"])
        else:
            o["keywords"] = set(["ostatní"])
        # TODO: GPS
        if type(o["beg"]) == type([]):
            for i in range(len(o["beg"])):
                for k in o:
                    if k in ["beg", "end"]:
                        print(k, o[k][i])
                    else:
                        print(k, o[k])
                print("---"*10)
        else:
            for k in o:
                print(k, o[k])
            print("==="*10)

if __name__ == "__main__":
    # script parser URL
    if len(sys.argv) < 2:
        print("process.py URL [PARSER]")
        exit(1)
    elif len(sys.argv) == 2:
        parse(sys.argv[1])
    else:
        parse(sys.argv[1], sys.argv[2])
