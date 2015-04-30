#!/bin/sh

SIZE=${1:-200}

curl -k -o eye-hair_${SIZE}.json -XGET 'https://darpamemex:darpamemex@esc.memexproxy.com/dig-latest/_search' -d '{"fields": ["hasBodyPart.text.english"], 
  "query": {
    "function_score" : {
      "query": {"simple_query_string": {"query": "eye~ OR blue~ OR brown~ OR green~ OR hazel~ OR amber~ OR gray~ OR grey~ OR hair~ OR black~ OR blonde~ OR red~ OR auburn~ OR chestnut~ OR silver~ OR ginger~ OR locks~ OR curls~ OR tresses~"}},
      "random_score" : {}
    }
}, "size": 200 }'


