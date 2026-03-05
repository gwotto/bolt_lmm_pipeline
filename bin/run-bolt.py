import os.path
import subprocess
import yaml
import re
import argparse
import sys
import socket
import json
from datetime import datetime
from pathlib import Path

## path to library files
bindir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(bindir, "../lib/"))

import bolt

program = os.path.basename(sys.argv[0])
version = bolt.__version__()
host = socket.gethostname()

## If not in debug mode, change to current working directory
## (directory where qsub was executed) within PBS job (workaround for
## SGE option "-cwd")

## needs python 3.8
if 'PBS_O_WORKDIR' in os.environ:
    wd = os.environ['PBS_O_WORKDIR']
    os.chdir(wd)

print('\nProgram: ' + program)
print('Version: ' + version)
print('Host: ' + host)
print('Start time: ' + str(datetime.now()))


## == parsing arguments ==

parser = argparse.ArgumentParser(description = "initializing bolt-lmm analysis pipeline")

## required arguments

requiredNamed = parser.add_argument_group('required named arguments')

requiredNamed.add_argument('-c', '--config-file', dest = 'config_file', required = True,
                           help = 'path to yaml configuration file',
                           type = lambda x: bolt.is_valid_file(parser, x))

requiredNamed.add_argument('-f', '--data-file', dest = 'data_file',
                           required = True,
                           help = 'path to json data file', metavar = 'FILE',
                           type = lambda x: bolt.is_valid_file(parser, x))

## optional arguments

parser.add_argument('-d', '--debug-mode',
                    dest = 'debug_mode',
                    action='store_true',
                    help='run in debug mode if set')

parser.add_argument('-v', '--version',
                    ## metavar = '',
                    action = 'version', version='%(prog)s ' + version,
                    help='prints out the version of the program')


args = parser.parse_args()

## run mode
debug_mode = args.debug_mode

data_file = args.data_file


## == configurations ==

## get configurations from yaml file
yaml_file = args.config_file

yaml_fh = open(yaml_file, 'r')
cfg = yaml.safe_load(yaml_fh)

## import parameters from yaml
outdir = cfg['outdir']
sample_file = cfg['sample-file']
pheno_file = cfg['pheno-file']
data_dir = cfg['data-dir'] 
imp_base = cfg['imp-base']

pheno_1 = cfg['pheno-1']
cov_1 = cfg['cov-1']
ncpus = str(cfg['ncpus'])
ldscore_file = cfg['ldscore-file']
min_maf = cfg['min-maf']
min_info = cfg['min-info']

remove_samples_list = cfg['remove-samples-list']


## serialised json_list
serial_list = json.load(open(data_file, 'rb'))


## == file paths ==
plink_dir = serial_list['plink-dir']
bolt_dir = serial_list['bolt-dir']
bolt_tempdir = serial_list['bolt-tempdir']
tempdir = serial_list['tempdir']
coreset_path = serial_list['coreset-path']

## creating directory, dealing with race condition
bgen_tempdir = os.path.join(tempdir, 'temp-bgen')
Path(bgen_tempdir).mkdir(parents=True, exist_ok=True)


## to debug
if debug_mode:
    pbs_array_index = 6
else:
    pbs_array_index = os.environ['PBS_ARRAY_INDEX']

base_index = int(pbs_array_index) - 1

print('pbs array index: ' + str(pbs_array_index))
print('debug mode: ' + str(debug_mode)) 
print('base index: ' + str(base_index))
    

## == generating bgenfile for range ==

chunk = serial_list['chunk-list'][base_index]
print('chunk: ' + str(chunk))

chr = chunk[0]
interval = chunk[1]

bgen_file = os.path.join(data_dir, (imp_base + str(chr) + '.bgen'))
bgen_tempfile= (os.path.join(bgen_tempdir, (imp_base + str(chr) + '_' + interval[0] + '-' +
                                            interval[1] + '.bgen')))

## bgen range needs a leading 0 for 1-digit chromosomes (WTF!)
bgen_range = str(chr).zfill(2) + ':' + interval[0] + '-' + interval[1]

bgen_c = 'bgenix -g ' + bgen_file + ' -incl-range ' + bgen_range + ' > ' + bgen_tempfile

print('\ngenerating bgen file for range ' + bgen_range + ' with command')
print('\n' + bgen_c)

os.system(bgen_c)

## bgen index
bgen_idx_c = 'bgenix -g ' + bgen_tempfile + ' -index'

print('\nindexing bgen file ' + bgen_tempfile)
print('\n' + bgen_idx_c)

os.system(bgen_idx_c)


## == run bolt-lmm ==

## TODO multiple models
stats_file = (os.path.join(bolt_tempdir, (imp_base + str(chr) + '_' + interval[0] + '-' +
                                            interval[1] + '.model_1.coresnps')))

stats_file_bgen_snps = (os.path.join(bolt_tempdir, (imp_base + str(chr) + '_' + interval[0] +
                                                    '-' + interval[1] + '.model_1.bolt')))

# phenotypes
pheno_col = pheno_1.split(',')[0]
print('\nphenotype: ' + pheno_col)

# categorial covariates
ccovar = cov_1.split(';')[0].split(',')

## test if there are categorial covariates
if(ccovar[0] != ''):
    print('\ncategorial covariate(s): ' + str(ccovar))
    ccovar_string = ''.join([(' --covarCol=' + x) for x in ccovar])
else:
    ccovar_string = ''

# quantitative covariates
qcovar = cov_1.split(';')[1].split(',')

## test if there are quantitative covariates
if(qcovar[0] != ''):
    print('\nquantitative covariate(s): ' + str(qcovar))
    qcovar_string = ''.join([(' --qCovarCol=' + x) for x in qcovar])
else:
    qcovar_string = ''

if((ccovar[0] != '') or (ccovar[0] != '')):
    print('\ncovariates in file: ' + pheno_file)
    covar_file_string = ' --covarFile=' + pheno_file
else:
    covar_file_string = ''

## if there is a file with samples to remove
if(remove_samples_list):
    print('\nsamples to remove in file: ' + remove_samples_list)
    remove_string = ' --remove=' + remove_samples_list
else:
    remove_string = ''
    
## TODO multiple models
## TODO get betas
bolt_c = ('bolt ' +
          ' --bfile=' + coreset_path +
          ' --noBgenIDcheck' +
          ' --bgenFile=' + bgen_tempfile +
          ' --sampleFile=' + sample_file +
          ' --phenoFile=' + pheno_file +
          ' --phenoCol=' + pheno_col +
          ' --lmm' +
          ' --covarMaxLevels=50 ' +
          ' --h2gGuess=0.15 ' +
          ' --numThreads=' + ncpus +
          ' --LDscoresFile=' + ldscore_file +
          ' --LDscoresMatchBp' +
          ' --verboseStats' +
          ' --bgenMinMAF=' + str(min_maf) +
          ' --bgenMinINFO=' + str(min_info) +
          ' --statsFile=' + stats_file +
          ' --statsFileBgenSnps=' + stats_file_bgen_snps +
          covar_file_string +
          ccovar_string +
          qcovar_string +
          remove_string
          )

print('\nrunning bolt-lmm with command')
print('\n' + bolt_c)

## not rather subprocess.run ?
os.system(bolt_c)

print('\nfinished running bolt-lmm at: ' + str(datetime.now()))


# $(find ${BINPATH}/ -name bolt) \
#     --bfile="$OUTPATH/plink/coreset" \
#     --noBgenIDcheck \
#     --bgenFile="$BASENAME.$RANGE.bgen" \
#     --sampleFile="$(basename $SAMPLEFILE)" \
#     --phenoFile="$(basename $PHENOFILE)" \
#     --phenoCol="log_Mean_cIMT_Max" \
#     --lmm \
#     --covarMaxLevels=50 \
#     --h2gGuess=0.15 \
#     --numThreads=$NUMTHREADS \
#     --LDscoresFile="$(basename $LDSCOREFILE)" \
#     --LDscoresMatchBp \
#     --verboseStats \
#     --bgenMinMAF=0.01 \
#     --bgenMinINFO=0.1 \
#     --statsFile="$BASENAME.$RANGE.model_1.coresnps" \
#     --statsFileBgenSnps="model1_$BASENAME.$RANGE.bolt" \
# --covarFile="$(basename $PHENOFILE)" \
#     --qCovarCol="Age" \
#     --qCovarCol="PC1" \
#     --qCovarCol="PC2" \
#     --qCovarCol="PC3" \
#     --qCovarCol="PC4" \
#     --covarCol="Sex" \
#     --covarCol="Center" 

#     command = paste0('$(find ${BINPATH}/ -name bolt) \\
#     --bfile="$OUTPATH/plink/coreset" \\
#     --noBgenIDcheck \\
#     --bgenFile="$BASENAME.$RANGE.bgen" \\
#     --sampleFile="$SAMPLEFILE" \\
#     --phenoFile="$PHENOFILE" \\
#     --phenoCol="',pheno_var,'" \\
#     --lmm \\
#     --covarMaxLevels=50 \\
#     --h2gGuess=0.15 \\
#     --numThreads=$NUMTHREADS \\
#     --LDscoresFile="$LDSCOREFILE" \\
#     --LDscoresMatchBp \\
#     --verboseStats \\
#     --bgenMinMAF=',minmaf,' \\
#     --bgenMinINFO=',mininfo,' \\
#     --statsFile="$BASENAME.$RANGE.model_',modelIndex,'.coresnps" \\
#     --statsFileBgenSnps="model',modelIndex,'_$BASENAME.$RANGE.bolt" \\\n')
    
#     if (getbetas) command = paste0(command, paste0('--predBetasFile = "model', modelIndex, '_$BASENAME.$RANGE.bolt_betas" \\\n'))
#     if (length(q_cov)+length(c_cov)) command = paste0(command, '--covarFile="$(basename $PHENOFILE)" \\\n')
#     if (length(q_cov)) command = paste0(command, makeFlag("qCovarCol",q_cov))
#     if (length(c_cov)) command = paste0(command, makeFlag("covarCol",c_cov))
#     command = substr(command,1,nchar(command)-2)
#     commands = c(commands, command)
#     commands = c(commands, paste0("Rscript ",filter_file," model",modelIndex,"_$BASENAME.$RANGE.bolt ",minmaf," ",mininfo," ",snpstokeep))
#     commands = c(commands, paste0("cp model",modelIndex,"_$BASENAME.$RANGE.bolt $OUTPATH/ranges/"))
#     if (getbetas) commands = c(commands, paste0("cp model", modelIndex, "_$BASENAME.$RANGE.bolt_betas $OUTPATH/ranges_betas/"))
    
#     resultspath = paste0(outpath,"/results/")
#     filename = paste0(resultspath,"/model",modelIndex,"_.bolt")
#     if (!file.exists(filename)) {
#       dir.create(resultspath)
#       fileConn = file(filename)
#       writeLines(c(paste0("#Phenotype: ",pheno_var), 
#                    paste0("#Categorical covariates: ",c_cov), 
#                    paste0("#Quantitative covariates: ",q_cov)), fileConn)
#       close(fileConn)
#     }

#     modelIndex = modelIndex + 1 
#   }
# }
