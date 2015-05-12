#!/usr/bin/python

import json
import random
import io

SEED=10

random.seed(SEED)

IN='eyehair_2000.json'
OUT='eyehair_1800.json'

with io.open(IF, 'r', encoding='UTF-8') as f:
    jdata = json.load(f)

random.shuffle(jdata["hits"]["hits"])

# get rid of the 100 or so we used in may101-110 and the 100 we used in may111
jdata["hits"]["hits"] = jdata["hits"]["hits"][100:]

# remove duplicates
seen = {}
keep = []
for hit in jdata["hits"]["hits"]:
    k = hit["fields"]["hasBodyPart.text.english"][0]
    if seen.get(k):
        pass
    else:
        seen.add(k)
        keep.append(hit)

jdata["hits"]["hits"] = keep

with open("randomsort__" + OUT, 'w') as f:
    json.dump(jdata, f)

