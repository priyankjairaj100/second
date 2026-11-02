"""Reconcile a saved failure snapshot without contacting Slurm or mutating it.

This is failure reporting, not success closure or authorization to launch. It
checks captured scheduler rows and the exact saved ledger bytes. Model/state
files are not reopened here; their earlier remote commitments remain separate.
"""
import datetime,hashlib,json,sys
from pathlib import Path
from research_v86.admission import require,terminal_disposition,carry_forward
from research_v83.accounting import cpu_time

def info(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(path):
    p=Path(path).absolute();require(p.is_file() and not any(x.is_symlink() for x in (p,*p.parents)), 'Regular nonsymbolic saved input required')
    require(p.stat().st_size<8*2**20,'Bounded failure metadata required');return p.read_bytes()

def review(snapshot,bindings):
    require(snapshot['queue']['exit']==snapshot['accounting']['exit']==0 and not snapshot['queue']['stdout'].strip(),'Captured terminal queue/accounting required')
    raw=snapshot['accounting']['stdout'];lines=raw.splitlines();header=lines[0].split('|')
    require(len(header)==len(set(header)),'Duplicate accounting columns')
    required={'JobIDRaw','State','ExitCode','Elapsed','TotalCPU','AllocCPUS','ReqMem','NodeList'}
    require(required<=set(header),'Missing original accounting columns')
    derived=[]
    for line in lines[1:]:
        values=line.split('|');require(len(values)==len(header),'Malformed saved scheduler row')
        row=dict(zip(header,values))
        elapsed,quantum=cpu_time(row['Elapsed']);require(elapsed%10**9==0,'Integral saved scheduler elapsed time required')
        derived.append('|'.join([row['JobIDRaw'],row['State'],row['ExitCode'],str(elapsed//10**9),row['TotalCPU'],row['AllocCPUS'],row['ReqMem'],row['NodeList']]))
    disposition=terminal_disposition('\n'.join(derived))
    root=snapshot['runs']['four-cell-service-v80-20261023-a'];raw_ledger=root['files']['budget/ledger.json'].encode()
    require(info(raw_ledger)==bindings['failed_v80_artifacts']['budget/ledger.json'],'Exact captured ledger bytes differ')
    require(root['sizes']['prepare/outputs/completion.json']==0 and bindings['failed_v80_artifacts']['prepare/outputs/completion.json']==info(b''),'Empty incomplete completion changed')
    budget=carry_forward(json.loads(raw_ledger))
    return dict(schema='saved-failure-reconciliation-v86',status='failure_snapshot_reconciled',
                snapshot_utc=snapshot['captured_utc'],disposition=disposition,budget=budget,
                scientific_success=False,launch_authorized=False,live_cluster_check=False,
                actual_model_state_reopened=False,old_ledger_bytes=info(raw_ledger),
                precise_runtime_exception_recovered=False)

def main(snapshot_path,bindings_path,output_path):
    a=read(snapshot_path);b=read(bindings_path);result=review(json.loads(a),json.loads(b))
    result.update(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  snapshot_commitment=info(a),bindings_commitment=info(b))
    with Path(output_path).open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
if __name__=='__main__':main(*sys.argv[1:])
