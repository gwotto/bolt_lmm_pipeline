import os.path
import subprocess
import yaml
import argparse
import sys
import time
import uuid
import json
import shlex
from datetime import datetime
from pathlib import Path

## path to library files
bindir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(bindir, "../lib/"))

import bolt

program = os.path.basename(sys.argv[0])
version = bolt.__version__()

## parse import arguments
parser = argparse.ArgumentParser(description = "initialising bolt-lmm analysis pipeline")


## list the following arguments as required arguments instead of
## optional arguments, see
## https://stackoverflow.com/questions/24180527/argparse-required-arguments-listed-under-optional-arguments
requiredNamed = parser.add_argument_group('required named arguments')

requiredNamed.add_argument('-c', '--config-file', dest = 'config_file', required = True,
                    help = 'path to yaml configuration file',
                    type = lambda x: bolt.is_valid_file(parser, x))

## optional arguments

parser.add_argument('-d', '--debug-mode',
                    dest = 'debug_mode', default='false',
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

print('\nProgram: ' + program)
print('Version: ' + version)
print('Start time: ' + str(datetime.now()))

## get configurations from yaml file
yaml_file = args.config_file

yaml_fh = open(yaml_file, 'r')
cfg = yaml.safe_load(yaml_fh)

sample_file = cfg['sample-file']


## == output and log directory ==

outdir = cfg['outdir']
Path(outdir).mkdir(parents=True, exist_ok=True)

log_dir = os.path.join(outdir, 'logs')
Path(log_dir).mkdir(parents=True, exist_ok=True)


init_command = 'python3 ' + os.path.join(bindir, 'main.py') + ' --config-file ' + yaml_file

echo_command = 'echo -e "%s"' % init_command

## maybe take the qsub variables from config file
## qsub_var = cfg['qsub-var'] 

## 72 hours is the maximum walltime in the throughput node

qsub_command = 'qsub -S /bin/bash -o ' + log_dir + ' -e ' + log_dir + ' -V -N main -lselect=1:ncpus=1:mem=64gb -lwalltime=72:00:00'

## I am not using shell=True, so need to use shlex to parse the string
## for subprocess.Popen
cmd = echo_command + " | " + qsub_command

print('\nrunning main.py on the pbs queue')

print('\ninitialisation command: ' + init_command)

print('\nqsub command: ' + str(qsub_command))

print('\ncommand: ' + cmd)

p1 = subprocess.Popen(shlex.split(echo_command), stdout=subprocess.PIPE)
p2 = subprocess.Popen(shlex.split(qsub_command), stdin=p1.stdout, stdout=subprocess.PIPE)
## Allow p1 to receive a SIGPIPE if p2 exits
p1.stdout.close()

job_id = p2.communicate()[0].decode('UTF-8').replace('.pbs', '').rstrip()

print('\nbolt-lmm pipeline initialised with job-id: ' + job_id)

print('\n')
