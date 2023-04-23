#!/usr/bin/env python3

from pathlib import Path
import re
import unittest
from typing import Optional

# Read Rules

def read_rules(lines):
    # matches strings like this with negative lookahead
    #
    #   " rule-name-123 "
    regex = re.compile(r"(?<= )[A-Za-z0-9\-]+(?=\b)")

    DEFINE_NAMES = [
        'define-cond-rule*',
        'define-cond-rule',
        'define-rule*',
        'define-rule',
    ]

    def search_line(line):
        if any(line.startswith(f"({name}") for name in DEFINE_NAMES):
            search = regex.search(line)
            if search:
                return [search.group(0)]
            else:
                return []
        else:
            return []
    rules = [rule for line in lines
             for rule in search_line(line)]
    return rules

def routine_read_rules(args):
    with open(args.f, "r") as f:
        lines = [line.rstrip() for line in f]
    rules = read_rules(lines)
    for rule in rules:
        print(rule)


def trace_worker(args):
    import subprocess
    import os
    os.nice(10)

    command_stem, pathIn, pathOut = args
    command = command_stem + [Path(pathIn)]
    pathOut.parent.mkdir(exist_ok=True, parents=True)
    trace = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           preexec_fn=lambda: os.nice(10))

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
    globInput = [str(path.relative_to(args.f))
                 for path in args.f.glob("**/*.smt2")]

    fileList = [path for path in globInput if path not in set(globOutput)]
    print(f"{len(fileList)}/{len(globInput)} input files skipped")

    import tqdm
    import multiprocessing

    threads = multiprocessing.cpu_count() if args.threads == 0 else args.threads

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
            (command_stem, args.f / path, args.output / path)
            for path in fileList
        ]
        with multiprocessing.Pool(threads) as pool:
            iterant = pool.imap_unordered(trace_worker, feedstock)
            results = list(tqdm.tqdm(iterant, total=len(fileList)))
    else:
        feedstock = [
            (command_stem, args.f / path, args.output / path)
            for path in fileList
        ]
        results = [
            trace_worker(a)
            for a in tqdm.tqdm(feedstock)
        ]



# Matches "all_simplify :args (" in front and matches a space after.
# The space is there to eliminate all "evaluate" calls!
REGEX_ALETHE_RULE = re.compile(r"(?<=\:rule all_simplify \:args \()[A-Za-z0-9\-]+(?= )")

def count_worker(args):
    import subprocess
    import os
    os.nice(10)

    KEY = ':rule all_simplify :args ('
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
    fileList = [path for path in args.f.glob("**/*")]

    import tqdm
    import multiprocessing
    threads = multiprocessing.cpu_count() if args.threads == 0 else args.threads

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
    os.nice(10)

    command_stem, pathIn, pathOut = args
    command = command_stem + [Path(pathIn)]
    pathOut.parent.mkdir(exist_ok=True, parents=True)
    trace = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           preexec_fn=lambda: os.nice(10))

    if trace.returncode == 0:
        with open(str(pathOut) + '.out', "w") as f:
            for line in trace.stdout.decode('utf-8').split('\r\n'):
                f.write(line)
    else:
        with open(str(pathOut) + '.err', "w") as f:
            for line in trace.stderr.decode('utf-8').split('\r\n'):
                f.write(line)
            f.write(str(trace.returncode))


def routine_make_regression(args):
    """
    inputs: ../*.smt2
    outputs: ../*.smt2.out or .err depending on the output
    """
    # Create the output directory
    args.output = Path(args.output)
    args.output.mkdir(exist_ok=True, parents=True)

    print("Unfinished")
    return

class TestRules(unittest.TestCase):

    def test_read_rules(self):
        self.assertEqual(read_rules([
            '(define-rule bv-eq-sym-1 ((x ?BitVec) (y ?BitVec))',
            '  (= x y) (= y x))'
        ]), ['bv-eq-sym-1'])
        self.assertEqual(read_rules([
            '(define-rule* bv-or-concat-pullup',
        ]), ['bv-or-concat-pullup'])
        self.assertEqual(read_rules([
            '(define-cond-rule* bv-rec-rec-rec-1 ;comment',
            '  (= x y) (= y x))'
        ]), ['bv-rec-rec-rec-1'])

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

    import sys
    if len(sys.argv) == 1:
        unittest.main()
        sys.exit(0)

    import argparse

    parser = argparse.ArgumentParser(
                    prog='CVC5 Tester',
                    description='Executes CVC5',
                    epilog='proof-new')

    EXEC_DICT = {
        'rules': routine_read_rules,
        'trace': routine_trace,
        'count': routine_count,
        'make_regression': routine_make_regression, # make a regression test
    }
    execHelpStr = ', '.join(EXEC_DICT.keys())
    parser.add_argument('mode', help="Mode of execution {" + execHelpStr + "}")
    parser.add_argument('-f', help='Input file')
    parser.add_argument('-o', '--output', default="", help='Input file')
    parser.add_argument('--timeout', type=int, default=60000, help='Execution timeout (milliseconds)')
    parser.add_argument('--cvc5', default="build/bin/cvc5", help='cvc5 path')
    parser.add_argument('--threads', type=int, default=0, help='Number of threads')
    args = parser.parse_args()

    if args.mode not in EXEC_DICT:
        print(f"Unknown mode: {args.mode}")
        sys.exit(0)

    args.f = Path(args.f)
    args.output = Path(args.output)

    EXEC_DICT[args.mode](args)
