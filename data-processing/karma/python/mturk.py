

def mtSentenceUri(sentenceId):
    sid = getValue("sentenceId")
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

    
