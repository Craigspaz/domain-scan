import logging
import requests
import re
import urllib.parse
from bs4 import BeautifulSoup

###
# Scanner to search for DAP.  It scrapes the front page and
# searches for the DAP js url and extracts parameters too.


# Set a default number of workers for a particular scan type.
# Overridden by a --workers flag. XXX not actually overridden?
workers = 50


# Required scan function. This is the meat of the scanner, where things
# that use the network or are otherwise expensive would go.
#
# Runs locally or in the cloud (Lambda).
def scan(domain: str, environment: dict, options: dict) -> dict:
    results = {}
    results["domain"] = domain
    results["dap_detected"] = False
    results['dap_traces'] = False
    results['dap_parameters'] = {}

    # Get the url
    try:
        response = requests.get("https://" + domain, timeout=5)
        results["status_code"] = response.status_code
    except Exception:
        logging.debug("got error while querying %s", domain)
        results["status_code"] = -1
        return results

    # check for DAP url
    res = re.findall(r'https://dap.digitalgov.gov/Universal-Federated-Analytics-Min.js', response.text)
    if res:
        results["dap_detected"] = True
        res = re.findall(r'"(https://dap.digitalgov.gov/Universal-Federated-Analytics-Min.js?.*?)"', response.text)
        for i in res:
            u = urllib.parse.urlparse(i)
            results['dap_parameters'] = urllib.parse.parse_qs(u.query)
    else:
        # search for DAP in included js
        soup = BeautifulSoup(response.text, features="lxml")
        scripts = soup.find_all('script')
        for s in scripts:
            if s.has_attr('src'):
                # slurp the js down and check for UA-33523145-1, which is supposedly an ID that
                # will never change.
                try:
                    if s['src'].startswith('http'):
                        jsurl = s['src']
                    else:
                        jsurl = 'https://' + domain + s['src']
                    jsresponse = requests.get(jsurl, timeout=5)
                    if re.findall(r'UA-33523145-1', jsresponse.text):
                        results["dap_detected"] = True
                        u = urllib.parse.urlparse(jsurl)
                        results['dap_parameters'] = urllib.parse.parse_qs(u.query)
                except Exception:
                    logging.debug("could not download", jsurl, 'for domain', domain)
        if results['dap_detected'] is not True:
            # check for things that look like analytics stuff
            # This is to try to handle the case like hud.gov, which currently
            # has a script that dynamically appends the nonstandard-named
            # locally hosted DAP js on the end of the file.  Ugh.
            fedanalytics = re.findall(r'Federated-Analytics', response.text)
            scriptid = re.findall(r'_fed_an_ua_tag', response.text)
            if fedanalytics and scriptid:
                # kinda pretty sure there's dap here
                results['dap_detected'] = True
                results['dap_traces'] = True
            elif fedanalytics or scriptid:
                # maybe?
                results['dap_traces'] = True

    logging.warning("DAP %s Complete!", domain)

    return results


# Required CSV row conversion function. Usually one row, can be more.
#
# Run locally.
def to_rows(data):
    row = []
    for i in headers:
        row.extend([data[i]])
    return [row]


# CSV headers for each row of data. Referenced locally.
headers = [
    "domain",
    "status_code",
    "dap_detected",
    "dap_parameters",
]
