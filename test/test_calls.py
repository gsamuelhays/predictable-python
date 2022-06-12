import pytest
from numbers import Number
from contract_util import *

global contract
contract = {
    "raise_on_contract_exception": True,
    "functions": ["caller", "called"],
    "caller": {
        "params": {},
        "returns": lambda x: True,
        "allowable_calls": [],
        "max_runtime_seconds": 0,
        "allowed_callers": [],
    },
    "called": {
        "params": {},
        "returns": lambda x: True,
        "allowable_calls": [],
        "max_runtime_seconds": 0,
        "allowed_callers": ["test_callee"],
    },
    "allowable_imports": ["contract_util"],
    "global_allowed_calls": ["enforce_contract"],
}

### contract functions to be tested
@enforce_contract(contract)
def called():
    return True


@enforce_contract(contract)
def caller():
    return called().returns


def missing_function():
    pass


@enforce_contract(contract)
def missing():
    missing_function()


###


def test_caller():
    # `called`` is not allowed to be called here.
    with pytest.raises(ContractException):
        called()

    # disable exception raising and try again
    contract["raise_on_contract_exception"] = False
    c = called()
    assert c.ok is False
    assert c.exception is not None

    # reset the contract value
    contract["raise_on_contract_exception"] = True

    # add this function to the contract and test again
    contract["called"]["allowed_callers"].append("test_caller")
    assert called().returns is True


def test_callee():
    # `caller`` is not allowed to call `called`
    with pytest.raises(ContractException):
        caller()

    # ensure we (`test_callee`) can call `caller`
    contract["caller"]["allowed_callers"].append("test_callee")
    # make sure `called` can be called by `caller`
    contract["called"]["allowed_callers"].append("caller")
    # make sure `caller` can call `called`
    contract["caller"]["allowable_calls"].append("called")

    assert caller().returns is True


def test_contract_properties():
    contract["functions"].remove("called")
    with pytest.raises(ContractException):
        called()
    contract["functions"].append("called")

    # test missing function name in functions key
    with pytest.raises(ContractException):
        missing()

    # add name to key, should fail for missing def.
    contract["functions"].append("missing")
    with pytest.raises(ContractException):
        missing()
