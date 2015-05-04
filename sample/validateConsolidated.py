#!/usr/bin/python

import csv
import io
import sys
from itertools import count, izip
import argparse


INPATH = "/Users/philpot/Downloads/consolidatedResult.tsv"

def outpath(inpath):
    return "validated_" + inpath

def validateConsolidate(consolidatedResult):
    with io.open(outpath(consolidatedResult), 'w', encoding='UTF-8') as outfile:
        with io.open(consolidatedResult, 'r', encoding='UTF-8') as infile:
            # rdr = csv.writer(infile, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
            rdr = csv.reader(infile, delimiter='\t')
            for (row, idx) in izip(rdr, count(0)):
                rowSize = None
                textSize = None
                e = None
                try:
                    rowSize = len(row)
                    textSize = len(row[7])
                except Exception as e:
                    pass
                print >> sys.stderr, "row %d size: %s, text size %s" % (idx, rowSize, textSize)
                if rowSize == 8:
                    # print >> outfile, u"\t".join([unicode(x) for x in row])
                    outfile.write(u"\t".join([unicode(x) for x in row]) + "\n")
                else:
                    print >> sys.stderr, "row %d discarded [%s]" % (idx, e)


def main(argv=None):
    '''this is called if run from command line'''
    parser = argparse.ArgumentParser()
    parser.add_argument('consolidatedResult', nargs='?', default=INPATH, help='input tsv file')

    args=parser.parse_args()
    consolidatedResult = args.consolidatedResult
    validateConsolidate(consolidatedResult)

# call main() if this is run as standalone
if __name__ == "__main__":
    sys.exit(main())
