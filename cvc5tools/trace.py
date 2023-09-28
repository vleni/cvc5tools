from pathlib import Path
import re
import unittest
from typing import Optional

from . import tabulate

# Lower the priority of threads so this does not hog the CPU
NICE = 20

# Matches "all_simplify :args (" in front and matches a space after.
# The space is there to eliminate all "evaluate" calls!
REGEX_ALETHE_RULE = re.compile(r"(?<=\:rule all_simplify \:args \()[A-Za-z0-9\-]+(?= )")

def trace_worker(args):
    import subprocess
    import os
    os.nice(NICE)

    command_stem, pathIn, pathOut = args
    command = command_stem + [Path(pathIn)]
    pathOut.parent.mkdir(exist_ok=True, parents=True)
    trace = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           preexec_fn=lambda: os.nice(NICE))

    if trace.returncode == 0:
        with open(str(pathOut) + '.out', "w") as f:
            for line in trace.stdout.decode('utf-8').split('\r\n'):
                f.write(line)
    else:
        with open(str(pathOut) + '.err', "w") as f:
            for line in trace.stderr.decode('utf-8').split('\r\n'):
                f.write(line)
            f.write(str(trace.returncode))


def routine_trace(args):
    """
    inputs: ../*.smt2
    outputs: ../*.smt2.out or .err depending on the output
    """
    # Create the output directory
    args.output = Path(args.output)
    args.output.mkdir(exist_ok=True, parents=True)

    # Filter the input so we don't do redundant work
    globOutput = [str(path.relative_to(args.output).with_suffix(""))
                      for path in args.output.glob("**/*")]
    # glob the input directory to see what files need processing
    globInput = [str(path.relative_to(args.file))
                 for path in args.file.glob("**/*.smt2")]

    fileList = [path for path in globInput if path not in set(globOutput)]
    print(f"{len(globInput) - len(fileList)}/{len(globInput)} input files skipped")

    import tqdm
    import multiprocessing

    threads = multiprocessing.cpu_count() - 2 if args.threads == 0 else args.threads

    print(f"Executing with {threads} threads")
    command_stem = [
        args.cvc5,
        '--produce-proofs',
        '--proof-granularity=dsl-rewrite',
        '--dump-proofs',
        '--proof-format-mode=alethe',
        '--dag-thres=0',
        f'--tlimit={args.timeout}',
    ]

    print(f"$ {' '.join(command_stem)} $IN > $OUT")
    # Execute cvc5
    results = None
    if threads > 1:
        feedstock = [
            (command_stem, args.file / path, args.output / path)
            for path in fileList
        ]
        with multiprocessing.Pool(threads) as pool:
            iterant = pool.imap_unordered(trace_worker, feedstock)
            results = list(tqdm.tqdm(iterant, total=len(fileList)))
    else:
        feedstock = [
            (command_stem, args.file / path, args.output / path)
            for path in fileList
        ]
        results = [
            trace_worker(a)
            for a in tqdm.tqdm(feedstock)
        ]
def count_worker(args):
    import subprocess
    import os
    os.nice(NICE)

    pathIn = args
    counts = dict()
    with open(pathIn, 'r') as f:
        for l in f.readlines():
            l = l.rstrip()
            matchObj = REGEX_ALETHE_RULE.search(l)
            if matchObj is not None:
                rule = matchObj.group(0)
                counts[rule] = 1 + counts.get(rule, 0)
    return counts
def routine_count(args):
    args.output = Path(args.output)
    args.output.mkdir(exist_ok=True, parents=True)
    fileList = [path for path in args.file.glob("**/*.out")]

    import tqdm
    import multiprocessing
    threads = multiprocessing.cpu_count() - 2 if args.threads == 0 else args.threads

    feedstock = fileList
    results = []
    if threads > 1:
        feedstock = fileList
        with multiprocessing.Pool(threads) as pool:
            iterant = pool.imap_unordered(count_worker, feedstock)
            results = list(tqdm.tqdm(iterant, total=len(fileList)))
    else:
        results = [
            count_worker(a)
            for a in tqdm.tqdm(feedstock)
        ]

    # Collects all the keys and merge them
    count = dict()
    for result in results:
        for k,v in result.items():
            count[k] = v + count.get(k, 0)
    keys = sorted(count.keys())
    for k in keys:
        print(f"{k}: {count[k]}")


def make_regression_worker(args):
    import subprocess
    import os
    os.nice(NICE)

    pathIn, pathAux, pathOut = args
    pathOut.parent.mkdir(exist_ok=True, parents=True)

    with open(pathIn, 'r') as fi:
        with open(pathOut, 'w') as fo:
            for line in fi.readlines():
                if line.startswith('(assert'):
                    continue
                fo.write(line)
    with open(pathAux, 'r') as fi:
        with open(str(pathOut) + '.out', 'w') as fo:
            for line in fi.readlines():
                if ':rule all_simplify' not in line:
                    continue
                fo.write(line)


def routine_make_regression(args):
    """
    -i: ../*.smt2
    -a: [same structure as -i but with .out files]
    outputs: {.smt2, .smt2.out} pairs
    """
    # Create the output directory
    args.auxiliary = Path(args.auxiliary)
    args.output = Path(args.output)
    args.output.mkdir(exist_ok=True, parents=True)

    # raw smt2 files
    globInput = [str(path.relative_to(args.file))
                 for path in args.file.glob("**/*.smt2")]
    # raw output files
    globAuxiliary = [path.relative_to(args.auxiliary)
                     for path in args.auxiliary.glob("**/*.out")]

    fileList = [path.with_suffix("") for path in globAuxiliary]

    import tqdm
    import multiprocessing

    threads = multiprocessing.cpu_count() if args.threads == 0 else args.threads

    print(f"Executing with {threads} threads")
    results = None
    feedstock = [
        (args.file / path, str(args.auxiliary / path) + '.out', args.output / path)
        for path in fileList
    ]
    if threads > 1:
        with multiprocessing.Pool(threads) as pool:
            iterant = pool.imap_unordered(make_regression_worker, feedstock)
            results = list(tqdm.tqdm(iterant, total=len(fileList)))
    else:
        results = [
            make_regression_worker(a)
            for a in tqdm.tqdm(feedstock)
        ]


class TestTrace(unittest.TestCase):
    def assert_alethe_rule_find(self, s: str, name: Optional[str]):
        obj = REGEX_ALETHE_RULE.search(s)
        if name is None:
            self.assertIsNone(obj)
        else:
            self.assertIsNotNone(obj)
            self.assertEqual(obj.group(0), name)

    def test_alethe_rule(self):
        self.assert_alethe_rule_find("(step t4 (cl (= (not true) false)) :rule all_simplify :args (evaluate))",
                                     None)
        self.assert_alethe_rule_find("(step t7 (cl (not false)) :rule false)",
                                     None)
        self.assert_alethe_rule_find("(step t2 (cl (= (bvule x x) true)) :rule all_simplify :args (bv-ule-self x))",
                                     "bv-ule-self")

if __name__ == '__main__':
    import os, sys

    if len(sys.argv) == 1:
        unittest.main()
        sys.exit(0)

    import argparse

    parser = argparse.ArgumentParser(
                    prog='CVC5 Tester',
                    description='Executes CVC5',
                    epilog='proof-new',
                    formatter_class=argparse.RawTextHelpFormatter)

    EXECS = [
        ('trace', "Execute cvc5 on a bunch of smt2 files in the -f directory and trace what rules are used. Then output to -o", routine_trace),
        ('trace-count', "Count rule occurrences in a trace (-f) produced by trace.", routine_count),
        ('make_regression', "Make regression test", routine_make_regression),
    ]
    EXEC_DICT = { name: func for name, _, func in EXECS }
    help_str = '\n\t'.join(f"{name}: {desc}"for name,desc,_ in EXECS)
    parser.add_argument('mode', help="Mode of execution {\n\t" + help_str + "\n}")
    parser.add_argument('-f', '--file', help='Input file')
    parser.add_argument('-a', '--auxiliary', default="", help='Auxiliary file/directory')
    parser.add_argument('-o', '--output', default="", help='Output directory')
    parser.add_argument('--timeout', type=int, default=60000, help='Execution timeout (milliseconds)')
    parser.add_argument('--cvc5', default=os.environ.get("CVC5", "build/bin/cvc5"), help='cvc5 path')
    parser.add_argument('--threads', type=int, default=0, help='Number of threads')
    args = parser.parse_args()

    if args.mode not in EXEC_DICT:
        print(f"Unknown mode: {args.mode}")
        sys.exit(0)

    args.file = Path(args.file)
    args.output = Path(args.output)

    EXEC_DICT[args.mode](args)
