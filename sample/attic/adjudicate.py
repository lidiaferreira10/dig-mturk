#!/usr/bin/python

# 7 May 2015

"""Typical usage:
python adjudicate.py dummy.json

utility arguments:
-h/--help: help
-v/--verbose: verbose debug output
"""

import sys, os
try:
    import simplejson as json
except:
    import json

import argparse
import io
from collections import defaultdict
import copy
import pprint

import util
from util import echo, canonList

def outpath(inpath):
    h,t = os.path.split(inpath)
    return os.path.join(h,"output_" + t)

class Adjudicator(object):
    def __init__(self, pathname, verbose=False):
        self.pathname = pathname
        self.verbose = verbose

    def ingest(self):
        with io.open(self.pathname, 'r', encoding='UTF-8') as f:
            self.inputJson = json.load(f)

    def acceptable(self, required, observed):
        # this is the adjudication threshold
        return observed >= 2

    def process(self):
        self.outputJson = []
        for inputSentence in self.inputJson:
            # for one sentence
            outputSentence = copy.copy(inputSentence)
            outputSentence["annotationSet"] = defaultdict(list)
            annotationSet = inputSentence["annotationSet"]
            # all annotations, regardless of user, indexed by the idxs
            byIdxs = defaultdict(list)
            for category, annotationValue in inputSentence["annotationSet"].iteritems():
                if category in [u'a', u'uri']:
                    continue
                # deal with singleton list issue
                for annotation in canonList(annotationValue):
                    entry = {}
                    idxs = annotation.get("annotatedTokenIdxs", None)
                    if idxs:
                        entry["start"] = idxs.split(',')[0]
                        entry["annotatedTokens"] = annotation["annotatedTokens"]
                        byIdxs[idxs].append(entry)
                    else:
                        print >> sys.stderr, "%s has no annotatedTokenIdxs" % annotation
                # Now we have all annotations for this category for this sentence, organized by idx
                # but we've lost the category?
                adjudicated = []
                for idxs,annotations in byIdxs.iteritems():
                    requiredCount = 3
                    observedCount = len(annotations)
                    if self.acceptable(requiredCount, observedCount):
                        adjudicated.extend(annotations)
                    else:
                        print >> sys.stderr, "Drop %s" % idxs
                # no adjudicated contains those passing the threshold
                if adjudicated:
                    outputSentence["annotationSet"][category] = adjudicated
                else:
                    # ignore this sentence
                    pass
            self.outputJson.append(outputSentence)


    def emit(self):
        with io.open(outpath(self.pathname), 'w', encoding='utf-8') as f:
            f.write(unicode(json.dumps(self.outputJson, ensure_ascii=False, indent=4)))

def main(argv=None):
    '''this is called if run from command line'''
    parser = argparse.ArgumentParser()
    parser.add_argument("inputJson", help='input json file')
    parser.add_argument('-v','--verbose', required=False, help='verbose', action='store_true')
    args=parser.parse_args()

    inputJson = args.inputJson
    verbose = args.verbose

    a = Adjudicator(inputJson, verbose=verbose)
    a.ingest()
    a.process()
    a.emit()

# call main() if this is run as standalone
if __name__ == "__main__":
    sys.exit(main())
