# The bolt-lmm pipeline on the high-performance computer cluster


## Introduction

This pipeline runs bolt-lmm (Loh et al, Nat Genet 2015; Loh et al. Nat
Genet 2018;
https://alkesgroup.broadinstitute.org/BOLT-LMM/BOLT-LMM_manual.html)
with UK biobank data on the Imperial hpc cluster. It formats data,
divides them into chunks and runs the chunks through bolt-lmm in
parallel (see ![pipeline diagram](./doc/fig-bolt-pipeline.pdf))


The pipeline carries out association testing by running bolt-lmm on
UKB imputed SNPs using a mixed model built on a subset of hard-called,
PLINK-format UKB genotypes. Thus, it first performs its model-fitting
on PLINK-format genotypes and then applies the model to scan any
provided imputed SNPs.


## Prerequisites

The pipeline needs software and python packages installed in the
environment path. On the Imperial hpc cluster, this is achieved by two
methods:

1. Environment modules, which load installed software into the search
   path. This is carried out by the pipeline itself. Required modules
   are listed in the configuration file.
2. The Conda enironment which provides python, python packages and
   other software defined by the user. For instructions on how to use
   a conda environment see
   https://www.imperial.ac.uk/admin-services/ict/self-service/research-support/rcs/support/applications/python/. 
   
When using conda for the first time on the cluster, you need to set it up for your environment:

```bash
module load anaconda3/personal
anaconda-setup
```

3. Before running this pipeline for the first time you have to create
   a Conda environment, called 'bolt', using the configuration file in
   the config directory.

```bash
module load anaconda3/personal
conda env create --file /path/to/config/environment.yml
```

4. If the environment.yml file has been modified, e.g. in a newer
   version of the pipeline, the environment can be updated like this:

```bash
conda env update --file /path/to/config/environment.yml
```


## Running the pipeline

### Configuration

The pipeline run is configured by the yaml-format file config.yml. An
example configuration file is located in
`/rds/general/project/uk-biobank-2020/live/software/bolt-lmm-pipeline/config/config.yml`. Copy
this file to a convenient location and edit the configuration to your
needs. For pipeline tests, an example phenotype file
`/rds/general/project/uk-biobank-2020/live/software/bolt-lmm-pipeline/data/sample.phenotype.txt`
can be used.

#### Data files

1. Phenotype file, containing phenotypes and covariates, with the
   first line containing column headers and subsequent lines
   containing records, one per individual. bolt-lmm requires this to
   be a whitespace-delimited file, so tab-delimited will do. The
   first two columns must be FID and IID (the PLINK identifiers of an
   individual). Any number of columns may follow. Values of -9 and NA
   are interpreted as missing data. All other values in the column
   should be numeric.
2. Sample information file for genotype data in .fam format.
3. Sample information file for imputed data in Oxford .sample format
   (used in bolt --sampleFile argument).
4. Data directory containing core snp files (in .bed and .bim format)
   and imputed snp files (in .bgen format). Currently these are
   ukb_gen_chr\*.bim, ukb_gen_chr\*.bed, and ukb_imp_chr\*.bgen files
   in
   `/rds/general/project/uk-biobank-2017/live/reference/sdata_latest/`
   by default. (TODO)
5. A file that is listing missing samples to remove (for the bolt
   --remove argument), e.g. samples in the fam-file that are missing
   in the sample-file. This is a header-less tab-delimited text file,
   FID and IID must be the first two columns. If samples are missing
   and no such remove-file is provided, bolt-lmm produces a file
   listing the samples to remove and exits with an error. The
   generated file can subsequently be used as the missing samples
   list.
   
#### Covariates

To use columns in the phenotype file as covariates in the model, the
config file has the following form:

	cov-1: cat_cov1,...,cat_covn;quant_cov1,...,quant_covn

i.e. a comma-separated list of categorial covariates, followed by a
semicolon, followed by a comma-separated list of quantitative
covariates. For example:

1. Categorial and quantitative covariates:

		cov-1: Sex,Center;Age,PC1,PC2,PC3,PC4

2. Quantitative covariates only:

		cov-1: ;age,PC1,PC2,PC3,PC4,PC5,PC6,PC7,PC8,PC9,PC10


#### Temporary files directory

The program produces temporary files and directories, the location of
which can be set with the 'tempdir' variable. These files take a lot
of space, therefore it is recommended to choose a location on the
ephemeral directory (default is
/rds/general/user/$USER/ephemeral/). The variable temp-delete
(True/False) determines if the temporary directory gets deleted at the
end of the pipeline run.



## Starting the pipeline

1. Loading the conda environment.

```bash
module load anaconda3/personal
source activate
conda activate bolt
```

2. Starting the pipeline

``` bash
python /rds/general/project/uk-biobank-2020/live/software/bolt-lmm-pipeline/bin/initialise-pipeline.py --config-file config.yml

```

3. Pipeline help message

``` bash
python /rds/general/project/uk-biobank-2020/live/software/bolt-lmm-pipeline/bin/initialise-pipeline.py -h

```

## Results

The output of the pipeline is a text file  *.bolt with the following columns:

| SNP | CHR | BP | GENPOS | ALLELE1 | ALLELE0 | A1FREQ | INFO | CHISQ\_LINREG | P\_LINREG | BETA | SE | CHISQ\_BOLT\_LMM\_INF | P\_BOLT\_LMM\_INF | CHISQ\_BOLT\_LMM | P_BOLT_LMM |

Note that the last two columns (CHISQ\_BOLT\_LMM | P_BOLT_LMM) can be
missing. By default, the pipeline runs with option `--lmm`, according to the
bolt-lmm manual:

> Performs default BOLT-LMM analysis, which consists of (1a)
> estimating heritability parameters, (1b) computing the BOLT-LMM-inf
> statistic, (2a) estimating Gaussian mixture parameters, and (2b)
> computing the BOLT-LMM statistic only if an increase in power is
> expected. If BOLT-LMM determines based on cross-validation that the
> non-infinitesimal model is likely to yield no increase in power, the
> BOLT-LMM (Bayesian) mixed model statistic is not computed.


**Warning:**

This pipeline has been tested vigorously and so far has proven to
yield the correct and complete result given the provided input and
configuration. However, it can not be ruled out that problems on the
hpc environment can occur, like nodes getting stuck, an unavailable
file system, lack of storage space etc. For this reason, it is good
practise to review the log files for possible error messages. It is
also recommended to make some plausibility tests with the output file,
e.g. if the numer of variants meets the expectation by counting line
numbers using the `wc` command, or by checking if all chromosomes are
represented in the output: `cut -f 2 output.txt | uniq -c`.


## Version history

  * v0.0.4 (2022-11-24)
	conda environment
	
  * v0.0.3 (2022-08-22)
	Documentation, config file
  
  * v0.0.2 (2022-08-12)
	Code organised in functions, documentation, updated config file, subprocesses
	
  * v0.0.1 (2022-07-28)
	First version running on hpc cluster

## TODO
  
  * variant annotation
  * multiple models in parallel
  * mail upon job completion
  * check queues (medbio?)
  * check warning: Overlap of sample file and fam file < 50%
  * dedicated conda environment?


