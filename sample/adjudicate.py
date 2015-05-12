#!/usr/bin/python

# 7 May 2015

"""Typical usage:
python adjudicate.py dummy.json

utility arguments:
-h/--help: help
-v/--verbose: verbose debug output
-s/--summary: print summary
"""

import sys, os
try:
    import simplejson as json
except:
    import json

import argparse
import io
from collections import defaultdict, Counter
# import copy
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

class Adjudicator(object):
    def __init__(self, pathname, verbose=False, summary=False):
        self.pathname = pathname
        self.verbose = verbose
        self.summary = summary

        # solely for statistics/reporting 
        self.totalLabelCount = 0
        self.usedLabelCount = {2: 0, 3: 0}
        self.droppedLabelCount = Counter()
        self.totalAnnotationCount = 0
        self.usedAnnotationCount = 0
        self.droppedAnnotationCount = Counter()

    def ingest(self):
        with io.open(self.pathname, 'r', encoding='UTF-8') as f:
            self.inputJson = json.load(f)

    def acceptable(self, possible, observed):
        # this is the adjudication threshold
        return observed >= 2

    def vprint(self, fmt, *args):
        if self.verbose:
            print >> sys.stderr, fmt % tuple(args)

    def process(self):
        self.outputJson = []
        for inputSentence in self.inputJson:
            try:
                # for one sentence
                outputSentence = {}
                outputSentence["text"] = inputSentence["text"]
                outputSentence["uri"] = inputSentence["uri"]
                outputSentence["allTokens"] = inputSentence["allTokens"].split("\t")
                outputSentence["annotationSet"] = defaultdict(list)
                self.vprint("Sentence %s" % inputSentence["uri"])
                self.vprint("Text: %s" % inputSentence["text"])
                self.vprint("  Raw Annotations:")
                annotationSet = inputSentence["annotationSet"]
                # all annotations, regardless of user, indexed by the idxs
                byIdxs = defaultdict(list)
                for category, annotationValue in inputSentence["annotationSet"].iteritems():
                    if category in [u'a', u'uri']:
                        continue
                    self.vprint("  %s" % category)
                    # deal with singleton list issue
                    for annotation in canonList(annotationValue):
                        idxs = annotation.get("annotatedTokenIdxs", "")
                        workerId = annotation["worker"]["workerId"]
                        self.vprint("    %s: (%s) %s", workerId, annotation.get("annotatedTokens", "").replace('\t', ' '), idxs.replace('\t', ' '))
                        if idxs:
                            start = int(idxs.split('\t')[0])
                            annotatedTokens = annotation["annotatedTokens"].split("\t")
                            byIdxs[(category, idxs)].append({"annotatedTokens": annotatedTokens, "start": start})
                            # pprint.pprint(byIdxs)
                        else:
                            print >> sys.stderr, "ERROR: %s has no annotatedTokenIdxs" % annotation
                # Now we have all annotations for all categories for this sentence, organized by (category, idxs)

                self.vprint("  Adjudications:")
                adjudicated = defaultdict(list)
                for k in sorted(byIdxs.keys(), key=asLabeledIntTuple):
                    self.totalLabelCount += 1
                    entries = byIdxs[k]
                    (category, idxs) = k
                    # print "entries for %s are %s" % (idxs, entries)
                    possibleCount = 3
                    observedCount = len(entries)
                    if observedCount not in [1,2,3]:
                        raise ValueError("Unexpected count number %s of annotations for category %s, idxs %r" % (observedCount, category, idxs))
                    entry = entries[0]
                    if self.acceptable(possibleCount, observedCount):
                        # add only one copy
                        self.vprint("    KEEP @ %d/%d %s (%s) %s", observedCount, possibleCount, category, ' '.join(entry["annotatedTokens"]), idxs.replace('\t',' '))
                        adjudicated[category].append(entries[0])
                        self.totalAnnotationCount += observedCount
                        self.usedAnnotationCount += observedCount
                        self.usedLabelCount[observedCount] += 1
                    else:
                        self.vprint("    DROP @ %d/%d %s (%s) %s", observedCount, possibleCount, category, ' '.join(entry["annotatedTokens"]), idxs.replace('\t',' '))
                        self.totalAnnotationCount += observedCount
                        self.droppedLabelCount[workerId] += 1
                        self.droppedAnnotationCount[workerId] += observedCount
                # no adjudicated contains those passing the threshold
                for category,entries in adjudicated.iteritems():
                    outputSentence["annotationSet"][category].extend(entries)
                else:
                    # ignore this sentence
                    pass
                self.outputJson.append(outputSentence)
            except Exception as e:
                print >> sys.stderr, "Uncaught [%s] on input sentence [%r]" % (e, inputSentence)

    def report(self):
        if self.summary:
            print >> sys.stderr, "%d labels seen, not including 'No Annotations'" % self.totalLabelCount
            print >> sys.stderr, "  %d accepted (%d at 3/3, %d at 2/3)." % (sum(self.usedLabelCount.values()), self.usedLabelCount[3], self.usedLabelCount[2])
            print >> sys.stderr, "  %d rejected: " % (sum(self.droppedLabelCount.values())),
            print >> sys.stderr,  ",  ".join(['%s: %d' % (workerId, droppedCount) 
                                              for workerId,droppedCount
                                              in sorted(self.droppedLabelCount.iteritems())])
    def emit(self):
        with io.open(outpath(self.pathname), 'w', encoding='utf-8') as f:
            f.write(unicode(json.dumps(self.outputJson, ensure_ascii=False, indent=4)))

def main(argv=None):
    '''this is called if run from command line'''
    parser = argparse.ArgumentParser()
    parser.add_argument("inputJson", help='input json file')
    parser.add_argument('-v','--verbose', required=False, help='verbose', action='store_true')
    parser.add_argument('-s','--summary', required=False, help='print final summary to stederr', action='store_true')
    args=parser.parse_args()

    inputJson = args.inputJson
    verbose = args.verbose
    summary = args.summary

    a = Adjudicator(inputJson, verbose=verbose, summary=summary)
    a.ingest()
    a.process()
    a.emit()
    a.report()

# call main() if this is run as standalone
if __name__ == "__main__":
    sys.exit(main())
