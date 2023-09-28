from pathlib import Path
import re
import unittest
from typing import Optional

import pandas

def automatic_read_rules(path):
    """
    Read the BV_Rewrites spreadsheet
    """
    df = pandas.read_csv(path, keep_default_na=False)
    return df["RARE"]

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
    with open(args.file, "r") as f:
        lines = [line.rstrip() for line in f]
    rules = read_rules(lines)
    rules = sorted(rules)
    for rule in rules:
        print(rule)


def routine_read_sheets(args):
    """
    Read the BV_Rewrites spreadsheet
    """
    rules = automatic_read_rules(args.file)
    rules = sorted(rule for rule in rules if rule != "")
    for rule in rules:
        print(rule)


def process_line_of_mkdslrulecounts(l) -> Optional[tuple[str, int]]:
    if ',' not in l:
        return None
    l = l.rstrip().removeprefix("[92m+")
    name, num = l.split(',')
    return name, int(num)


def routine_read_counts(args):
    """
    Read the BV_Rewrites spreadsheet
    """
    df_bv = pandas.read_csv(args.auxiliary, keep_default_na=False)
    print("Columns: ", df_bv.columns)
    with open(args.file, "r") as f:
        counts = [x for x in [process_line_of_mkdslrulecounts(line) for line in f] if x]

    counts = { name: num for name,num in counts }

    df_out = df_bv["RARE"].map(lambda name: counts.get(name, "")).to_frame()
    print(df_out.to_csv(index=False))



class TestTabulate(unittest.TestCase):

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



if __name__ == '__main__':

    import sys
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
        ('read-rules', "Read rules from -f src/theory/bv/rewrites and print them", routine_read_rules),
        ('read-sheets', "Read rules from -f BV Rewrites and print them", routine_read_sheets),
        ('read-counts', "Read rules from mkdslrulecounts, use -a for the BV-Rewrites table, and output a column", routine_read_counts),
    ]
    EXEC_DICT = { name: func for name, _, func in EXECS }
    help_str = '\n\t'.join(f"{name}: {desc}"for name,desc,_ in EXECS)
    parser.add_argument('mode', help="Mode of execution {\n\t" + help_str + "\n}")
    parser.add_argument('-f', '--file', help='Input file')
    parser.add_argument('-a', '--auxiliary', default="", help='Auxiliary file/directory')
    args = parser.parse_args()

    if args.mode not in EXEC_DICT:
        print(f"Unknown mode: {args.mode}")
        sys.exit(0)

    args.file = Path(args.file)

    EXEC_DICT[args.mode](args)
