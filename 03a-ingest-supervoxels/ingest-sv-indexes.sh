#!/bin/bash

##
## Use the ingest_label_indexes command-line utility (shipped with flyemflows)
## to load supervoxel label indexes into the root UUID of our DVID repo.
##

DVID_SERVER=emdata6.int.janelia.org:8900
DVID_UUID=cc036e

ingest_label_indexes \
    --operation=indexes \
    --num-threads=16 \
    --batch-size=10_000 \
    ${DVID_SERVER} \
    ${DVID_UUID} \
    segmentation \
    block-statistics.h5 \
##

