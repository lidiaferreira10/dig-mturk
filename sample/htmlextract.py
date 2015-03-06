
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

