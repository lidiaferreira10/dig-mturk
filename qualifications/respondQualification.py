'''
Created on May 28, 2015

@author: Suba
'''
import sys
from boto.mturk.connection import MTurkConnection
import argparse

APPROVE_QUAL = 1
REJECT_MSG = "The confirmation code was incorrect. Please try again"

def connectToMturk(mturkURL, access_key_id="", secret_access_key=""):
    conn = MTurkConnection(host=mturkURL, 
                           aws_access_key_id=access_key_id,
                           aws_secret_access_key=secret_access_key)
    return conn

def respondQualifications(conn, qualID, verbose=False):
    qualifications =  conn.get_qualification_requests(qualID)
    for qual in qualifications:
        requestID = qual.QualificationRequestId
        confirmCode =  str(qual.answers[0][0].fields[0])
        if checkConfirmationCode(confirmCode):
            if verbose:
                print >> sys.stderr, "Approving"
            conn.grant_qualification(requestID, APPROVE_QUAL)
        else:
            if verbose:
                print >> sys.stderr, "Rejecting"
            conn.reject_qualification(requestID, 0, REJECT_MSG)
            
def checkConfirmationCode(code):
    """We use mod 97 <insert the SO link>"""
    try:
        return int(code) %97 == 1
    except:
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-a','--access_key_id', required=True, help='aws_access_key_id')
    parser.add_argument('-s','--secret_access_key', required=True, help='aws_secret_access_key')
    parser.add_argument('-v','--verbose', required=False, help='verbose', action='store_true')
    parser.add_argument('--live', required=False, help='deploy to live MT', action='store_true')
    parser.add_argument('--sandbox', required=False, help='deploy to MT sandbox', action='store_true')
    parser.add_argument("qualid", help='qualification ID')
    args=parser.parse_args()

    if args.live:
        mturkURL = 'mechanicalturk.amazonaws.com'
    elif args.sandbox:
        mturkURL = 'mechanicalturk.sandbox.amazonaws.com'
    else:
        print >> sys.stderr, "Incorrect environment name"
        sys.exit()

    qualID = args.qualid
    if qualID == "null" or qualID == "None":
        qualID = ""

    conn = connectToMturk(mturkURL, access_key_id=args.access_key_id, secret_access_key=args.secret_access_key)
    respondQualifications(conn, qualID, verbose=args.verbose)
    
if __name__ == "__main__":
    sys.exit(main())
