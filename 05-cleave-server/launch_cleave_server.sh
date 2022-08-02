#!/bin/bash

# Launch a cleave server for the Aso MB 4nm volume

#ACTIVATE=/groups/flyem/proj/cluster/miniforge/bin/activate
#source $ACTIVATE flyem

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

CLEAVE_PORT=5100
CLEAVE_TABLE=${SCRIPT_DIR}/aso-mb-4nm-cleave-edges.npy

DVID_SERVER=emdata6.int.janelia.org
DVID_PORT=8900
PRIMARY_UUID=aa71edf0017541c8b78b738503922578

echo "launching cleave server on http://$(uname -n):${CLEAVE_PORT}"

nohup neuclease_cleave_server \
  -p ${CLEAVE_PORT} \
  --log-dir ${SCRIPT_DIR}/logs \
  --merge-table ${CLEAVE_TABLE} \
  --primary-dvid-server ${DVID_SERVER}:${DVID_PORT} \
  --primary-uuid ${PRIMARY_UUID} \
  --primary-labelmap-instance segmentation \
  >> logs/nohup.out 2>&1 &
##
