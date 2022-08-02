from neuclease.dvid import *

# Commit root node
post_commit('http://emdata6.int.janelia.org:8900', 'cc036e', 'Ingested supervoxels')

# Create a child of the root
post_newversion('http://emdata6.int.janelia.org:8900', 'cc036e', 'Ingesting agglomeration')
