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
    return safeSeparatorCharacter.join(json.loads(base64.b64decode(encodedTokens)))

def mtExtractAnnotatedTokens(tokenIds, joinedTokens):
    """Beware of fencepost error here"""
    ids = [-1+int(i) for i in tokenIds.split(',') if (i and i>0)]
    tokens = joinedTokens.split(safeSeparatorCharacter)
    annotated = [tokens[i] for i in ids]
    return safeSeparatorCharacter.join(annotated)


def mtDecodeTokens2(encodedTokens):
    return json.loads("[1, 2]")

