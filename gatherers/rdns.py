import json
import logging
import re

from scanners import utils

# Reverse DNS
#
# Given a path to a (local) "JSON Lines" formatted file,
# based on Rapid7's Reverse DNS data, pull out the domains
# that match the given suffixes.
#
# Bearing in mind that the gathering system currently loads
# all domains into memory in order to dedupe them, it may be
# easiest to use this on a file that has been pre-filtered in
# some way (such as by grepping for the intended suffix).

# Best-effort filter for hostnames which are just reflected IPs.
# IP addresses often use dots or dashes.
# Some also start with "u-" before the IP address.
ip_filter = re.compile("^(\w+[\-\.]?)?\d+[\-\.]\d+[\-\.]\d+[\-\.]\d+")

# Best-effort filter for hostnames with just numbers on the base domain.
# (Note: this won't work for fed.us subdomains, but that's okay, this
# is just a best-effort to cut down noise.)
number_filter = re.compile("^[\d\-]+\.")

def gather(suffixes, options, extra={}):
    path = options.get("rdns")

    if path is None:
        logging.warn("--rdns is required to be a path to a local file.")
        exit(1)

    # May become useful to allow URLs in future.
    if path.startswith("http:") or path.startswith("https:"):
        logging.warn("--rdns is required to be a path to a local file.")
        exit(1)

    with open(path) as lines:
        logging.debug("\tReading %s..." % path)

        for line in lines:
            record = json.loads(line)
            # logging.debug("\t%s" % record["value"])

            # Filter out IP-like reflected addresses.
            is_ip = (ip_filter.search(record["value"]) is not None)

            # Check if it's just something like '1234.what.ever.gov'
            is_number = (number_filter.search(record["value"]) is not None)

            if (not is_ip) and (not is_number):
                yield record["value"]
