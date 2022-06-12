import pytest
from numbers import Number
from contract_util import *
from time import sleep

global contract
contract = {
    "raise_on_contract_exception": True,
    "functions": ["one_sec"],
    "one_sec": {
        "params": {"stime": lambda x: isinstance(x, float)},
        "returns": lambda x: x is not None,
        "allowable_calls": ["sleep"],
        "max_runtime_seconds": 0.25,
        "allowed_callers": ["test_time"],
    },
    "allowable_imports": ["contract_util", "time"],
    "global_allowed_calls": ["enforce_contract"],
}

### contract functions to be tested
@enforce_contract(contract)
def one_sec(stime):
    sleep(stime)
    return stime


###


def test_time():
    # should be OK
    assert one_sec(0.2).returns == 0.2

    # too long!
    with pytest.raises(ContractException):
        one_sec(0.3)
