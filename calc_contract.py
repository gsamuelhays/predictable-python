from numbers import Number
import re

c = {
    "raise_on_contract_exception": True,
    "functions": ["calculate"],
    "calculate": {
        "params": {
            "calculation": lambda x: isinstance(x, str)
            and re.match(r"^(?:\s*(?:\d+\.?\d*?|[\-\+\/\*\(\)]{1})\s*)*$", x)
            # and re.match(r"^(\s+)?\d+(?:(\s+)?([\-\+\/\*]{1}(\s+)?\d+(\s+)?))+$", x)
        },
        "returns": lambda x: isinstance(x, Number),
        "allowable_calls": ["eval"],
        "max_runtime_seconds": 2.0,
        "allowed_callers": ["<module>"],
    },
    "allowable_imports": ["sys", "contract_util", "calc_contract"],
    "global_allowed_calls": ["enforce_contract"],
}
