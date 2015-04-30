#!/bin/sh

SIZE=${1:-200}

curl -k -o eye-hair_${SIZE}.json -XGET 'https://darpamemex:darpamemex@esc.memexproxy.com/dig-latest/_search' -d '{"fields": ["hasBodyPart.text.english"], 
  "query": {
    "function_score" : {
      "query": {"simple_query_string": {"query": "eye~ blue green brown hazel hair blond~ brunette chestnut ginger",
                                        "default_operator": "OR"}},
      "random_score" : {}
    }
}, "size": 200 }'
