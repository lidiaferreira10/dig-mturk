#!/usr/bin/python

import sys, os
import re
import argparse
import pprint
from HTMLParser import HTMLParser

from util import identity

class HTMLTokenizer(HTMLParser):

    def __init__(self):
        self.buffer = []
        # this works only for new-style class
        # super(HTMLShedder,self).__init__()
        HTMLParser.__init__(self)
    def reset(self):
        self.buffer = []
        HTMLParser.reset(self)
    def handle_data(self, data):
        if data:
            self.buffer.extend(re.findall(r"\w+|[^\w\s]", data, re.UNICODE))
    def handle_starttag(self, tag, attrs):
        self.buffer.append("<%s" % tag + "".join([''' %s="%s"''' % attr for attr in attrs]) + ">")
    def handle_endtag(self, tag):
        self.buffer.append("</%s>" % tag)
    def handle_startendtag(self, tag, attrs):
        self.buffer.append("<%s" % tag + "".join([''' %s="%s"''' % attr for attr in attrs]) + "/>")
    def handle_entityref(self, name):
        self.buffer.append("&%s;" % name)
    def handle_charref(self, name):
        if name[0].upper() in ['A', 'B', 'C', 'D', 'E', 'F']:
            self.buffer.append("&#x%s;" % name)
        else:
            self.buffer.append("&#%s;" % name)
    def handle_comment(data):
        pass
    def handle_decl(data):
        pass

#     def myidentity(self, token):
#         return token

#     def myescape(self, token):
#         print [self, token]
#         try:
#             token = str(token)
#             if token.startswith('<'):
#                 return self.escape(token)
#         except:
#             pass
#         return token

#     def mytokenize(self, document, myinterpret=myidentity):
#         tokenizer = HTMLTokenizer()
#         tokenizer.feed(document)
#         tokenized = tokenizer.buffer
#         tokenizer.close()
#         return [myinterpret(t) for t in tokenized]


DATA = ["this is regular text",
        "<br/>text with<br/>breaks",
        """<a href="bobo"><b>bold<i>bold, italic<tt>bold italic tt</tt>more bi</i>more bold</b>just text</a>and more text""",
        "&#123; &#xA4; &#xa4; &gt;"
        ]

def bucketize(x, bucketName='__HTMLMARKUP__'):
    try:
        if x[0] in '<':
            return bucketName
    except:
        pass
    return x

def tokenize(document, interpret=identity):
    tokenizer = HTMLTokenizer()
    tokenizer.feed(document)
    tokenized = tokenizer.buffer
    tokenizer.close()
    return [interpret(t) for t in tokenized]

def sample():
    """Reuses tokenizer"""
    output = []
    tokenizer = HTMLTokenizer()
    for doc in DATA:
        tokenizer.reset()
        tokenizer.feed(doc)
        tokenized = tokenizer.buffer
        tokenizer.close()
        output.append( (doc, tokenized) )
    return output

def main(argv=None):
    '''this is called if run from command line'''
    s = sample()
    pprint.pprint(s)

# call main() if this is run as standalone
if __name__ == "__main__":
    sys.exit(main())
