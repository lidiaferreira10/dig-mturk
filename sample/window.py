#!/usr/bin/python

# 4 March 2015

import sys, os
try:
    import simplejson as json
except:
    import json

import re
import random
import nltk
import itertools
import argparse
import pprint
from htmltoken import tokenize

import util
from util import echo

SEED = 20150304
random.seed(SEED)

def truth(*args):
    return True

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

def gentokens(text):
    for tok in tokenize(text):
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

def isValidFileArg(parser, arg):
    if not os.path.exists(arg):
        parser.error("The file %s does not exist!" % arg)
    else:
        # return open(arg, 'r')  # return an open file handle
        return arg

def toFn(expr):
    if re.match(r"""^[a-zA-Z0-9_]+$""", expr):
        # simple token: global function
        return globals()[expr]
    else:
        m = re.match(r"""^([a-zA-Z0-9_]+)\((.*)\)$""", expr)
        if m:
            return globals()[m.group(1)](m.group(2))
        else:
            raise ValueError("Bad function spec %s" % expr)

seen = {}

@echo
def windows(elsjson, ratio=0.9, matcher=containsEye, textConditioner=None, generator=genwords, ahead=5, behind=5, limit=5, seen=seen):
    output = []
    with open(elsjson, 'r') as f:
        input = json.load(f)
    for hit in input["hits"]["hits"]:
        docId = hit["_id"]
        for payload in hit["fields"]["hasBodyPart.text"]:
            if seen.get(payload, False):
                # already seen this one
                continue
            payload = textConditioner(payload) if textConditioner else payload
            print "=================================================================="
            print payload
            if random.random() > ratio:
                # we are interested in this instance
                words = [word for word in generator(payload)]
                for (word, i) in itertools.izip(words, itertools.count()):
                    if matcher(word):
                        # we found it
                        start = max(i-behind, 0)
                        end = min(i+ahead, len(words))
                        output.append([docId, words[start:end]])
                        if limit:
                            limit -= 1
                            if limit <= 0:
                                return output
    return output

AHEAD=5
BEHIND=5
RATIO=0.5
MATCHER="containsEye"
GENERATOR="genwords"

def main(argv=None):
    '''this is called if run from command line'''
    parser = argparse.ArgumentParser()
    parser.add_argument("elsjson", help='input json file', type=lambda x: isValidFileArg(parser, x))
    parser.add_argument('-r','--ratio', required=False, help='ratio of accepts', default=RATIO, type=float)
    parser.add_argument('-m','--matcher', required=False, default=MATCHER, type=str)
    parser.add_argument('-t','--textConditioner', required=False, default=None, type=str)
    parser.add_argument('-g','--generator', required=False, default=GENERATOR, type=str)
    parser.add_argument('-a','--ahead','--after', required=False, default=AHEAD, type=int)
    parser.add_argument('-b','--behind','--before', required=False, default=BEHIND, type=int)
    parser.add_argument('-l','--limit', required=False, default=None, type=int)
    args=parser.parse_args()

    elsjson = args.elsjson
    ratio = args.ratio
    # matcher = globals()[args.matcher]
    matcher = toFn(args.matcher)
    textConditioner = globals()[args.textConditioner] if args.textConditioner else None
    generator = globals()[args.generator]
    ahead = args.ahead
    behind = args.behind
    limit = args.limit
    print [elsjson, ratio, matcher, textConditioner, generator, ahead, behind, limit]
    s = windows(elsjson, ratio=ratio, matcher=matcher, textConditioner=textConditioner, generator=generator, ahead=ahead, behind=behind, limit=limit)
    pprint.pprint(s)

# call main() if this is run as standalone
if __name__ == "__main__":
    sys.exit(main())
