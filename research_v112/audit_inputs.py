"""Binary-safe full-state audit reads under the original artifact/JSON bounds."""
from pathlib import Path
from research_v61.postrun import Inputs as BinaryInputs
from research_v80.io import regular,require
from research_v112.config import ROOT

class Inputs(BinaryInputs):
    def read(self,path,expected=None,retain=True,maximum=2**30):
        path=regular(path)
        require(path.is_relative_to(ROOT),'Audit input outside registered project')
        require(type(maximum) is int and 0<=maximum<=2**30,'Original one-GiB artifact bound required')
        result=super().read(path,retain=retain,maximum=maximum)
        require(expected is None or self.files[str(path)]==expected,'Audit input commitment differs')
        return result
