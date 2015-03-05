#!/bin/sh

curl -s -k -u 'darpamemex:darpamemex' -o output.json -d @query.json -XGET 'https://esc.memexproxy.com/dig-ht-pilot-unfiltered/_search'
