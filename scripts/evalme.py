#!/bin/env python

import os
import argparse

here=os.path.dirname(os.path.realpath(__file__))
lCorkRoot=os.path.dirname(here)

lScriptsDir=os.path.join(lCorkRoot, 'scripts')
lPythonDir=os.path.join(lCorkRoot, 'python')

parser = argparse.ArgumentParser()
parser.add_argument('shell', choices=['sh','csh'])
args = parser.parse_args()

if args.shell == 'sh':
    print 'export PATH="%s:$PATH"' % lScriptsDir
    print 'export PYTHONPATH="%s:$PYTHONPATH"' % lPythonDir
elif args.shell == 'csh':
    print 'setenv PATH "%s:$PATH"' % lScriptsDir
    print 'setenv PYTHONPATH "%s:$PYTHONPATH"' % lPythonDir
