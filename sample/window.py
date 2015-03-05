#!/usr/bin/python

# 4 March 2015

import sys, os
try:
    import simplejson as json
except:
    import json

import random
import nltk
import itertools
import argparse
import pprint

import util

SEED = 20150304
random.seed(SEED)

def truth(*args):
    return True

from HTMLParser import HTMLParser

class HTMLTextExtractor(HTMLParser):

    def __init__(self):
        self.buffer = []
        # this works only for new-style class
        # super(HTMLShedder,self).__init__()
        HTMLParser.__init__(self)
    def handle_data(self, data):
        if data:
            self.buffer.append(data)
    # def handle_endtag(self,tag):
    #     if tag == "br" or tag in blockLevelElements:
    #         self.buffer.append(" ")
        
def extract_text(html):
    parser = HTMLTextExtractor()
    parser.feed(html)
    output = " ".join(parser.buffer)
    parser.close()
    return output

"""{
  "took": 136,
  "timed_out": false,
  "_shards": {
    "total": 40,
    "successful": 40,
    "failed": 0
  },
  "hits": {
    "total": 18340,
    "max_score": 4.5852017,
    "hits": [
      {
        "_index": "dig-ht-pilot-unfiltered",
        "_type": "WebPage",
        "_id": "http://dig.isi.edu/ht/data/page/252ED2CF70811CF450EDFF7D87E9434E1AF30427/1402532895000/processed",
        "_score": 4.5852017,
        "fields": {
          "hasBodyPart.text": [
            "Blue eye Barbie - 20"
          ]
        }
      },"""

def genwords(text):
    for sentence in nltk.sent_tokenize(text):
        for tok in nltk.word_tokenize(sentence):
            yield tok

def containsEye(w):
    try:
        i = w.lower().index("eye")
        return True
    except:
        return False

def contains(t):
    def inner(s):
        try:
            i = s.lower().index(t)
            return True
        except:
            return False
    return inner

def sample(elsjson, ratio=0.9, matcher=containsEye, textConditioner=None, generator=genwords, ahead=5, behind=5, limit=5):
    output = []
    with open(elsjson, 'r') as f:
        input = json.load(f)
    for hit in input["hits"]["hits"]:
        for payload in hit["fields"]["hasBodyPart.text"]:
            payload = textConditioner(payload) if textConditioner else payload
            if random.random() > ratio:
                # we are interested in this instance
                words = [word for word in generator(payload)]
                for (word, i) in itertools.izip(words, itertools.count()):
                    if matcher(word):
                        # we found it
                        start = max(i-behind, 0)
                        end = min(i+ahead, len(words))
                        output.append(words[start:end])
                        if limit:
                            limit -= 1
                            if limit <= 0:
                                return output
    return output

from util import echo

def is_valid_file(parser, arg):
    if not os.path.exists(arg):
        parser.error("The file %s does not exist!" % arg)
    else:
        # return open(arg, 'r')  # return an open file handle
        return arg

AHEAD=5
BEHIND=5
RATIO=0.5
MATCHER="containsEye"
def main(argv=None):
    '''this is called if run from command line'''
    parser = argparse.ArgumentParser()
    parser.add_argument("elsjson", help='input json file', type=lambda x: is_valid_file(parser, x))
    parser.add_argument('-r','--ratio', required=False, help='ratio of accepts', default=RATIO, type=float)
    parser.add_argument('-m','--matcher', required=False, default=MATCHER, type=str)
    parser.add_argument('-t','--textConditioner', required=False, default=None, type=str)
    parser.add_argument('-a','--ahead','--after', required=False, default=AHEAD, type=int)
    parser.add_argument('-b','--behind','--before', required=False, default=BEHIND, type=int)
    parser.add_argument('-l','--limit', required=False, default=None, type=int)
    args=parser.parse_args()

    elsjson = args.elsjson
    ratio = args.ratio
    matcher = globals()[args.matcher]
    textConditioner = globals()[args.textConditioner] if args.textConditioner else None
    ahead = args.ahead
    behind = args.behind
    limit = args.limit
    s = sample(elsjson, ratio=ratio, matcher=matcher, textConditioner=textConditioner, ahead=ahead, behind=behind, limit=limit)
    pprint.pprint(s)

# call main() if this is run as standalone
if __name__ == "__main__":
    sys.exit(main())
