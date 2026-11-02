"""Pure failure fixtures; these do not qualify or launch a recovery."""
import copy,unittest
from research_v86 import admission as a

def ledger():
    return dict(schema='phase-cpu-ledger-v1',binding=dict(phase_cpu_seconds={'feasibility':108020},identity={'protocol_sha256':a.OLD_PROGRAM}),attempts={a.OLD_ATTEMPT:dict(charged_cpu_seconds=12602,observed_cpu_ns=None,phase='feasibility',reserved_cpu_seconds=12602,state='reserved')})
def rows():
    result=[]
    for job,(state,exitcode) in a.EXPECTED.items():
        ran=state!='CANCELLED';cpu={'15904':'00:11.560','15905':'01:46:42','15917':'00:00.850'}.get(job,'00:00:00')
        result.append('|'.join([job,state,exitcode,str(a.EXPECTED_ELAPSED.get(job,0)),cpu,'1' if ran else '0','16G','csis.mn1' if ran else 'None assigned']))
    return result
class RecoveryAdmission(unittest.TestCase):
    def test_full_terminal_census_is_failure_not_science(self):
        result=a.terminal_disposition('\n'.join(rows()))
        self.assertEqual(len(result['allocations']),19);self.assertFalse(result['scientific_success'])
        self.assertEqual(result['scheduler_cpu_ns'],6414410000000)
    def test_nonterminal_missing_duplicate_or_unknown_job_refuses(self):
        examples=[rows()[:-1],rows()+[rows()[0]],rows()+['19999|COMPLETED|0:0|1|00:00:01|1|16G|csis.mn1'],[r.replace('15905|FAILED','15905|RUNNING') for r in rows()]]
        for example in examples:
            with self.subTest(example=example[-1]):
                with self.assertRaises(ValueError):a.terminal_disposition('\n'.join(example))
    def test_cancelled_job_cannot_hide_an_actual_allocation(self):
        bad=[r.replace('15906|CANCELLED|0:0|0|00:00:00|0','15906|CANCELLED|0:0|0|00:00:00|1') for r in rows()]
        with self.assertRaises(ValueError):a.terminal_disposition('\n'.join(bad))
    def test_complete_old_charge_is_carried_without_mutation(self):
        original=ledger();before=copy.deepcopy(original);result=a.carry_forward(original)
        self.assertEqual(original,before);self.assertEqual(result['combined_numerical_reservation'],120622)
        self.assertEqual(result['remaining_numerical_reservation_margin'],2);self.assertEqual(result['combined_controller_reservation'],6622)
    def test_lower_scheduler_cost_cannot_refund_or_settle_old_ledger(self):
        for patch in [dict(charged_cpu_seconds=6402),dict(observed_cpu_ns=6402*10**9),dict(state='settled')]:
            original=ledger();original['attempts'][a.OLD_ATTEMPT].update(patch)
            with self.assertRaises(ValueError):a.carry_forward(original)
    def test_another_unknown_attempt_or_changed_binding_refuses(self):
        original=ledger();original['attempts']['new']=dict(original['attempts'][a.OLD_ATTEMPT])
        with self.assertRaises(ValueError):a.carry_forward(original)
        original=ledger();original['binding']['identity']['protocol_sha256']='0'*64
        with self.assertRaises(ValueError):a.carry_forward(original)
if __name__=='__main__':unittest.main()
