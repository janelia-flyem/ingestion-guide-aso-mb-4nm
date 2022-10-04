# Aso MB 4nm DVID setup

This repoository contains the scripts and configuration files that were used to prepare the Aso MB 4nm volume for proofreading in DVID.

## Contents

- [Overview](#overview)
  - [Inputs](#inputs)
  - [Outputs](#outputs)
- [Software Installation](#software-installation)
    - [DVID](#dvid)
    - [flyemflows](#flyemflows)

1. [DVID Configuration](#1-dvid-configuration)
2. [Grayscale Conversion](#2-grayscale-conversion)
3. [Supervoxel Ingestion](#3-supervoxel-ingestion)
    - [Copy voxels](#copy-voxels)
    - [Ingest label indexes](#ingest-label-indexes)
    - [Supervoxel Meshes](#supervoxel-meshes)
    - [Lock DVID UUID](#lock-root-dvid-uuid)
4. [Agglomeration Ingestion](#4-agglomeration-ingestion)
    - [Ingest mapping table and label indexes](#ingest-mapping-table-and-label-indexes)
    - [neuroglancer meshes](#neuroglancer-meshes)
    - [Lock DVID UUID](#lock-agglo-dvid-uuid)
5. [Cleave Server](#5-cleave-server)


## Overview

Our two main proofreading clients are NeuTu and neu3. (They're closely related and share a lot of code.)
Those clients obtain all image and proofreading data from a DVID server, so our first task is to load the segmentation and grayscale image volumes into a DVID database.  For the grayscale data, we can alternatively store the data in a static format, and configure DVID to serve as a proxy for data.

### Inputs

We assume you are starting with the following:

- Grayscale volume in a supported format (Zarr, N5, TIFF, PNG, HDF5, neuroglancer precomputed)
- Supervoxel Segmentation in a supported format
- Agglomeration mapping (sv ID -> agglomerated ID)
- Agglomeration affinities, at least for "internal" edges
  (edges between supervoxels which inhabit the same agglomerated bodies)

### Outputs

We'll process the inputs to construct the following components of our proofreading infrastructure.  Parts 1 and 2 involve large image volumes, so we use the compute cluster.  Parts 3 and 4 require only a single machine with sufficient RAM.

The scripts and configuration files for each of these steps can be found in this repository.

1. DVID server
2. Grayscale data
    - Loaded in DVID
    - Or copied as neuroglancer precomputed format, with DVID configured to proxy from that source
3. Supervoxel segmentation
    - Raw voxels loaded into the DVID database
    - supervoxel segment block statistics loaded into DVID as "label indexes"
    - Optional: supervoxel meshes
4. Agglomerated segmentation
    - agglomeration mapping (sv ID -> agglomerated ID) loaded into DVID
    - agglomerated segment block statistics loaded into DVID as "label indexes"
    - Optional: neuroglancer meshes
5. Cleave server
    - An independent server
    - Backed by a table of edge affinities
    - Configured to refer to our DVID server

## Software installation

### DVID

On Linux, there are three ways to install DVID:

- [download the release tarball with a self-contained executable](https://github.com/janelia-flyem/dvid/releases)
- Install via conda:
    ```bash
    conda create -n dvid -c flyem-forge -c conda-forge "dvid>=0.9.16"
    conda activate dvid
    ```
- Use a pre-built docker container.  The tarball method linked above contains no external dependencies, so there is little benefit to using a docker container unless you are integrating DVID into a docker swarm.
    - TODO: Link to our docker container

### flyemflows

The ingestion scripts rely on a custom-built package for running various data processing tasks on a compute cluster using dask.  Install it via conda:

```bash
conda create -n flyem -c flyem-forge -c conda-forge "flyemflows>=0.5.post.dev513"
conda activate flyem
```

## 1. DVID configuration

DVID relies on a single TOML file for configuration.  Copy `01-dvid/aso-mb-4nm.toml` from this repository to your server machine and edit it to configure the server port and storage directories. Then launch DVID:

```bash
cd /path/to/dvid/configs/
dvid aso-mb-4nm.toml
```

Using a new terminal window on the same machine, create a single repository on the server:

```bash
# Make sure this port matches the `rpcAddress` in your TOML file.
dvid -rpc=:8001 repos new aso-mb-4nm "Aso Mushroom Body Z0419_25_Alpha3"
```

## 2. Grayscale Conversion

We use `flyemflows` to convert the grayscale data from N5 to neuroglancer precomputed format.  For proofreading purposes, we find that JPEG compression offers good speed/quality tradeoff, so that's how we'll encode the data.

Copy the `02-export-grayscale` directory from this repository to our network file system.  Edit the file paths and dataset dimensions in `workflow.yaml`.  Also, pay special attention to the `store-type` for Zarr arrays:

- `store-type: DirectoryStore` - For "ordinary" zarr arrays with chunk names such as `15.7.20`
- `store-type: NestedDirectoryStore` - For zarr arrays whose chunks are stored in a directory hierarchy, e.g. `15/7/20`
- `store-type: N5Store` - For N5 volumes which we'll read via the `zarr` Python library

You may also wish to inspect `dask-config.yaml` to understand how each LSF node will be allocated for dask workers.  Pay attention to the `-P` setting which specifies who should be billed for the cluster job.

Then, from a cluster login node, submit the export job to the cluster, using the `launchflow` executable (from `flyemflows`):

```
conda activate flyem
bsub launchflow -n 32 02-export-grayscale
```

The job will not create any files in  your `02-export-grayscale` directory itself.  Instead, that directory is used as a template, and the actual "execution directory" will be a timestamped copy:

```
$ ls -d 02-export-grayscale*
02-export-grayscale
02-export-grayscale-20220707.112909
```

Monitor progress by inspecting the `output.log` within the execution directory.

Once the job is complete (~45 minutes), Create a google storage bucket to hold the data.  Then enable public access, with CORS permitted:

```
$ cat > cors.json << EOF
[{"maxAgeSeconds": 3600, "method": ["GET"], "origin": ["*"], "responseHeader": ["Content-Type", "Range"]}]
EOF

$ gsutil iam ch allUsers:objectViewer gs://aso-z0419_25_alpha3-jpeg
$ gsutil cors set cors.json gs://aso-z0419_25_alpha3-jpeg
```

Then upload the exported volume:

```bash
gsutil -m cp -r Z0419_25_Alpha3_jpeg/* gs://aso-z0419_25_alpha3-jpeg/
```

NeuTu/neu3 always reads from DVID, so we'll edit the DVID configuration to make DVID serve this grayscale data.  (Alternatively, we could have loaded the data directly into the DVID database itself.  That could have been achieved via different settings in `workflow.yaml`, above.)

To serve the precomputed grayscale data via DVID, edit the TOML file's `[store]` section:

```toml
[store]
    [store.aso-grayscale]
    engine = "ngprecomputed"
    ref = "aso-z0419_25_alpha3-jpeg"  # bucket name
    instance = "grayscale"            # instance name
```

And restart DVID:

```bash
dvid -rpc=:8001 shutdown
```

```bash
cd /path/to/dvid/configs/
dvid aso-mb-4nm.toml
```

## 3. Supervoxel Ingestion

### Copy voxels

We use `flyemflows` to copy the base voxel data into DVID. The procedure for launching the job is similar to the grascale export we performed above:

Copy the `03a-ingest-supervoxels` directory from this repository to our network file system.  Edit the file paths and dataset dimensions in `workflow.yaml`.  Also, pay special attention to the `store-type` for Zarr arrays:

- `store-type: DirectoryStore` - For "ordinary" zarr arrays with chunk names such as `15.7.20`
- `store-type: NestedDirectoryStore` - For zarr arrays whose chunks are stored in a directory hierarchy, e.g. `15/7/20`
- `store-type: N5Store` - For N5 volumes which we'll read via the `zarr` Python library

You may also wish to inspect `dask-config.yaml` to understand how each LSF node will be allocated for dask workers.  Pay attention to the `-P` setting which specifies who should be billed for the cluster job.

Then, from a cluster login node, submit the export job to the cluster, using the `launchflow` executable (from `flyemflows`):

```
conda activate flyem
bsub launchflow -n 64 03a-ingest-supervoxels
```

The job will not create any files in  your `03a-ingest-supervoxels` directory itself.  Instead, that directory is used as a template, and the actual "execution directory" will be a timestamped copy:

```
$ ls -d 03a-ingest-supervoxels*
03a-ingest-supervoxels
03a-ingest-supervoxels-20220802.144205
```

Monitor progress by inspecting the `output.log` within the execution directory.

### Ingest label indexes

While the job is copying supervoxels, it also collects the segment size and block locations for each supervoxel.
Those stats are saved in `block-statistics.h5`.  Now we need to process those statistics to create "label indexes" for the dvid index.  The `flyemflows` library comes with a command-line utility named `ingest_label_indexes` to generate and upload the label indexes.  In our example, we call that utility from a little wrapper script:

```bash
cd 03a-ingest-supervoxels-20220802.144205
./ingest-sv-indices.sh
```

### Supervoxel Meshes

Our cleaving tool, neu3, is designed to quickly display high-quality meshes.  For every supervoxel, we must produce a mesh and load it into DVID.  The `flyemflows` package has a few different "workflows" for creating meshes, but in this case, the `GridMeshes` workflow is best.

Copy the `03b-sv-meshes` directory from this repository to our network file system.  Edit the DVID server and UUID.

Then, from a cluster login node, submit the export job to the cluster, using the `launchflow` executable (from `flyemflows`):

```
conda activate flyem
bsub launchflow -n 256 03b-sv-meshes
```

(That takes about ~60 minutes.)

### Lock Root DVID UUID

With the supervoxels fully ingested, it's time to commit (lock) the root DVID node.  You can do that with DVID's REST API, or via a convenience function in `neuclease` which is already installed in your conda environment.

Example:

```python
from neuclease.dvid import *

# Commit root node
post_commit(
    'http://emdata6.int.janelia.org:8900',
    'cc036e',
    'Ingested supervoxels')

# Create a child of the root
post_newversion(
    'http://emdata6.int.janelia.org:8900',
    'cc036e',
    'Ingesting agglomeration')
```

## 4. Agglomeration Ingestion

### Ingest mapping table and label indexes

Now we can load an agglomeration mapping, to group supervoxels into agglomerated "bodies".
Once again, we will use `ingest_label_indexes` to load the mapping and label indexes into DVID.
This time, we must provide the mapping in the form of a `.csv` or `.npy` file with two columns: `segment_id, body_id`.
The `load-agglomeration` directory in this repository contains a script to convert Will's mapping to the format we need.
It is called by the following script:

```bash
cd load-agglomeration
./ingest-agglo-indices.sh
```

### Neuroglancer meshes

Neuroglancer isn't needed for proofreading, but it can be convenient for browsing and debugging.
We can use a service to dynamically generate meshes for us, or we can pre-generate neuroglancer meshes using yet another `flyemflows` workflow.

**TODO: Document each option.**

Either way, the first step is to create an empty `keyvalue` instance.  Even if we plan to use dynamically generated meshes (and therefore will not be populating the instance with content), neuroglancer won't know to display meshes for our data unless this instance exists.

```python
create_instance(
    'http://emdata6.int.janelia.org:8900',
    'cc036e',
    'segmentation_meshes',
    'keyvalue',
    tags={'type': 'meshes'}
)
```

### Lock Agglo DVID UUID

This is a good time to lock the DVID UUID, to distinguish between initial body states and changes introduced during proofreading.

```python
from neuclease.dvid import *

# Commit agglo node
post_commit(
    'http://emdata6.int.janelia.org:8900',
    '3324593350404bb8925259e9553a3594',
    'Ingested agglomeration mapping/indexes')

# Create a child of the agglo node
post_newversion(
    'http://emdata6.int.janelia.org:8900',
    '3324593350404bb8925259e9553a3594',
    'Open for proofreading')
```

## 5. Cleave Server

Before we can launch a cleave server, we need to construct
a table of the intrabody (internal) edge affinities.

The script `05-cleave-server/construct-cleave-table.py` constructs a suitable table,
using the edges provided by Will and the agglomeration table from the previous step
to determine which edges are internal and therefore retained in the cleave table.

After running that script, you can launch the cleave server using `launch_cleave_server.sh`.
Verify that the server launched by checking the log file.

