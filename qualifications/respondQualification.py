'''
Created on May 28, 2015

@author: Suba
'''
import sys
from boto.mturk.connection import MTurkConnection

conn = None
APPROVE_QUAL = 1
REJECT_QUAL = "The confirmation code was incorrect. Please try again"

def connectToMturk(mturkURL):
    global conn 
    conn = MTurkConnection(host=mturkURL)
    
def approveQualifications(qualID):
    if qualID == "null" or qualID == "None":
        qualID = ""
    qualifications =  conn.get_qualification_requests(qualID)
    for qual in qualifications:
        requestID = qual.QualificationRequestId
        confirmCode =  str(qual.answers[0][0].fields[0])
        if checkConfirmationCode(confirmCode):
            conn.grant_qualification(requestID,APPROVE_QUAL )
            
def checkConfirmationCode(code):
    try:
        return int(code) %97 == 1
    except:
        return False

def main():
    if len(sys.argv) == 3:
        env = sys.argv[1]
        mturkURL = ""
        if env == "-live":
            mturkURL = 'mechanicalturk.amazonaws.com'
        elif env == "-sandbox":
            mturkURL = 'mechanicalturk.sandbox.amazonaws.com'
        else:
            print "Incorrect environment name"
            sys.exit()
        qualID = sys.argv[2]
        connectToMturk(mturkURL)
        approveQualifications(qualID)
    else:
        print "Incorrect number of arguments. -env qualification_id. Qualifiication id can be set to null/None/"" to retrieve and verify all qualifications "
    
if __name__ == "__main__":
    sys.exit(main())