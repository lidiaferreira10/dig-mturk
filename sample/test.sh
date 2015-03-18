#!/bin/sh

# python window.py -l 1 -r 0 -w -f pyfmt/multicategory2/hitdata.pyfmt -j multicategory2_12 feature/multicategory/multicategory.json

# python window.py -l 10 -r 0 -w -f pyfmt/multicategory/hitdata.pyfmt -j multicategory13 feature/multicategory/multicategory.json

# python window.py -l 3 -r 0 -w --ahead 0 --behind 0 --matcher truth --format pyfmt/multicategory/hitdata.pyfmt -j multicategory14 feature/multicategory/multicategory.json

python window.py --limit 100 -r 0 -w --ahead 0 --behind -1 --matcher truth --format pyfmt/multicategory/hitdata.pyfmt -j multicategory14 feature/multicategory/multicategory.json