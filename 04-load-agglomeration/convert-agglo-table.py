import numpy as np
import pandas as pd

orig_lut = '/groups/aso/asolab/Z0419_25_Alpha3/data.zarr/volumes/processed/neuron_glia/mushroom_body/fragment_segment_lut.npy'

lut = np.load(orig_lut).T
mapping_df = pd.DataFrame(lut, columns=['segment_id', 'body_id'], dtype=np.uint64)

# Body 0 is reserved, so let's replace that with a different ID.
max_body = mapping_df['body_id'].max()
body_0_rows = mapping_df['body_id'] == 0
mapping_df.loc[body_0_rows, 'body_id'] = max_body + 1

np.save('agglo-mapping.npy', mapping_df.to_records(index=False))
