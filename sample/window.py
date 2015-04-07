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
import hashlib
import uuid
from htmltoken import tokenize, bucketize

import boto
from boto.s3.key import Key
from boto.s3.connection import S3Connection
BUCKETNAME = 'aisoftwareresearch'
PROFILE_NAME = 'aisoftwareresearch'

import StringIO
import cgi

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

def genbucketized(text):
    for tok in tokenize(text, interpret=bucketize):
        yield tok

def genescaped(text):
    for tok in tokenize(text, interpret=cgi.escape):
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

def truth(t):
    return True

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

def interpretFnSpec(s):
    if isinstance(s, str):
        fnName = s
        fn = toFn(s)
    else:
        fnName = None
        fn = s
    return (fn, fnName)

"""categories      {{
        "label": "Person"
      }},
      {{
        "label": "Organization"
      }}
"""

"""sentences
      {{
        "id": "1",
        "sentence": "A \"Hello, world!\" program has become the traditional first program that many people learn."
      }}
"""

FORMAT = """=[
  {{
    "instructions_html": "{instructions_html}",
    "autoapproval": "",
    "assignment_duration": "",
    "hit_lifetime": "",
    "qualifications": [{qualifications}],
    "description": "{description}",
    "title": "{title}",
    "keywords": "{keywords}",
    "num_assignments": "",
    "reward": "",
    "hit_sentences": [{sentences}],
    "categories": [{categories}]
  }}
]"""

def generateSentencesJson(jobname, output):
    sentences = []
    for d in output:
        sentences.append({"id": d["id"],
                          "sentence": " ".join(d["tokens"])})
    return json.dumps(sentences)

### CHECK functions
### return false value (conventionally, None) if check passes
### return an error indicator if fails

def longEnough(s, minimum=50):
    try:
        if isinstance(s, (str, unicode)):
            l = len(s)
            if l>=minimum:
                return None
            else:
                return "longEnough: %s<%s" % (l, minimum)
    except:
        pass
    return "longEnough: general failure"

def onlySlightlyUnicode(s, threshold=0.20):
    try:
        if isinstance(s, (str, unicode)):
            l = len(s)
            k = sum([1 if ord(c) >= 256 else 0 for c in s])
            ratio = k/float(l)
            # print "%r / %r => %r" % (k, l, ratio)
            if l>0 and (ratio <= threshold):
                return None
            else:
                return "onlySlightlyUnicode: %r/%r > %r" % (k, l, threshold)
    except:
        pass
    return "onlySlightlyUnicode: general failure"

def standardCheck(s):
    # negative polarity, returns first failure case
    return longEnough(s) or onlySlightlyUnicode(s)

def intOrNone(thing):
    if thing==None or thing=='None':
        return None
    else:
        return int(thing)

AHEAD=None
BEHIND=None
RATIO=0.5
# MATCHER="containsEye"
MATCHER=lambda x: True
GENERATOR="genescaped"
TEXTCONDITIONER=None
CHECK=standardCheck
SKIP=None

def generateMatchContexts(words, behind, ahead, matcher):
    if ahead and behind:
        # multiple matches
        for (word, i) in itertools.izip(words, itertools.count()):
            if matcher(word):
                # we found it
                start = max(i-behind, 0)
                end = min(i+ahead, len(words))
                yield (start, end)
    elif len(words)>0 and matcher(words[0]):
        # single match of whole thing
        yield (0, len(words))
    else:
        return

seen = {}
def windows(elsjson, ratio=0.9, matcher=containsEye, textConditioner=None, generator=genescaped, ahead=5, behind=5, 
            limit=5, write=False, format=None, jobname=None,
            field="hasBodyPart.text", shuffle=None, seen=seen, cloud=False, check=CHECK, skip=SKIP, 
            verbose=False):

    matcher, matcherName = interpretFnSpec(matcher)
    textConditioner, textConditionerName = interpretFnSpec(textConditioner if textConditioner else None)
    generator, generatorName = interpretFnSpec(generator)
    check, checkName = interpretFnSpec(check)
    if format:
        with open(format, 'r') as f:
            format = f.read()
    if not jobname:
        jobname = str(uuid.uuid4())
    if shuffle==None:
        # unspecified, so default
        # pass shuffle=False if you are sure you want to turn if off
        shuffle = ratio>0

    output = []
    with open(elsjson, 'r') as f:
        input = json.load(f)
    ehits = input["hits"]["hits"]
    if shuffle:
        random.shuffle(ehits)
    uid = None

    def nested(limit):
        for ehit in ehits:
            docId = ehit["_id"]
            docIndex = ehit["_index"]
            fields = ehit.get("fields")
            if verbose:
                print >> sys.stderr, "Ehit: %r" % (ehit)
            payloads = fields and fields.get(field, [])
            if verbose:
                print >> sys.stderr, "Payloads for field %r: %r" % (field, payloads)
            problem = None
            if payloads:
                for payload in ehit["fields"][field]:
                    if seen.get(payload, False):
                        # already seen this one
                        continue
                    payload = textConditioner(payload) if textConditioner else payload
                    problem = check(payload)
                    if problem:
                        if verbose:
                            print >> sys.stderr, "broken/rejected row [%s] %r" % (problem, ehit)                  
                        continue
                    if random.random() > ratio:
                        if verbose:
                            print >> sys.stderr, "processing %s" % docId
                        # we are interested in this instance
                        words = [word for word in generator(payload)]
                        # all matches or just one match:
                        for (start, end) in generateMatchContexts(words, behind, ahead, matcher):
                            if skip:
                                skip -=1
                                if skip > 0:
                                    continue
                            output.append({"X-indexId": docId, 
                                           "X-indexName": docIndex,
                                           "X-field": field,
                                           "X-matchAnchor": matcherName,
                                           "X-textConditioner": textConditionerName,
                                           "X-generator": generatorName,
                                           "X-reqWindowWidth": (end-start)+1,
                                           "X-tokenStart": start,
                                           "X-tokenEnd": end,
                                           "X-elasticsearchJsonPathname": elsjson,
                                           "id": hashlib.sha1("%s-%s-%s" % (docId, start, end)).hexdigest(),
                                           "tokens": words[start:end]
                                           # "markup": " ".join(["<span>%s</span>" % word for word in words])
                                           })
                            if limit:
                                limit -= 1
                                if limit <= 0:
                                    return output
            else:
                if verbose:
                    print >> sys.stderr, "No payloads for ehit %r" % (ehit)

    nested(limit)
    if write:
        data = generateSentencesJson(jobname, output)
        outfile = 'config/%s.json' % jobname
        sio = StringIO.StringIO()
        sio.write(format.format(sentences=data))
        jdata = sio.getvalue()
        # Dump the intermediate (post-substitution) JSON
        if verbose:
            with open("/tmp/jdata.json", 'w') as f:
                print >> f, jdata
        # Validate the JSON
        try:
            json.loads(jdata)
        except Exception as e:
            print >> sys.stderr, "Invalid JSON [%r]" % e
        if cloud:
            c = boto.connect_s3(profile_name=PROFILE_NAME)
            b = c.get_bucket(BUCKETNAME)
            keyName = 'ner/%s/%s' % (jobname, outfile)
            k = b.new_key(keyName)
            k.set_contents_from_string(jdata)
            k.set_canned_acl('public-read')
            return "https://s3-us-west-2.amazonaws.com/aisoftwareresearch/%s" % keyName
        else:
            with open(outfile, 'w') as f:
                f.write(jdata)
            return outfile
    else:
        return output

def main(argv=None):
    '''this is called if run from command line'''
    parser = argparse.ArgumentParser()
    parser.add_argument("elsjson", help='input json file', type=lambda x: isValidFileArg(parser, x))
    parser.add_argument('-r','--ratio', required=False, help='ratio of accepts', default=RATIO, type=float)
    parser.add_argument('-m','--matcher', required=False, default=MATCHER, type=str)
    parser.add_argument('-t','--textConditioner', required=False, default=TEXTCONDITIONER, type=str)
    parser.add_argument('-g','--generator', required=False, default=GENERATOR, type=str)
    parser.add_argument('-a','--ahead','--after', required=False, default=AHEAD, type=intOrNone)
    parser.add_argument('-b','--behind','--before', required=False, default=BEHIND, type=intOrNone)
    parser.add_argument('-l','--limit', required=False, default=None, type=int)
    parser.add_argument('-w','--write', required=False, action='store_true')
    parser.add_argument('-f','--format', required=False, help='format template', type=lambda x: isValidFileArg(parser, x))
    parser.add_argument('-j','--jobname', required=False, help='jobname', type=str, default=None)
    parser.add_argument('-c','--cloud', required=False, help='cloud', action='store_true')
    parser.add_argument('-e','--field', required=False, help='field', type=str, default="hasBodyPart.text.english")
    parser.add_argument('-x','--check', required=False, help='check', type=str, default=CHECK)
    parser.add_argument('-s','--skip', required=False, help='skip', type=str, default=SKIP)
    parser.add_argument('-v','--verbose', required=False, help='verbose', action='store_true')
    args=parser.parse_args()

    elsjson = args.elsjson
    ratio = args.ratio
    matcher = args.matcher
    textConditioner = args.textConditioner if args.textConditioner else None
    generator = args.generator
    ahead = args.ahead
    behind = args.behind
    limit = args.limit
    write = args.write
    format = args.format
    jobname = args.jobname
    cloud = args.cloud
    field = args.field
    check = args.check
    skip = None if args.skip==0 else args.skip
    verbose = args.verbose
    s = windows(elsjson, ratio=ratio, matcher=matcher, textConditioner=textConditioner, generator=generator, 
                ahead=ahead, behind=behind, limit=limit, write=write, format=format, jobname=jobname, 
                cloud=cloud, field=field, check=check, skip=skip, verbose=verbose)

# call main() if this is run as standalone
if __name__ == "__main__":
    sys.exit(main())
