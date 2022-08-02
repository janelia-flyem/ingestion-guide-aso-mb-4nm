#!/bin/bash

python convert-agglo-table.py

DVID_SERVER='http://emdata6.int.janelia.org:8900'
DVID_UUID=3324593350404bb8925259e9553a3594

AGGLO_MAPPING=agglo-mapping.npy
BLOCK_STATS=../ingest-supervoxels-20220802.144205/block-statistics.h5

#
# This loads both the mapping and the agglomerated body label indexes
#
ingest_label_indexes \
    --operation=both \
    --tombstones=include \
    --num-threads=16 \
    --batch-size=10_000 \
    --agglomeration-mapping=${AGGLO_MAPPING} \
    ${DVID_SERVER} \
    ${DVID_UUID} \
    segmentation \
    ${BLOCK_STATS} \
##
