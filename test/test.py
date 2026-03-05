##

import random
import sys

sys.path.append("../lib/")

import bolt

snp_list = random.sample(range(0,1000),100)

snp_list.sort()

bolt.snp_chunks(snp_list, 'chr3', 10)



def test_snp_cunks() -> None:
    assert chunk_list() == 0






# case = 1
# queue = "all.q"
# jobName = "test-1" % case
# cmd = "echo %i; date; sleep 60; date; echo $PBS_O_WORKDIR; echo $PBS_ARRAY_INDEX" % case
# echoArgs = ["echo", "-e", "'%s'" % cmd]
# print(" ".join(echoArgs))
# qsubArgs = ["qsub", "-J", "1-2", "-V", "-N", jobName, "-l", "select=1:ncpus=1:mem=16gb", "-l", "walltime=01:00:00"]
# print(" ".join(qsubArgs))


# wholeCmd = " ".join(echoArgs) + " | " + " ".join(qsubArgs)
# out = subprocess.run(wholeCmd, shell=True, capture_output = True)
# out_stdout = out.stdout.decode('ascii')

# qstat_1 = subprocess.run(['qstat'], capture_output=True)

# qstat_1_stdout = qstat_1.stdout.decode('ascii')
# qstat_1_stderr = qstat_1.stderr.decode('ascii')
# qstat_1_returncode = qstat_1.returncode

# print('\njob id:\n' + job_id)
# print('\nqstat_1 stdout:\n' + qstat_1_stdout)
# print('\nqstat_1 stderr:\n' + qstat_1_stderr)
# print('\nqstat_1 returncode:\n' + str(qstat_1_returncode))
