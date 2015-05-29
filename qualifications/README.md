The python code pulls all qualification requests from amazon, verifies the confirmation code for each requests and approves the requests with correct codes.

arguments: -environmentName QualificationID
QualificationID can be set to None/null - it will pull all requests.
If set to a particular ID it will pull only requests pertaining to that ID.