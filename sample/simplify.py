#!/usr/bin/python

# 7 May 2015

"""Typical usage:
python simplify.py dummy.json

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
    return os.path.join(h,"simplified_output_" + t)

def dictToTuple(d):
    return tuple(sorted(d.items()))

def tupleToDict(t):
    dict(t)

def asLabeledIntTuple(s):
    label, ints = s
    return (label, [int(i) for i in ints.split('\t')])

class Simplifier(object):
    def __init__(self, pathname, verbose=False):
        self.pathname = pathname
        self.verbose = verbose

        # solely for statistics/reporting 
        self.totalLabelCount = 0
        self.usedLabelCount = {2: 0, 3: 0}
        self.droppedLabelCount = 0
        self.totalAnnotationCount = 0
        self.usedAnnotationCount = 0
        self.droppedAnnotationCount = 0

    def ingest(self):
        with io.open(self.pathname, 'r', encoding='UTF-8') as f:
            self.inputJson = json.load(f)

    def acceptable(self, possible, observed):
        # this is the adjudication threshold
        return observed >= 2

    def vprint(self, fmt, *args):
        if self.verbose:
            print >> sys.stderr, fmt  % tuple(args)

    def process(self):
        self.outputJson = []
        for inputSentence in self.inputJson:
            # for one sentence
            outputSentence = {}
            outputSentence["text"] = inputSentence["text"]
            outputSentence["uri"] = inputSentence["uri"]
            outputSentence["allTokens"] = inputSentence["allTokens"].split("\t")
            outputSentence["annotationSet"] = defaultdict(list)
            annotationSet = inputSentence["annotationSet"]
            # all annotations, regardless of user, indexed by the idxs
            byIdxs = defaultdict(list)
            for category, annotationValue in inputSentence["annotationSet"].iteritems():
                if category in [u'a', u'uri']:
                    continue
                self.vprint("  %s" % category)
                # deal with singleton list issue
                for annotation in canonList(annotationValue):
                    idxs = annotation.get("annotatedTokenIdxs", None)
                    self.vprint("xyzzy annotation %s" % idxs)
                    self.vprint("    Idxs %s", idxs)                        
                    if idxs:
                        start = int(idxs.split('\t')[0])
                        annotatedTokens = annotation["annotatedTokens"].split("\t")
                        byIdxs[(category, idxs)].append({"annotatedTokens": annotatedTokens, "start": start})
                        # pprint.pprint(byIdxs)
                    else:
                        print >> sys.stderr, "%s has no annotatedTokenIdxs" % annotation
            # Now we have all annotations for all categories for this sentence, organized by (category, idxs)


            adjudicated = {}
            for k in sorted(byIdxs.keys(), key=asLabeledIntTuple):
                self.totalLabelCount += 1
                entries = byIdxs[k]
                (category, idxs) = k
                # print "entries for %s are %s" % (idxs, entries)
                possibleCount = 3
                observedCount = len(entries)
                if self.acceptable(possibleCount, observedCount):
                    # add only one copy
                    self.vprint("    Keep %s %s: %s/%s", category, idxs, observedCount, possibleCount)
                    adjudicated[category] = entries[0]
                    self.totalAnnotationCount += observedCount
                    self.usedAnnotationCount += observedCount
                    self.usedLabelCount[observedCount] += 1
                else:
                    self.vprint("    Drop %s %s: %s/%s", category, idxs, observedCount, possibleCount)
                    self.totalAnnotationCount += observedCount
                    self.droppedLabelCount += 1
                    self.droppedAnnotationCount += observedCount
            # no adjudicated contains those passing the threshold
            for category,entry in adjudicated.iteritems():
                outputSentence["annotationSet"][category] = entry
            else:
                # ignore this sentence
                pass
            self.outputJson.append(outputSentence)

    def report(self):
        if self.verbose:
            print >> sys.stderr, "%d labels were seen, not including 'No Annotations'" % self.totalLabelCount
            print >> sys.stderr, "  %d were accepted at 3/3, %d accepted at 2/3. %d rejected" % (self.usedLabelCount[3], self.usedLabelCount[2], self.droppedLabelCount)
            print [self.totalAnnotationCount, self.usedAnnotationCount, self.droppedAnnotationCount]
            print [self.totalLabelCount, self.usedLabelCount, self.droppedLabelCount]


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

    a = Simplifier(inputJson, verbose=verbose)
    a.ingest()
    a.process()
    a.emit()
    a.report()

# call main() if this is run as standalone
if __name__ == "__main__":
    sys.exit(main())
