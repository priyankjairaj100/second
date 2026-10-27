"""Actual generated receipt files test historical cost binding and all-cell output."""
import contextlib,copy,io,json,tempfile,unittest
from pathlib import Path
from reporting_v113.reduce import (main,identity,historical_hosts,preparation_times,
                                  PARENT,PARENT_SHA,RUN,PROFILES,CELLS,name)
from reporting_v113.test_reduce import fixture


def generate(base):
    t,p,a,b,raw=fixture()
    def put(relative,value,bound=True):
        blob=json.dumps(value,sort_keys=True,separators=(',',':')).encode()
        path=base/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
        if bound:t['inputs'][str(RUN/relative)]=identity(blob)
        return identity(blob)
    put('program.json',p)
    gate=dict(parent_program_sha256=PARENT_SHA,original_receipts_not_modified=True,inputs={})
    for i,profile in enumerate(PROFILES):
        host=dict(status='complete',error=None,program_sha256=PARENT_SHA,operation=profile+'/prepare',arguments=[],
                  outcome=dict(exit_code=0,failure=None),elapsed_ns=9000+i)
        e=put('historical/'+profile+'-prepare-host.json',host,False)
        gate['inputs'][str(PARENT/(profile+'--prepare-host.json'))]=e
    put('gates/v104-failed-screen-v110.json',gate)
    a['costs']={'trials':{}}
    for profile in PROFILES:
        a['evidence'][profile]['storage']={}
        for cell,arm in CELLS.items():
            a['evidence'][profile]['storage'][cell]=[]
            for step in (1,2):
                trial=f'{profile}/{cell}-{step}'
                request=dict(arm=arm,request_elapsed_ns=1000,live_state_bytes=100,
                    retained_ids=list(range(p['retained_counts'][step-1])),timing=dict(
                    stages=[dict(stage_id=str(i),elapsed_ns=1,fallback=False) for i in range(p['stage_counts'][profile])],
                    source_extraction_ns=0,neural_stage_record_pairs=0,encoding_and_gram_ns=0,
                    predecessor_validation_ns=10,serialization_ns=10,disposal_ns=10))
                put(trial+'/outputs/completion.json',dict(status='complete',slurm_job_id=t['costs'][trial]['job_id'],request=request,max_rss_kib=123))
                put(name(trial)+'-host.json',dict(status='complete',elapsed_ns=2000))
                a['costs']['trials'][trial]=dict(complete_host_elapsed_ns=2000,request_elapsed_ns=1000)
                a['evidence'][profile]['storage'][cell].append(dict(live_state_bytes=100,checkpoint_inclusive_bytes=200))
    b['costs']=copy.deepcopy(a['costs'])
    primary=put('primary-audit.json',a);b['evidence']['primary_sha256']=primary['sha256'];put('supplemental-audit.json',b)
    terminal=base/'terminal.json';terminal.write_text(json.dumps(t,sort_keys=True))
    return terminal


class Reuse(unittest.TestCase):
    def test_both_original_preparation_costs_are_required_and_positive(self):
        for change in ('missing','zero','wrong_operation','wrong_program'):
            hosts={p:dict(status='complete',error=None,program_sha256=PARENT_SHA,operation=p+'/prepare',arguments=[],outcome=dict(exit_code=0,failure=None),elapsed_ns=100) for p in PROFILES}
            if change=='missing':hosts.pop('gpt2')
            elif change=='zero':hosts['gpt2']['elapsed_ns']=0
            elif change=='wrong_operation':hosts['gpt2']['operation']='distilgpt2/prepare'
            else:hosts['gpt2']['program_sha256']='0'*64
            with self.assertRaises(ValueError):preparation_times(hosts)

    def test_full_saved_file_reduction_keeps_all_cells_and_historical_cost(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);terminal=generate(base);out=base/'reduction.json'
            with contextlib.redirect_stdout(io.StringIO()):main(terminal,base,out)
            r=json.loads(out.read_bytes());self.assertEqual(len(r['rows']),16)
            self.assertEqual(set(r['comparisons']),set(PROFILES))
            self.assertEqual(set(r['reused_preparation_host_ns']),set(PROFILES))
            self.assertTrue(all(v>0 for v in r['reused_preparation_host_ns'].values()))
            self.assertTrue(r['preparation_cost_is_historical_not_zero'])
            self.assertFalse(r['preparation_reexecuted']);self.assertFalse(r['stable_latency_established'])
            self.assertEqual(r['cumulative_screen_numerical_seconds'],6322)

    def test_changed_historical_receipt_rejects_before_output(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);terminal=generate(base);out=base/'reduction.json'
            p=base/'historical/gpt2-prepare-host.json';q=json.loads(p.read_bytes());q['elapsed_ns']=1;p.write_text(json.dumps(q))
            with self.assertRaisesRegex(ValueError,'Changed original preparation cost'):main(terminal,base,out)
            self.assertFalse(out.exists())

    def test_wrong_historical_gate_is_rejected(self):
        for gate in (dict(parent_program_sha256='0'*64,original_receipts_not_modified=True),
                     dict(parent_program_sha256=PARENT_SHA,original_receipts_not_modified=False)):
            with self.assertRaises(ValueError):historical_hosts(gate)

if __name__=='__main__':unittest.main()
