from typing import Callable

schema_globals = {
    "raise_on_contract_exception": bool,
    "allowable_imports": list,
    "global_allowed_calls": list,
    "functions": list,
}

schema_functions = {
    "params": dict,
    "returns": Callable,
    "allowable_calls": list,
    "max_runtime_seconds": float,
    "allowed_callers": list,
}
