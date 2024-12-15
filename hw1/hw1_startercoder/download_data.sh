#!/bin/bash

ROOT=https://data.commoncrawl.org/crawl-data/CC-MAIN-2018-17/segments/1524125937193.1/

# Note: the --no-clobber arg required curl 7.83. If it doesn't work for you,
# you can either update curl or remove that argument.

curl -o data.warc.gz --no-clobber ${ROOT}warc/CC-MAIN-20180420081400-20180420101400-00000.warc.gz
gunzip data.warc.gz

curl -o data.wet.gz --no-clobber ${ROOT}wet/CC-MAIN-20180420081400-20180420101400-00000.warc.wet.gz
gunzip data.wet.gz

curl -o data.wat.gz --no-clobber ${ROOT}wat/CC-MAIN-20180420081400-20180420101400-00000.warc.wat.gz
gunzip data.wat.gz