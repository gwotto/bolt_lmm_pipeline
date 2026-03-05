import os.path
import subprocess
import yaml
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

## Change to current working directory (directory where qsub was executed)
## within PBS job (workaround for SGE option "-cwd")
wd = os.environ['PBS_O_WORKDIR']
os.chdir(wd)

print('\nProgram: ' + program)
print('Version: ' + version)
print('Host: ' + host)
print('Start time: ' + str(datetime.now()))


## == parsing arguments

parser = argparse.ArgumentParser(description = "initializing bolt-lmm analysis pipeline")

## required arguments

## list the following arguments as required arguments instead of
## optional arguments, see
## https://stackoverflow.com/questions/24180527/argparse-required-arguments-listed-under-optional-arguments
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

# parser.add_argument('-h', '--help',
#                     ## metavar = '',
#                     help='prints out the help message')

args = parser.parse_args()

## debug mode
debug_mode = args.debug_mode

data_file = args.data_file


## == configuration ==

## get configurations from yaml file
yaml_file = args.config_file

yaml_fh = open(yaml_file, 'r')
cfg = yaml.safe_load(yaml_fh)

outdir = cfg['outdir']
data_dir = cfg['data-dir'] 
fam_file = cfg['fam-file']
pheno_file = cfg['pheno-file']

### filtering parameters for the selection of core SNPs
thr_maf = cfg['thr-maf']
thr_geno = cfg['thr-geno']
thr_hwe = cfg['thr-hwe']

## serialised gen_base_list
## serial_list = pickle.load(open(jason_file, 'rb'))
serial_list = json.load(open(data_file, 'rb'))

## to debug
print('\ndebug_mode: ' + str(debug_mode))
if debug_mode:
    pbs_array_index = 0
else:
    pbs_array_index = os.environ['PBS_ARRAY_INDEX']

gen_base_index = int(pbs_array_index) - 1

print('pbs array index: ' + str(pbs_array_index))
print('debug mode: ' + str(debug_mode)) 
print('base index: ' + str(gen_base_index))

gen_base = serial_list['gen-list'][gen_base_index]

print('gen_base: ' + gen_base)


## == file paths ==

tempdir = serial_list['tempdir']

plink_tempdir = serial_list['plink-tempdir']

bed_tempdir = serial_list['bed-tempdir']

print('\ncreating directory: ' + bed_tempdir)
Path(bed_tempdir).mkdir(parents=True, exist_ok=True)


input_bim = os.path.join(data_dir, (gen_base + '.bim'))
temp_bim = os.path.join(bed_tempdir, (gen_base + '.bim')) 

input_bed = os.path.join(data_dir, (gen_base + '.bed'))
temp_bed = os.path.join(bed_tempdir, (gen_base + '.bed')) 

temp_fam = os.path.join(bed_tempdir, (gen_base + '.fam')) 

plink_path = os.path.join(plink_tempdir, (gen_base + '.coreset'))

gen_base_path = os.path.join(bed_tempdir, gen_base)


## == data files for plink ==

## creating temporary input files for plink filtering and formatting
## per chromosome, linking the ukb_gen_chr*.bed file, writing a
## modified ukb_gen_chr*.bim file and copying a (common) fam file to
## the respective temp-ukb_gen_chr* directory

awk_c = "awk 'BEGIN { OFS = \"\t\"} {print $1,$1\"_\"$4\"_\"$5\"_\"$6\"_1\",$3,$4,$5,$6}' " + input_bim + ' > ' + temp_bim
link_c = 'ln -s ' + input_bed + ' ' + temp_bed
copy_c = 'cp ' + fam_file + ' ' + temp_fam

print("\nprocessing input files")
print(awk_c + '\n')
print(link_c + '\n')
print(copy_c + '\n')

os.system(awk_c)
os.system(link_c)
os.system(copy_c)


## == running plink ==

## creates coreset snp files per chromosome in temp-plink directory: .bed .bim .fam .log .nosex 
plink_c = 'plink --bfile ' + gen_base_path + ' --keep ' + pheno_file + ' --maf ' + str(thr_maf) + ' --geno ' + str(thr_geno) + ' --hwe ' + (thr_hwe) + ' --make-bed  --out ' + plink_path

print("running plink")
print(plink_c + '\n')

## not rather subprocess.run ?
os.system(plink_c)

print('\nfinished running plink at: ' + str(datetime.now()))
