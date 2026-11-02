"""Real sealed child/ledger fixture, synthetic artifact payloads; Linux only."""
import sys
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
from research_v80 import receipts,worker
from research_v80.io import write,json_read
from research_v61.postrun import Inputs
from src.experiment_inventory import source_hashes
from src.phase_budget import PhaseBudget,read_budget_snapshot
from src.run_store import canonical_json,digest
from src.worker_control import WorkerLimits,run_limited

class LinuxReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sys.platform!='linux':raise RuntimeError('Pinned Linux receipt gate required; no skip')

    def fixture(self,root):
        from src import worker_control
        repository=Path(worker_control.__file__).resolve().parents[1]
        p=dict(trial_order=['prepare'],trials=dict(prepare=dict(cpu_seconds=20,wall_seconds=30)),
            process_address_space_bytes=512*2**20,file_size_bytes=8*2**20,new_sources={})
        program_sha=digest(canonical_json(p));trial=root/'prepare';trial.mkdir()
        command=[sys.executable,'-B','-c','print("software-only sealed fixture")']
        identity=dict(protocol_sha256=program_sha,source_sha256=source_hashes(repository))
        budget=PhaseBudget(root/'budget',identity=identity,phase_cpu_seconds={'feasibility':22})
        import os
        result=run_limited(command,trial/'worker',WorkerLimits(cpu_seconds=20,wall_seconds=30,
            address_space_bytes=p['process_address_space_bytes'],file_size_bytes=p['file_size_bytes'],threads=1,
            affinity_cpus=(min(os.sched_getaffinity(0)),)),identity=dict(campaign_sha256=program_sha,trial='prepare'),
            cwd=repository,phase_budget=budget,phase='feasibility')
        write(trial/'transaction.json',dict(worker_outcome=result['outcome'],budget=budget.snapshot(),slurm_job_id='123'))
        write(trial/'plan.json',dict(trial='prepare',program=str(root/'program.json'),program_sha256=program_sha,output=str(trial/'outputs'),slurm_job_id='123'))
        artifacts={}
        for n in worker.expected_artifacts('prepare'):
            e=write(trial/'outputs'/n,b'fixture',raw=True);artifacts[n]=e
        write(trial/'outputs/completion.json',dict(schema='four-cell-complete-service-worker-v80',trial='prepare',
            status='complete',complete_model=True,program_sha256=program_sha,source_files_sha256=digest(canonical_json({})),
            slurm_job_id='123',shared_primal_kernel={'fixture':True},implementation={'fixture':True},artifacts=artifacts))
        snap=read_budget_snapshot(root/'budget',identity=identity,phase_cpu_seconds={'feasibility':22})
        return p,snap,repository,command

    def test_actual_sealed_receipt_and_mutated_cpu_debit(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();p,snap,repo,command=self.fixture(root)
            with patch.object(receipts,'ROOT',repo),patch.object(receipts,'command',return_value=command),patch.object(receipts,'verify_kernel'),patch.object(receipts,'verify_implementation'):
                results=receipts.verify_worker_receipts(root,p,Inputs(),snap)
                self.assertEqual(set(results),{'prepare'})
                import copy
                bad=copy.deepcopy(snap);next(iter(bad['attempts'].values()))['observed_cpu_ns']+=1
                with self.assertRaises(ValueError):receipts.verify_worker_receipts(root,p,Inputs(),bad)

    def test_actual_artifact_mutation_cannot_use_old_success(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();p,snap,repo,command=self.fixture(root)
            (root/'prepare/outputs/model.bin').write_bytes(b'changed')
            with patch.object(receipts,'ROOT',repo),patch.object(receipts,'command',return_value=command),patch.object(receipts,'verify_kernel'),patch.object(receipts,'verify_implementation'):
                with self.assertRaises(ValueError):receipts.verify_worker_receipts(root,p,Inputs(),snap)

if __name__=='__main__':unittest.main()
