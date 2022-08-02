"""
This script loads the Aso MB agglomeration mapping and edge table
(from LSD/dacapo agglomeration) and exports the intra-body edges
in the format that can be used by a cleave server.
"""
import numpy as np
import pandas as pd

# Load agglo mapping (sv -> body)
mapping = pd.DataFrame(np.load(f'../04-load-agglomeration/agglo-mapping.npy'))
mapping = mapping.rename(columns={'segment_id': 'sv', 'body_id': 'body'})

# Load edges as DataFrame
print("Loading edges")
edge_columns = ['id_a', 'id_b', 'score', 'xa', 'ya', 'za', 'xb', 'yb', 'zb']
agglo_dir = '/groups/aso/asolab/Z0419_25_Alpha3/data.zarr/volumes/processed/neuron_glia/mushroom_body'
edges = np.load(f'{agglo_dir}/edges.npy')
edges = pd.DataFrame(edges, columns=edge_columns)

# Use the mapping to append columns for body_a and body_b
print("Populating columns: body_a,body_b")
edges = edges.merge(mapping.rename(columns={'sv': 'id_a', 'body': 'body_a'}), 'left', on='id_a')
edges = edges.merge(mapping.rename(columns={'sv': 'id_b', 'body': 'body_b'}), 'left', on='id_b')

edges['body_a'] = edges['body_a'].fillna(edges['id_a']).astype(np.uint64)
edges['body_b'] = edges['body_b'].fillna(edges['id_b']).astype(np.uint64)

# For the cleave table, we only need intra-body (internal)
# edges for every body, not inter-body edges.
print("Filtering for intra-body edges")
edges = edges.query('body_a == body_b')

# Convert to the precise layout needed by the cleave server.
# Note: cleave() expects scores to be "costs",
# i.e. lower means "merge", higher means "don't merge"
MERGE_TABLE_DTYPE = [('id_a', '<u8'),
                     ('id_b', '<u8'),
                     ('xa', '<u4'),
                     ('ya', '<u4'),
                     ('za', '<u4'),
                     ('xb', '<u4'),
                     ('yb', '<u4'),
                     ('zb', '<u4'),
                     ('score', '<f4')]

print("Converting dtypes")
cols = [k for k,v in MERGE_TABLE_DTYPE]
edges = edges.astype(dict(MERGE_TABLE_DTYPE))[cols]

output_path = 'aso-mb-4nm-cleave-edges.npy'
print(f"Exporting to {output_path}")
np.save(output_path, edges.to_records(index=False))

print("DONE")
