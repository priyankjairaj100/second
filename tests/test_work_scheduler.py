import unittest
from fractions import Fraction as F
from src.work_scheduler import Packet, weighted_race

class SchedulerTests(unittest.TestCase):
    def test_bound_and_cleanup_for_uneven_packets(self):
        for b, r in (([3, 2, 1], [1, 1]), ([1, 2], [3, 3, 3]), ([3]*9, [2]*7)):
            for alpha in (F(1, 3), F(1), F(3, 2)):
                committed, canceled = [], []
                def branch(xs):
                    it = iter(enumerate(xs))
                    def step():
                        i, cost = next(it)
                        return Packet(cost, i == len(xs)-1, 'canonical-result' if i == len(xs)-1 else None)
                    return step
                def cancel(name):
                    canceled.append(name)
                    return 4
                def commit(value):
                    committed.append(value)
                    return 5
                result = weighted_race(branch(b), branch(r), alpha=alpha, packet_limit=3, cancel=cancel, commit=commit)
                wb, wr = 1/(1+alpha), alpha/(1+alpha)
                self.assertLessEqual(result.total_work, min((sum(b)+3)/wb, (sum(r)+3)/wr)+9)
                self.assertEqual(committed, ['canonical-result'])
                self.assertEqual(canceled, ['repair' if result.winner == 'baseline' else 'baseline'])
    def test_invalid_packet_never_commits(self):
        committed=[]
        with self.assertRaises(ValueError):
            weighted_race(lambda:Packet(4, True, 1),lambda:Packet(1,True,1),alpha=F(1),packet_limit=3,cancel=lambda x:0,commit=lambda x:committed.append(x))
        self.assertEqual(committed,[])
