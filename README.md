# sshicstuff: a pipeline for analyzing ssDNA-specific Hi-C data

## Dependencies  
It is recommended to use a virtual environment to install the dependencies. We suggest you to use the 
requirements.yml file to install a conda environment or mamba.
You can do it as follows:

```bash
mamba env create -f environment.yml
```

Activate the environment:
    
```bash
mamba activate sshicstuff
```

Inside the sshicstuff directory, install the package with the following command:

```bash
pip install -e .
```


## Description  
ssHiCstuff enables the analysis of ssDNA-specific Hi-C contact generated from paired-end Illumina reads. This project has not yet been packaged (coming soon). 
It includes multiples independents scripts which are executed one after the 
other according to the main script ```pipeline.py```. 
This pipeline is actually a downstream analysis extension of the HiC analysis pipeline hicstuff 
(https://github.com/koszullab/hicstuff). You can use it as follows:


## Usage

The sshicstuff command line interface is composed of multiple subcommands. 
You can always get a summary of all available commands by running:


```bash
Single Stranded DNA Hi-C pipeline for generating oligo 4-C profiles and aggregated contact matrices.

usage:
    sshicstuff [-hv] <command> [<args>...]

options:
    -h, --help                  shows the help
    -v, --version               shows the version

The subcommands are:
    subsample           Subsample and compress FASTQ file using seqtk.
    genomaker           Create a chromosome artificial that is the concatenation of the
                        annealing oligos and the enzyme sequence.
    associate           Associate oligo/probe name to fragment/read ID that contains it.
    hiconly             Keep only Hi-C reads from a sparse matrix file (i.e., remove all ssDNA reads).
    filter              Filter reads from a sparse matrix and keep only pairs of reads that 
                        contain at least one oligo/probe.
    coverage            Calculate the coverage per fragment and save the result to a bedgraph.
    profile             Generate a 4C-like profile for each ssDNA oligo.
    rebin               Rebin change binning resolution of a 4C-like profile
    stats               Generate statistics and normalization for contacts made by each probe.
    compare             Compare the capture efficiency of a sample with that of a wild type
                        (may be another sample).
    aggregate           Aggregate all 4C-like profiles on centromeric or telomeric regions.
    pipeline            Run the entire pipeline from filtering to aggregation.
    view                Open a graphical user interface to visualize 4-C like profile.
```


## Subcommands :

### Subsample

### Genomaker

### Associate

### Hiconly

### Filter

### Coverage

### Profile

### Rebin

### Stats

### Compare

### Aggregate

### Pipeline

### View



## Mandatory files structure

#### Annealing Oligo file structure

#### Capture Oligo file structure

#### Sparse matrix file structure

#### Fragment file structure

#### Chromosome coordinates file structure

#### Additional probe groups file structure



