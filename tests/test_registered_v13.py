import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import run_registered_v13 as driver


class RegisteredDriverTests(unittest.TestCase):
    def test_reserved_placeholder_is_not_a_finished_failure(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(driver,'ARCHIVE',Path(directory)):
            attempt=Path(directory)/'test';(attempt/'worker').mkdir(parents=True);(attempt/'phase-cpu-budget').mkdir()
            ledger=attempt/'phase-cpu-budget/ledger.json';receipt=attempt/'worker/result.json'
            ledger.write_text(json.dumps({'attempts':{'x':{'state':'reserved'}}}))
            receipt.write_text(json.dumps({'outcome':{'status':'failed','kind':'launch_failed'},'budget_debit':{'state':'reserved'}}))
            self.assertFalse(driver.settled('test'));self.assertFalse(driver.completed('test'))
            ledger.write_text(json.dumps({'attempts':{'x':{'state':'settled'}}}))
            self.assertFalse(driver.settled('test'))
            receipt.write_text(json.dumps({'outcome':{'status':'complete'},'budget_debit':{'state':'settled'}}))
            self.assertTrue(driver.settled('test'));self.assertTrue(driver.completed('test'))
            receipt.write_text(json.dumps({'outcome':{'status':'failed'},'budget_debit':{'state':'settled'}}))
            self.assertTrue(driver.settled('test'));self.assertFalse(driver.completed('test'))
