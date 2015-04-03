#!/bin/sh

curl -k -o multicategory_pilot.json -XGET 'https://darpamemex:darpamemex@esc.memexproxy.com/dig-ht-pilot-test03/_search' -d '{"fields": ["hasBodyPart.text.english"], "size": 200, "query": {"function_score" : {"query" : { "match_all": {} }, "random_score" : {}    }}}'