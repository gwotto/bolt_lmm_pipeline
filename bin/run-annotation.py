import os.path
import sys
import socket
import argparse
from datetime import datetime

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



vep = '/rds/general/project/uk-biobank-2020/live/resources/ensembl-vep/ensembl-vep-release-107/vep'

variant_file = '/rds/general/project/uk-biobank-2020/live/resources/ensembl-vep/ensembl-vep-release-107/examples/homo_sapiens_GRCh38.vcf'

# cache_path = '/rds/general/user/gotto/ephemeral/test/bolt-lmm/test-annotation/cache'

cache_path = '/rds/general/project/uk-biobank-2020/live/resources/ensembl-vep/ensembl-vep-release-107/cache'

vep_output = '/rds/general/user/gotto/ephemeral/test/bolt-lmm/test-annotation/vep_output.txt'

vep_c = vep + ' -i ' + variant_file  + ' -o ' + vep_output + ' --cache --dir_cache ' + cache_path

print('\nrunning vep with command')
print('\n' + vep_c)

os.system(vep_c)
