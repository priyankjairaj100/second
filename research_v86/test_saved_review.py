import copy,json,unittest
from research_v86.saved_review import review,info
from research_v86.test_admission import rows,ledger

def fixture():
    header='JobIDRaw|State|ExitCode|Elapsed|TotalCPU|AllocCPUS|ReqMem|NodeList\n'
    mapped=[]
    for row in rows():
        parts=row.split('|');seconds=int(parts[3]);parts[3]=f'{seconds//3600:02d}:{seconds//60%60:02d}:{seconds%60:02d}';mapped.append('|'.join(parts))
    old=json.dumps(ledger(),sort_keys=True,separators=(',',':'))
    snapshot=dict(captured_utc='fixture',queue=dict(exit=0,stdout=''),accounting=dict(exit=0,stdout=header+'\n'.join(mapped)),runs={'four-cell-service-v80-20261023-a':dict(files={'budget/ledger.json':old},sizes={'prepare/outputs/completion.json':0})})
    bindings=dict(failed_v80_artifacts={'budget/ledger.json':info(old.encode()),'prepare/outputs/completion.json':info(b'')})
    return snapshot,bindings
class SavedReview(unittest.TestCase):
    def test_reconciles_failure_without_promotion_or_mutation(self):
        snapshot,bindings=fixture();before=copy.deepcopy(snapshot);result=review(snapshot,bindings)
        self.assertEqual(snapshot,before);self.assertEqual(result['status'],'failure_snapshot_reconciled')
        self.assertFalse(result['scientific_success']);self.assertFalse(result['launch_authorized']);self.assertFalse(result['live_cluster_check'])
    def test_semantically_equal_but_changed_ledger_bytes_refuse(self):
        snapshot,bindings=fixture();snapshot['runs']['four-cell-service-v80-20261023-a']['files']['budget/ledger.json']+='\n'
        with self.assertRaisesRegex(ValueError,'ledger bytes'):review(snapshot,bindings)
    def test_nonempty_completion_and_nonterminal_queue_refuse(self):
        snapshot,bindings=fixture();snapshot['runs']['four-cell-service-v80-20261023-a']['sizes']['prepare/outputs/completion.json']=2
        with self.assertRaisesRegex(ValueError,'completion'):review(snapshot,bindings)
        snapshot,bindings=fixture();snapshot['queue']['stdout']='15905|RUNNING'
        with self.assertRaisesRegex(ValueError,'queue'):review(snapshot,bindings)
if __name__=='__main__':unittest.main()
