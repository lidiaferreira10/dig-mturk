#!/bin/sh

SIZE=${1:-10000}

curl -k -XGET 'https://darpamemex:darpamemex@esc.memexproxy.com/dig-latest/_search' -d '{"fields": ["hasBodyPart.text.english"], 
  "query": {
    "function_score" : {
      "query": {"simple_query_string": {"query": "eye~ blue green brown hazel hair blond~ brunette chestnut ginger redhead",
                                        "default_operator": "OR"}},
      "random_score" : {}
    }
}, "size": 10000 }' | jq "." > eyehair_${SIZE}.json 
