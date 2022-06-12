from contract_util import *
from calc_contract import c as contract
from sys import argv


@enforce_contract(contract)
def calculate(calculation):
    return eval(calculation)


if __name__ == "__main__":
    if len(argv) > 1:
        val = calculate("".join(argv[1:]))
        if not val.ok:
            print(f"Error: {val.exception}")
        print(val.returns)
