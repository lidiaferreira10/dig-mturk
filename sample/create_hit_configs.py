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

"""Typical usage:
python create_hit_configs.py -f pyfmt/embed/hitdata.pyfmt feature/embed/embed.json

most common arguments:
-f/--format: pyfmt file
-j/--experiment: experiment name (default auto-generated)
-w/--write: write output
-c/--cloud: write to S3
-p/--pretokenize: write all tokens to file

less common arguments:
-k/--hitcount: number of hits to create (default 10)
-l/--hitsize: number of sentences per hit (default 10)
-t/--tokencount: number of tokens per sentence (default 60) can be a posint or "None"
-s/--skip: skip specified number of sentences.  useful to generate non-overlapping sets from same esjson
-x/--check: filter function(s); can supply multiple times

rare arguments:
-e/--field: elastic search path (default hasBodyPart.text.english)
-g/--generator: iterator to generate tokens from text content

utility arguments:
-h/--help: help
-v/--verbose: verbose debug output
"""

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
import hashlib
import base64

import boto
BUCKETNAME = 'aisoftwareresearch'
PROFILE_NAME = 'aisoftwareresearch'
ZONENAME='s3-us-west-2.amazonaws.com'

import StringIO
import cgi
import tempfile

import util
from util import echo, ensureDirectoriesExist

def verb(f, *args):
    print >> sys.stderr, f % tuple(args)

### argparse/main argument validation and canonicalization

def isValidFileArg(parser, arg):
    """ensure arg (string) is an existing, readable input file"""
    if not os.path.exists(arg):
        parser.error("The file %s does not exist!" % arg)
    else:
        # return open(arg, 'r')  # return an open file handle
        return arg

def intOrNone(parser, arg):
    if arg==None:
        return arg
    elif arg=="None":
        return None
    else:
        try:
            return int(arg)
        except:
            parser.error("Neither None nor a valid int: %r" % arg)

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
GENERATOR="genescaped"

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
MATCHER="truth"

### CHECK functions
### given an ad content string, ensure it is appropriate for turker annotation
### return false value (conventionally, None) if check passes
### return an error indicator if fails
### TODO: signal exception rather than use error indicator

def _longEnough(s, minimum=50):
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

def longEnough(minimum):
    return lambda s: _longEnough(s, minimum=int(minimum))

def _onlySlightlyUnicode(s, threshold=0.20):
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

def onlySlightlyUnicode(threshold):
    return lambda s: _onlySlightlyUnicode(s, threshold=float(threshold))

def _shortEnough(s, maximum=1000):
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

def shortEnough(maximum):
    return lambda s: _shortEnough(s, maximum=int(maximum))

# default CHECK function
def standardCheck(s):
    # negative polarity, returns first failure case
    return _longEnough(s) or _onlySlightlyUnicode(s) or _shortEnough(s)
CHECK=["standardCheck"]
# new CHECK function
def asciiCheck(s):
    # negative polarity, returns first failure case
    return _longEnough(s) or _onlySlightlyUnicode(s, threshold=0.0) or _shortEnough(s)
CHECK=["asciiCheck"]
### Used to insert selected sentences into JSON template
def renderSentenceJson(experiment, sentenceRecords):
    """SENTENCERECORDS is a sequence of dicts, each one detailing a sentence for annotation.  Extract and format as JSON the relevant information for MTurk"""
    sentences = []
    for d in sentenceRecords:
        sentences.append({"id": d["id"],
                          "sentence": " ".join(d["tokens"]),
                          # simple encoding mechanism: tab-separated unicodes, base64 encoded
                          "tokens": base64.b64encode(u"\t".join([unicode(tok) for tok in d["tokens"]]).encode('UTF-8'))
                          })
    return json.dumps(sentences, indent=4)

TOKENCOUNT=60

### Used to select (potentially multiple) fragments from a single ad content text token list
def generateFragmentContexts(words, behind, ahead, matcher=MATCHER, tokencount=None):
    """With BEHIND, AHEAD, MATCHER: Can be used to generate multiple contexts within a single document;
Without BEHIND, AHEAD, MATCHER: just yield the input as one sentence context """
    if ahead and behind:
        # multiple matches
        for (word, i) in itertools.izip(words, itertools.count()):
            if matcher(word):
                # we found it
                start = max(i-behind, 0)
                end = min(i+ahead, len(words))
                yield (start, end)
    elif tokencount:
        # generate non-overlapping subsequences of length TOKENCOUNT
        # """yield (0,n), (n,2n), (nk,nk+n)... for all indices of nk+n <=len(iterable)"""
        l = len(words)
        for start in xrange(0, l, tokencount):
            end = start+tokencount
            if end < l:
                yield (start, end)
    elif len(words)>0 and matcher(words[0]):
        # single match of whole thing
        yield (0, len(words))
    else:
        # TODO: raise?
        return

BEGIN_COMMENT = """<!-- ##begin## -->"""
END_COMMENT = """<!-- ##end## -->"""

SKIP=None
HITCOUNT=10
HITSIZE=10

class ExitLoop(Exception):
    pass

seen = {}
def create_hit_configs(elsjson,
                       experiment=None, format=None, instructions=None, 
                       hitsize=HITSIZE, hitcount=HITCOUNT, 
                       generator=GENERATOR,
                       matcher=MATCHER,
                       check=CHECK,
                       tokencount=TOKENCOUNT,
                       write=False, cloud=False,
                       pretokenize=False,
                       field="hasBodyPart.text", 
                       seen=seen, skip=SKIP, 
                       verbose=False):

    # instantiate functions for all functional arguments
    generator, generatorName = interpretFnSpec(generator)
    interpretedChecks = []
    for c in check:
        cfn, cfnName = interpretFnSpec(c)
        interpretedChecks.append(cfn)
    check = interpretedChecks
    matcher, matcherName = interpretFnSpec(matcher)
    # verify format/instructions inputs
    if format:
        with open(format, 'r') as f:
            format = f.read()
    else:
        raise ValueError("-f/--format missing")
    if instructions:
        with open(instructions, 'r') as f:
            instructions = f.read()
            p1 = instructions.index(BEGIN_COMMENT)
            p2 = instructions.index(END_COMMENT)+len(END_COMMENT)
            instructions = json.dumps(instructions[p1:p2])
    else:
        print >> sys.stderr, "No instructions page.html file found"
        instructions = ""
    if not experiment:
        experiment = str(uuid.uuid4())

    with open(elsjson, 'r') as f:
        input = json.load(f)
    ehits = input["hits"]["hits"]

    def publish_hit(experiment, hitIndex, records):
        print >> sys.stderr, "PH"
        outpath = 'config/%s__%04d.json' % (experiment, hitIndex)
        if write:
            data = renderSentenceJson(experiment, records)
            sio = StringIO.StringIO()
            sio.write(format.format(sentences=data,instructions=instructions))
            jdata = sio.getvalue()
            # only for verbose do we dump the intermediate (post-substitution) JSON to tmp file
            if verbose:
                jfile = os.path.join(tempfile.gettempdir(), "jdata__%s__%04d.json" % (experiment, hitIndex))
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
                if verbose:
                    print >> sys.stderr, "writing to cloud bucket %s" % keyName
                k = b.new_key(keyName)
                k.set_contents_from_string(jdata)
                k.set_canned_acl('public-read')
                return "https://%s/%s/%s" % (ZONENAME, BUCKETNAME, expName)
            else:
                outfile = os.path.join(tempfile.gettempdir(), outpath)
                print >> sys.stderr, "Write to %s" % outfile
                ensureDirectoriesExist(outfile)
                with open(outfile, 'w') as f:
                    f.write(jdata)
                return outpath
        else:
            print >> sys.stderr, "Would write hit %s with %s sentences" % (outpath, len(records))
            return records

    def applyChecks(payload, checks):
        for check in checks:
            problem = check(payload)
            if problem:
                return problem

    # we want to generate HITCOUNT output (hit) files each with HITSIZE sentences

    def nested(hitcount, hitsize, skip):
        hitNum = 0
        hitRecords = []
        try:
            while ehits:
                ehit = ehits.pop(0)
                # work on this ehit
                docId = ehit["_id"]
                docIndex = ehit["_index"]
                fields = ehit.get("fields")
                if verbose:
                    print >> sys.stderr, "Ehit: %r" % (ehit)
                payloads = fields and fields.get(field, [])
                if payloads:
                    if verbose:
                        print >> sys.stderr, "Payloads for field %r: %r" % (field, len(payloads))
                    for payload in ehit["fields"][field]:
                        if seen.get(payload, False):
                            # already seen this one
                            continue
                        seen[payload] = True
                        problem = applyChecks(payload, check)
                        if problem:
                            if verbose:
                                print >> sys.stderr, "Broken/rejected row [%s] %r" % (problem, ehit)                  
                            continue
                        if verbose:
                            print >> sys.stderr, "Processing %s" % docId
                        # we are interested in this instance
                        words = [word for word in generator(payload)]
                        # all matches or just one match:
                        for (start, end) in generateFragmentContexts(words, None, None, matcher, tokencount=tokencount):
                            if skip:
                                skip -= 1
                                continue
                            else:
                                hashText = " ".join(words[start:end])
                                if seen.get(hashText, False):
                                    continue
                                seen[hashText] = True
                                verb("%s/%s hits, %s/%s hit records", hitNum, hitcount, 1+len(hitRecords), hitsize)
                                hashCode = hashlib.sha1(hashText.encode('utf-8')).hexdigest().upper()
                                hashUri = "http://dig.isi.edu/sentence/" + hashCode
                                hitRecords.append({"X-indexId": docId, 
                                                   "X-indexName": docIndex,
                                                   "X-field": field,
                                                   "X-generator": generatorName,
                                                   "X-reqWindowWidth": (end-start)+1,
                                                   "X-tokenStart": start,
                                                   "X-tokenEnd": end,
                                                   "X-elasticsearchJsonPathname": elsjson,
                                                   "id": hashUri,
                                                   "tokens": words[start:end]
                                                   })
                                if len(hitRecords)==hitsize:
                                    # publish
                                    publish_hit(experiment, hitNum, hitRecords)
                                    # prepare for next
                                    hitNum += 1
                                    hitRecords = []
                                    if hitNum==hitcount:
                                        raise ExitLoop
                                else:
                                    continue
                else:
                    if verbose:
                        print >> sys.stderr, "No payloads for ehit %r" % (ehit)

            if hitNum != hitcount:
                print >> sys.stderr, "Ran out of ES data"

        except ExitLoop as e:
            pass

    nested(hitcount, hitsize, skip)

def main(argv=None):
    '''this is called if run from command line'''
    parser = argparse.ArgumentParser()
    parser.add_argument("elsjson", help='input json file', type=lambda x: isValidFileArg(parser, x))
    parser.add_argument('-j','--experiment', required=False, help='experiment name; if not supplied, generate random UUID4', 
                        type=str, default=None)
    parser.add_argument('-f','--format', required=True, help='format template file: must exist', 
                        type=lambda x: isValidFileArg(parser, x))
    parser.add_argument('-k','--hitcount', required=False, help='number of hits to generate',
                        type=int, default=HITCOUNT)
    parser.add_argument('-l','--hitsize', required=False, help='number of sentences per hit',
                        type=int, default=HITSIZE)
    parser.add_argument('-t','--tokencount', required=False, help='number of tokens per sentence',
                        default=TOKENCOUNT,
                        type=lambda x: intOrNone(parser, x))
    parser.add_argument('-w','--write', required=False, action='store_true', help='write hit files')
    parser.add_argument('-c','--cloud', required=False, action='store_true', help='write destination is S3; ignored unless -w/--write supplied')
    parser.add_argument('-p','--pretokenize', required=False, action='store_true', help='include tokens in file')
    parser.add_argument('-x','--check', help='filter function(s)', required=False, default=[], action='append')

    parser.add_argument('-e','--field', required=False, help='elasticsearch path expression to extract content string',
                        type=str, default="hasBodyPart.text.english")

    parser.add_argument('-g','--generator', required=False, default=GENERATOR, type=str)
    parser.add_argument('-s','--skip', required=False, help='skip', type=int, default=SKIP)
    parser.add_argument('-v','--verbose', required=False, help='verbose', action='store_true')
    args=parser.parse_args()

    elsjson = args.elsjson
    generator = args.generator
    hitcount = args.hitcount
    hitsize = args.hitsize
    tokencount = args.tokencount
    write = args.write
    format = args.format
    (dirpath, _) = os.path.split(format)
    instructions = os.path.join(dirpath, 'page.html')
    experiment = args.experiment
    cloud = args.cloud
    pretokenize = args.pretokenize
    field = args.field
    check = args.check or CHECK
    skip = None if args.skip==0 else args.skip
    verbose = args.verbose
    s = create_hit_configs(elsjson, experiment=experiment, 
                           hitsize=hitsize, hitcount=hitcount, tokencount=tokencount,
                           write=write, cloud=cloud, 
                           pretokenize=pretokenize,
                           format=format, instructions=instructions,
                           field=field, generator=generator, check=check, skip=skip, 
                           verbose=verbose)
    if s:
        print s

# call main() if this is run as standalone
if __name__ == "__main__":
    sys.exit(main())
