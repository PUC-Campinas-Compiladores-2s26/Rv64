"""Launcher com infraestrutura oficial e relatório por caso."""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
import pytest

class Report:
    def __init__(self): self.cases = {}; self.errors = []
    def pytest_collection_finish(self,session):
        self.cases.update({i.nodeid:'NOT_RUN' for i in session.items})
    def pytest_collectreport(self,report):
        if report.failed: self.errors.append(str(report.longrepr))
    def pytest_runtest_logreport(self,report):
        if report.when=='call' or report.failed:
            self.cases[report.nodeid]='PASS' if report.passed else 'FAIL'

def main():
    root=Path(__file__).resolve().parent
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--implementation',type=Path,default=root)
    p.add_argument('--closed',action='store_true')
    p.add_argument('--collect-only',action='store_true')
    p.add_argument('--report',type=Path,default=Path('test-results.json'))
    args=p.parse_args()
    sys.path.insert(0,str(args.implementation.resolve()))
    import load_previous
    for name in ('ir','executor','backend_api','emitter','toolchain'):
        spec=importlib.util.spec_from_file_location(name,root/(name+'.py'))
        module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    for name in ('rv_cfg','liveness','live_ranges','interference','regalloc'):
        spec=importlib.util.spec_from_file_location(name,args.implementation.resolve()/(name+'.py'))
        module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    paths=[str(root/'tests')]
    if args.closed: paths.append(str(root.parent/'tests'/'test_closed.py'))
    report=Report()
    result=pytest.main(['-q','--timeout=10',*paths]+(['--collect-only'] if args.collect_only else []),plugins=[report])
    args.report.write_text(json.dumps({'status':int(result),'python':sys.version,'cases':report.cases,'categories':{k:('infrastructure' if 'test_execution.py' in k else 'student') for k in report.cases},'collection_errors':report.errors,'hashes':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [*root.glob('*.py'),*args.implementation.resolve().glob('*.py')]}},indent=2))
    return int(result)
if __name__=='__main__': raise SystemExit(main())
