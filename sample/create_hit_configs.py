#!/usr/bin/python

# 4 March 2015
# 10 April 2015

# Adapted from window.py
# drop many options
# drop ahead, behind
# drop textConditioner
# jobname becomes -j/--experiment
# drop ratio, shuffle, skip, SEED
# drop/stub matcher
# get rid of USEDOCID

import sys, os
try:
    import simplejson as json
except:
    import json

import re
import nltk
import itertools
import argparse
import uuid
from htmltoken import tokenize, bucketize

import boto
BUCKETNAME = 'aisoftwareresearch'
PROFILE_NAME = 'aisoftwareresearch'
ZONENAME='s3-us-west-2.amazonaws.com'

import StringIO
import cgi
import tempfile

import util
from util import echo, ensureDirectoriesExist

### argparse/main argument validation and canonicalization

def isValidFileArg(parser, arg):
    """ensure arg (string) is an existing, readable input file"""
    if not os.path.exists(arg):
        parser.error("The file %s does not exist!" % arg)
    else:
        # return open(arg, 'r')  # return an open file handle
        return arg

def toFn(expr):
    """Convert string expression like F into the global function F; F(abc) becomes the (presumably functional) value of F("abc") (note: quotes inputs)"""
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
    """Ensures s is either a function or a string representation of form which evaluates to function;
returns pair: function, function name"""
    if isinstance(s, str):
        fnName = s
        fn = toFn(s)
    else:
        fnName = None
        fn = s
    return (fn, fnName)


### Example of an elasticsearch query result

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

### GENERATOR functions
### given an ad content string, yield as series of strings

def genwords(text):
    """Rely on NLTK trained word and sentence tokenizers only"""
    for sentence in nltk.sent_tokenize(text):
        for tok in nltk.word_tokenize(sentence):
            yield tok

def gentokens(text):
    """All tokens in TEXT with no escaping/encoding"""
    for tok in tokenize(text):
        yield tok

def genbucketized(text):
    """All tokens in text, with all HTML tags mapped to a single bucket meta-token"""
    for tok in tokenize(text, interpret=bucketize):
        yield tok

# default GENERATOR function
def genescaped(text):
    """All tokens in TEXT with any odd characters (such as <>&) encoded using HTML escaping"""
    for tok in tokenize(text, interpret=cgi.escape):
        yield tok

### MATCHER functions
### given an ad content string, examine content (keywords, etc.) to decide whether or not to use it

def contains(t):
    """For use as MATCHER function template"""
    def inner(s):
        try:
            i = s.lower().index(t)
            return True
        except:
            return False
    return inner

def containsEye(w):
    """For use as MATCHER function"""
    try:
        i = w.lower().index("eye")
        return True
    except:
        return False

# default MATCHER function
def truth(*args):
    """Can be used as MATCHER function"""
    return True

### CHECK functions
### given an ad content string, ensure it is appropriate for turker annotation
### return false value (conventionally, None) if check passes
### return an error indicator if fails
### TODO: signal exception rather than use error indicator

def longEnough(s, minimum=50):
    """Reject string S if shorter than MININUM (default: 50) characters"""
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
    """Reject string S if THRESHOLD (default 20%) or more of characters are beyond 1st code page (i.e. not in latin-1)"""
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

def shortEnough(s, maximum=600):
    """Reject string S if longer than MAXIMUM (default: 600) characters"""
    try:
        if isinstance(s, (str, unicode)):
            l = len(s)
            if l<=maximum:
                return None
            else:
                return "shortEnough: %s<%s" % (l, maximum)
    except:
        pass
    return "shortEnough: general failure"

# default CHECK function
def standardCheck(s):
    # negative polarity, returns first failure case
    return longEnough(s) or onlySlightlyUnicode(s) or shortEnough(s)





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

def formatSentenceJson(experiment, output):
    sentences = []
    for d in output:
        sentences.append({"id": d["id"],
                          "sentence": " ".join(d["tokens"])})
    return json.dumps(sentences, indent=4)

MATCHER="truth"
GENERATOR="genescaped"
CHECK=standardCheck
SKIP=None

def generateMatchContexts(words, behind, ahead, matcher=MATCHER):
    """With BEHIND, AHEAD, MATCHER: Can be used to generate multiple contexts within a single document"""
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

BEGIN_COMMENT = """<!-- ##begin## -->"""
END_COMMENT = """<!-- ##end## -->"""

seen = {}
def create_hit_configs(elsjson,
                       limit=10, hitcount=10, write=False, format=None, instructions=None, experiment=None,
                       generator=GENERATOR,
                       matcher=MATCHER,
                       check=CHECK,
                       field="hasBodyPart.text", seen=seen, cloud=False, skip=SKIP, 
                       verbose=False):

    generator, generatorName = interpretFnSpec(generator)
    check, checkName = interpretFnSpec(check)
    matcher, matcherName = interpretFnSpec(matcher)
    if format:
        with open(format, 'r') as f:
            format = f.read()
    if instructions:
        with open(instructions, 'r') as f:
            instructions = f.read()
            p1 = instructions.index(BEGIN_COMMENT)
            p2 = instructions.index(END_COMMENT)+len(END_COMMENT)
            instructions = json.dumps(instructions[p1:p2])
    if not experiment:
        experiment = str(uuid.uuid4())

    output = []
    with open(elsjson, 'r') as f:
        input = json.load(f)
    ehits = input["hits"]["hits"]
    uid = None

    def publish_hit(experiment, hitCount, records):
        if write:
            data = formatSentenceJson(experiment, records)
            outpath = 'config/%s__%04d.json' % (experiment, hitCount)
            sio = StringIO.StringIO()
            sio.write(format.format(sentences=data,instructions=instructions))
            jdata = sio.getvalue()
            # Dump the intermediate (post-substitution) JSON
            if verbose:
                jfile = os.path.join(tempfile.gettempdir(), "jdata__%s__%04d.json" % (experiment, hitCount))
                with open(jfile, 'w') as f:
                    print >> f, jdata
            # Validate the JSON
            try:
                json.loads(jdata)
            except Exception as e:
                print >> sys.stderr, "Invalid JSON [%r]" % e
            if cloud:
                c = boto.connect_s3(profile_name=PROFILE_NAME)
                b = c.get_bucket(BUCKETNAME)
                expName = 'ner/%s' % (experiment)
                keyName = 'ner/%s/%s' % (experiment, outpath)
                k = b.new_key(keyName)
                k.set_contents_from_string(jdata)
                k.set_canned_acl('public-read')
                return "https://%s/%s/%s" % (ZONENAME, BUCKETNAME, expName)
            else:
                outfile = os.path.join(tempfile.gettempdir(), outpath)
                ensureDirectoriesExist(outfile)
                with open(outfile, 'w') as f:
                    f.write(jdata)
                return outpath
        else:
            print >> sys.stderr, "Would write %s %s with %s records" % (experiment, hitCount, len(records))
            return records


    # we want to generate HITCOUNT files
    # each with LIMIT

    def nested(hitcount, limit):
        hitNum = 0
        while hitNum < hitcount:
            output = []
            while len(output)<limit:
                ehit = ehits.pop(0)
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
                        problem = check(payload)
                        if problem:
                            if verbose:
                                print >> sys.stderr, "broken/rejected row [%s] %r" % (problem, ehit)                  
                            continue
                        if verbose:
                            print >> sys.stderr, "processing %s" % docId
                        # we are interested in this instance
                        words = [word for word in generator(payload)]
                        # all matches or just one match:
                        for (start, end) in generateMatchContexts(words, None, None, matcher):
                            output.append({"X-indexId": docId, 
                                           "X-indexName": docIndex,
                                           "X-field": field,
                                           "X-generator": generatorName,
                                           "X-reqWindowWidth": (end-start)+1,
                                           "X-tokenStart": start,
                                           "X-tokenEnd": end,
                                           "X-elasticsearchJsonPathname": elsjson,
                                           "id": docId,
                                           "tokens": words[start:end]
                                           })
                else:
                    if verbose:
                        print >> sys.stderr, "No payloads for ehit %r" % (ehit)
            # this hit is fully populated
            publish_hit(experiment, hitNum, output)
            output = []
            hitNum += 1
    nested(hitcount, limit)

def main(argv=None):
    '''this is called if run from command line'''
    parser = argparse.ArgumentParser()
    parser.add_argument("elsjson", help='input json file', type=lambda x: isValidFileArg(parser, x))
    parser.add_argument('-g','--generator', required=False, default=GENERATOR, type=str)
    parser.add_argument('-l','--limit', required=False, default=None, type=int)
    parser.add_argument('-k','--hitcount', required=False, default=None, type=int)
    parser.add_argument('-w','--write', required=False, action='store_true')
    parser.add_argument('-f','--format', required=False, help='format template', type=lambda x: isValidFileArg(parser, x))
    parser.add_argument('-j','--experiment', required=False, help='experiment', type=str, default=None)
    parser.add_argument('-c','--cloud', required=False, help='cloud', action='store_true')
    parser.add_argument('-e','--field', required=False, help='field', type=str, default="hasBodyPart.text.english")
    parser.add_argument('-x','--check', required=False, help='check', type=str, default=CHECK)
    parser.add_argument('-s','--skip', required=False, help='skip', type=int, default=SKIP)
    parser.add_argument('-v','--verbose', required=False, help='verbose', action='store_true')
    args=parser.parse_args()

    elsjson = args.elsjson
    generator = args.generator
    limit = args.limit
    hitcount = args.hitcount
    write = args.write
    format = args.format
    (dirpath, _) = os.path.split(format)
    instructions = os.path.join(dirpath, 'page.html')
    experiment = args.experiment
    cloud = args.cloud
    field = args.field
    check = args.check
    skip = None if args.skip==0 else args.skip
    verbose = args.verbose
    s = create_hit_configs(elsjson, experiment=experiment, generator=generator, 
                           write=write, cloud=cloud, 
                           format=format, instructions=instructions,
                           field=field, check=check, limit=limit, hitcount=hitcount, skip=skip, 
                           verbose=verbose)

# call main() if this is run as standalone
if __name__ == "__main__":
    sys.exit(main())
