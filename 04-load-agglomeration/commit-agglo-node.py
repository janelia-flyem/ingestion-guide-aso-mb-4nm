from neuclease.dvid import *

# Commit agglo node
post_commit('http://emdata6.int.janelia.org:8900', '3324593350404bb8925259e9553a3594', 'Ingested agglomeration mapping/indexes')

# Create a child of the agglo node
post_newversion('http://emdata6.int.janelia.org:8900', '3324593350404bb8925259e9553a3594', 'Open for proofreading')

