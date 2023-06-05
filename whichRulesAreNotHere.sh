#!/bin/bash

# which bv rewrite rules don't show up in regression tests?

REWRITES=../cvc5/src/theory/bv/rewrites
MKDSL_OUT=./rules/mkdsl-output.txt
ALL=./rules/all.txt
POSITIVE=./rules/positive.txt
NEGATIVE=./rules/negative.txt

python3 proof-rules.py rules -f $REWRITES > $ALL
#grep $MKDSL_OUT -e 'bv-' | sed -n 's/^.* \(.*\):.*$/\1/p' > $POSITIVE
grep $MKDSL_OUT -e 'bv-' | sed 's/,.*//' > $POSITIVE
grep -F -x -v -f $POSITIVE $ALL > $NEGATIVE
