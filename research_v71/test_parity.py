"""Generated loss values only; no model or corpus inference."""
import copy,math,unittest
from research_v71 import parity as p
IDS=['a','b','c','d']
def table():return {m:[dict(id=i,predictions=127,nll_sum=508.,mean_nll=4.) for i in IDS] for m in p.MODELS}

class ParityTests(unittest.TestCase):
    def test_all_twenty_four_pairs_and_fixed_tolerance_are_checked(self):
        cpu=table();gpu=copy.deepcopy(cpu);gpu['candidate_6'][-1]['nll_sum']+=127*.5e-8
        gpu['candidate_6'][-1]['mean_nll']=gpu['candidate_6'][-1]['nll_sum']/127
        r=p.compare(gpu,cpu,IDS);self.assertTrue(r['passed']);self.assertEqual(len(r['checks']),24)
        self.assertFalse(r['actual_parameter_artifact_binding_performed'])

    def test_one_late_model_article_failure_cannot_be_hidden_by_first_batch(self):
        cpu=table();gpu=copy.deepcopy(cpu);gpu['sequential_6'][-1]['nll_sum']+=127*2e-8
        gpu['sequential_6'][-1]['mean_nll']=gpu['sequential_6'][-1]['nll_sum']/127
        r=p.compare(gpu,cpu,IDS);self.assertFalse(r['passed'])
        self.assertEqual(sum(not c['passed'] for c in r['checks']),1)

    def test_incomplete_duplicate_nonfinite_or_inconsistent_rows_refuse(self):
        cases=[]
        a=table();a.pop('nearest');cases.append(a)
        a=table();a['original'].pop();cases.append(a)
        a=table();a['original'][1]['id']='a';cases.append(a)
        for key,value in [('nll_sum',math.nan),('mean_nll',3.),('predictions',126),('nll_sum',True)]:
            a=table();a['candidate_12'][0][key]=value;cases.append(a)
        for x in cases:
            with self.assertRaises(ValueError):p.compare(x,table(),IDS)
        with self.assertRaises(ValueError):p.compare(table(),table(),IDS[:3])


if __name__=='__main__':unittest.main()
