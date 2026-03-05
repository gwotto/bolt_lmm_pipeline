import os.path
import subprocess
import yaml
import argparse
import socket
import sys
import time
import uuid
import json
import re
import shutil
import shlex
import pandas as pd
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


## parse import arguments
parser = argparse.ArgumentParser(description = "initializing bolt-lmm analysis pipeline")

## this is a trick to list the following arguments as required
## arguments instead of optional arguments, see
## https://stackoverflow.com/questions/24180527/argparse-required-arguments-listed-under-optional-arguments
requiredNamed = parser.add_argument_group('required named arguments')

requiredNamed.add_argument('-c', '--config-file', dest = 'config_file', required = True,
                    help = 'path to yaml configuration file',
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

# parser.add_argument('-h', '--help',
#                     ## metavar = '',
#                     help='prints out the help message')

args = parser.parse_args()

## run mode
run_mode = args.debug_mode


## == configuration ==

## get configurations from yaml file
yaml_file = args.config_file

yaml_fh = open(yaml_file, 'r')
cfg = yaml.safe_load(yaml_fh)

sample_file = cfg['sample-file']
gen_base = cfg['gen-base']
imp_base = cfg['imp-base']

outdir = cfg['outdir']
data_dir = cfg['data-dir']
temp_parent = os.path.expandvars(cfg['tempdir'])

temp_delete = cfg['temp-delete']

chunksize = cfg['chunksize']
ncpus = str(cfg['ncpus'])


## == modules ==

print("using environment modules")
   
# module_lib = cfg['module-lib']
module_init = cfg['module-init']
module_list = cfg['module-list']

## to get module environment working
exec(open(module_init).read())

## setting the modules library
## module('use', '-a', module_lib)
   
print('removing loaded modules....')
module('purge')

## necessary to remove all white space here
module_list = module_list.replace(" ", "")
module_list = module_list.split(',')

print("now loading modules....")

for mod in module_list:
    module('load', mod)
    
## write to log file
module('list')


## == output, log and temporary directories ==

Path(outdir).mkdir(parents=True, exist_ok=True)

log_dir = os.path.join(outdir, 'logs')
Path(log_dir).mkdir(parents=True, exist_ok=True)

plink_dir = os.path.join(outdir, 'plink')
Path(plink_dir).mkdir(parents=True, exist_ok=True)

bolt_dir = os.path.join(outdir, 'bolt')
Path(bolt_dir).mkdir(parents=True, exist_ok=True)

tempdir = os.path.join(temp_parent, ('tempdir_' +  uuid.uuid4().hex))
print('\ncreating temporary directory ' + tempdir)
Path(tempdir).mkdir(parents=True, exist_ok=True)

## temporary directory for the reformatted bim files, bed and fam files per chromosome
bed_tempdir = os.path.join(tempdir, 'temp-bed')
Path(bed_tempdir).mkdir(parents=True, exist_ok=True)

## temporary directory for plink filtered output per chromosome
plink_tempdir = os.path.join(tempdir, 'temp-plink')
Path(plink_tempdir).mkdir(parents=True, exist_ok=True)

## temporary directory for bolt-lmm output per chunk
bolt_tempdir = os.path.join(tempdir, 'temp-bolt')
Path(bolt_tempdir).mkdir(parents=True, exist_ok=True)

    
## == chromosomes, list of input files ==

if 'chr-list' in cfg:
    chr_list = cfg['chr-list']
    chr_list = chr_list.replace(" ", "")
    chr_list = chr_list.split(',')
else:
    chr_list = [*range(1, 23, 1)]
    print("no chromosome list in config file, using default set: " + str(chr_list) + '\n')
    
n_chr = len(chr_list)

## concatenating gen_base string with each chromosome name
gen_base_list = list(map(lambda chr: gen_base + str(chr), chr_list))

print('\ngen base list: ', gen_base_list)

imp_base_list = list(map(lambda chr: imp_base + str(chr), chr_list))

print('\nimp base list: ', imp_base_list)

n_gen_base = len(gen_base_list)

if n_chr != n_gen_base:
    sys.exit('number of chromosomes ' + n_chr +  ' and number of basenames ' + n_gen_base + ' do not match.')


## == serialising data for run-plink.py ==

json_file_plink = os.path.join(tempdir, ('data_file_' + uuid.uuid4().hex + '.json'))

serial_data = {'chr-list': chr_list,
               'gen-list': gen_base_list,
               'imp-list': imp_base_list,
               'tempdir': tempdir,
               'plink-tempdir': plink_tempdir,
               'bed-tempdir': bed_tempdir}

with open(json_file_plink, "w" ) as fh:
    json.dump(serial_data, fh )


## == running plink ==
    
pipeline_command = 'python3 ' + os.path.join(bindir, 'run-plink.py') + ' --config-file ' + yaml_file + ' --data-file ' + json_file_plink

echo_command = 'echo -e "%s"' % pipeline_command

## maybe take the qsub variables from config file
## qsub_var = cfg['qsub-var'] 

qsub_command = 'qsub  -S /bin/bash -o ' + log_dir + ' -e ' + log_dir + ' -V -N run-plink -J ' +  ('1-' + str(n_gen_base)) + ' -lselect=1:ncpus=1:mem=16gb -l walltime=04:00:00'

cmd =  echo_command + " | " + qsub_command

print('\nrunning run-plink.py on the pbs queue')

print('\npipeline command: ' + pipeline_command)
      
print('\nqsub command: ' + str(qsub_command))

print('\ncommand: ' + cmd)

p1 = subprocess.Popen(shlex.split(echo_command), stdout=subprocess.PIPE)
p2 = subprocess.Popen(shlex.split(qsub_command), stdin=p1.stdout, stdout=subprocess.PIPE)
## Allow p1 to receive a SIGPIPE if p2 exits
p1.stdout.close()

job_id = p2.communicate()[0].decode('UTF-8').replace('.pbs', '').rstrip()

print("\nrunning script run-plink.py as job-id: " + job_id)


## == monitoring the qsub processes ==

bolt.monitor_qsub(job_id)


## == merging core SNP sets ==

print('\nmerging core SNP sets.')

coreset_list_file = os.path.join(plink_tempdir, 'basename.list')

ch = open(coreset_list_file, "w")

for gb in gen_base_list:
   gb_path = os.path.join(plink_tempdir, (gb + '.coreset'))
   ch.write(gb_path + '\n')

ch.close()

coreset_path = os.path.join(plink_dir, 'coreset')

## merging the per chromosome core snp files 
plink_cmd = 'plink --merge-list ' + coreset_list_file + ' --make-bed --out ' + coreset_path

print('\nplink commamd: ' + plink_cmd)

plink_out = subprocess.run(shlex.split(plink_cmd), capture_output = True)

## don't need it right now
## plink_out = plink_out.stdout.decode('UTF-8')



## == creating subsets of bgen files in chunk size bins ==


chunk_list = []

for idx, chr in enumerate(chr_list):

    bgen_file = os.path.join(data_dir, (imp_base + str(chr) + '.bgen'))
    snps_file = os.path.join(data_dir, (imp_base + str(chr) + '.bim'))

    ## reading in bim file from ukb_imp_chr* file and putting positions in array

    f = open(snps_file, 'r')
    snp_array = f.readlines()

    ## only need snp position, i.e. 4th column
    snp_array = list(map(lambda snp: snp.split('\t')[3], snp_array))
    
    ## list of tuples
    ## ((chr1, (chunk1, chunk2)), (chr1, (chunk3, chunk4)), (chr2, (chunk1, chunk2)))

    chr_chunks = bolt.snp_chunks(snp_array, chr, chunksize)

    chunk_list.extend(chr_chunks)


print('\nlist of chunks:\n', chunk_list)


## == serialising data for run-bolt.py ==

json_file_bolt = os.path.join(tempdir, ('data_file_' + uuid.uuid4().hex + '.json'))

serial_data = {'chr-list': chr_list,
               'chunk-list': chunk_list,
               'imp-list': imp_base_list,
               'tempdir': tempdir,
               'plink-dir': plink_dir,
               'bolt-dir': bolt_dir,
               'bolt-tempdir': bolt_tempdir,
               'coreset-path': coreset_path}

with open(json_file_bolt, "w" ) as fh:
    json.dump(serial_data, fh )


## == running bolt ==

pipeline_command_1 = 'python3 ' + os.path.join(bindir, 'run-bolt.py') + ' --config-file ' + yaml_file + ' --data-file ' + json_file_bolt

echo_command_1 = 'echo -e "%s"' % pipeline_command_1

qsub_command_1 = 'qsub -S /bin/bash -o ' + log_dir + ' -e ' + log_dir + ' -V -N run-bolt -J ' + ('1-' + str(len(chunk_list))) + ' -lselect=1:ncpus=' + ncpus + ':mem=48gb' + ' -lwalltime=72:00:00'

cmd_1 = echo_command_1 + " | " + qsub_command_1

print('\nrunning run-bolt.py on the pbs queue')

print('\npipeline command: ' + pipeline_command_1)
      
print('\nqsub command: ' + str(qsub_command_1))

print('\ncommand: ' + cmd_1)

p1_1 = subprocess.Popen(shlex.split(echo_command_1), stdout=subprocess.PIPE)
p2_1 = subprocess.Popen(shlex.split(qsub_command_1), stdin=p1_1.stdout, stdout=subprocess.PIPE)
## Allow p1 to receive a SIGPIPE if p2 exits
p1_1.stdout.close()

job_id_1 = p2_1.communicate()[0].decode('UTF-8').replace('.pbs', '').rstrip()

print("\nrunning script run-bolt.py as job-id: " + job_id_1)


## == monitoring the qsub processes ==

bolt.monitor_qsub(job_id_1)

## == concatenating bolt chunks ==

bolt_outfile = os.path.join(bolt_dir, 'model_1.bolt.txt')

print('\nconcatenating bolt-lmm output chunks and writing to file ' + bolt_outfile)

bolt_tempfile_list = []

for chunk in chunk_list:

    ## print('chunk: ' + str(chunk))
    chr = chunk[0]
    ## print('chr: ' + chr)
    interval = chunk[1]

    bolt_tempfile = os.path.join(bolt_tempdir, (imp_base + str(chr) + '_' + interval[0] + '-' +
                                            interval[1] + '.model_1.bolt'))

    bolt_tempfile_list.append(bolt_tempfile)

## print(bolt_tempfile_list)


bolt_df = pd.concat((pd.read_csv(f, sep = '\t', dtype={'CHR': 'str', 'BP': 'str', 'GENPOS' : 'str', 'CHISQ_BOLT_LMM_INF' : 'str'}) for f in bolt_tempfile_list), ignore_index=True)

bolt_df.to_csv(bolt_outfile, sep='\t', index=False, quoting=None)


if(temp_delete):
    print('\ndeleting temporary directory ' + tempdir)
    shutil.rmtree(tempdir)

print('\nfinished pipeline at ' + str(datetime.now()))
