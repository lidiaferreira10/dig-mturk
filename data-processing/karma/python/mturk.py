import base64
import json

def mtSentenceUri(sentenceId):
    sid = sentenceId
    if sid=="emptyanswer":
        return ""
    elif sid.startswith("http"):
        return sid
    else:
        return "http://dig.isi.edu/sentence/" + sid

def mtAnnotationSetUri(sentenceUri):
    return sentenceUri+"/annotationset"

categoryToAnnotationClass = {"Person name": "personName",
                             "Ethnicity/Origin": "ethnicityOrigin",
                             "Hair type": "hairType",
                             "Eye color": "eyeColor",
                             "Company name": "companyName"}

def mtAnnotationClass(category):
    return categoryToAnnotationClass.get(category, "")

    
safeSeparatorCharacter = "\t"

def mtDecodeTokens(encodedTokens):
    # return safeSeparatorCharacter.join(json.loads(base64.b64decode(encodedTokens)))
    return base64.b64decode(encodedTokens)

def validTokenIdx(thing):
    "any inteeger >= 0; remove -1, empty strings"
    try:
        return int(thing)>=0
    except:
        pass
    return False

def mtExtractAnnotatedTokens(tokenIdxs, joinedTokens):
    idxs = [int(i) for i in tokenIdxs.split(',') if validTokenIdx(i)]
    tokens = joinedTokens.split(safeSeparatorCharacter)
    annotated = [tokens[i] for i in idxs]
    return safeSeparatorCharacter.join(annotated)

def mtExtractAnnotatedTokenIdxs(tokenIdxs):
    idxs = [i for i in tokenIdxs.split(',') if validTokenIdx(i)]
    return safeSeparatorCharacter.join(idxs)

