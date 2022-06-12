import pytest
from numbers import Number
from contract_util import *

global contract
contract = {
    "raise_on_contract_exception": True,
    "functions": [
        "no_params",
        "pos_param",
        "pos_param_ret",
        "bad_return",
        "kwarg_param",
    ],
    "no_params": {
        "params": {},
        "returns": lambda x: None,
        "allowable_calls": [],
        "max_runtime_seconds": 0,
        "allowed_callers": ["test_params"],
    },
    "pos_param": {
        "params": {"y": lambda x: x is not None},
        "returns": lambda x: x is None,
        "allowable_calls": [],
        "max_runtime_seconds": 0,
        "allowed_callers": ["test_params"],
    },
    "bad_return": {
        "params": {},
        "returns": lambda x: isinstance(x, str),
        "allowable_calls": [],
        "max_runtime_seconds": 0,
        "allowed_callers": ["test_bad_return"],
    },
    "allowable_imports": ["contract_util"],
    "global_allowed_calls": ["enforce_contract"],
}

### contract functions to be tested
@enforce_contract(contract)
def no_params():
    pass


@enforce_contract(contract)
def pos_param(x):
    pass


@enforce_contract(contract)
def bad_return():
    return True


###


def test_params():
    with pytest.raises(ContractException):
        no_params(1)

    # this is because the function declares `x` but the contract declares `y`
    with pytest.raises(ContractException):
        pos_param(1)

    # now we'll fix the above (change contract key to `x`)
    contract["pos_param"]["params"]["x"] = contract["pos_param"]["params"].pop("y")

    # function returns None but contract forbids this
    with pytest.raises(ContractException):
        pos_param(None)


def test_bad_return():
    # return value is expected to be str, but we get a bool, thus violating the contract
    with pytest.raises(ContractException):
        bad_return()
