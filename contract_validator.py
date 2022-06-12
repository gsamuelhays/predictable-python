import ast
import argparse
import logging as log
import importlib
from typing import Tuple

log.basicConfig(level=log.DEBUG)


class ContractValidationException(Exception):
    pass


class ASTVisitor(ast.NodeVisitor):
    """
    A class responsible for introspecting the code to determine
    if violations of the contract have occurred.
    """

    call_violation = []
    import_violation = []
    undeclared_func = []
    undefined_func = []
    undecorated_class = []
    call_graph = {}
    contract = None
    tree = None
    error_count = 0
    current_func = None
    debug = False

    def __init__(
        self,
        contract: dict,
        file_contents: str,
        debug: bool = False,
    ):
        self.contract = contract
        self.debug = debug
        self.tree = ast.parse(file_contents)

    def visit_Import(self, node):
        """
        Visit all import statements to check contract violations.
        """

        if self.debug:
            log.debug(f"[DEBUG] visit_Import\n{ast.dump(node, indent=2)}")
        for n in node.names:
            if n.name not in self.contract["allowable_imports"]:
                self.error_count += 1
                self.import_violation.append((n.lineno, n.name))

    def visit_ImportFrom(self, node):
        """
        Visit all `from x import y` statements to check contract violations.
        """
        if self.debug:
            log.debug(f"visit_ImportFrom:\n{ast.dump(node, indent=2)}")
        if node.module not in self.contract["allowable_imports"]:
            self.error_count += 1
            self.import_violation.append((node.lineno, node.module))

    def visit_FunctionDef(self, node):
        """
        Visit all function definitions to check contract violations.
        """
        if self.debug:
            log.debug(f"visit_FunctionDef:\n{ast.dump(node, indent=2)}")

        # Check if the node name is in our contract's function list...
        if node.name in self.contract.get("functions", []):

            # build a graph of all calls...
            if node.name not in self.call_graph:
                self.call_graph[node.name] = list()
            try:
                # construct a list of all allowable calls from the contract
                allowed_calls = self.contract.get(
                    "global_allowed_calls", []
                ) + self.contract[node.name].get("allowable_calls", [])

                # walk the the tree in functions to find calls and imports
                for cn in ast.walk(node):
                    if type(cn) == ast.Import:
                        self.visit_Import(cn)
                    if type(cn) == ast.ImportFrom:
                        self.visit_ImportFrom(cn)
                    if type(cn) == ast.Call:
                        called = (
                            cn.func.id if hasattr(cn.func, "id") else cn.func.value.id
                        )
                        if called not in allowed_calls:
                            self.call_violation.append((cn.lineno, called, node.name))
                            self.error_count += 1
                        else:
                            if called not in self.call_graph[node.name]:
                                self.call_graph[node.name].append((called, True))

            except KeyError as ke:
                self.error_count += 1
                self.undefined_func.append(node.name)

        # if not, this is an error...
        else:
            self.error_count += 1
            self.undeclared_func.append((node.lineno, node.name))

    def visit_ClassDef(self, node):
        if self.debug:
            log.debug(f"visit_ClassDef:\n{ast.dump(node, indent=2)}")
        if "enforce_contract" not in [x.func.id for x in node.decorator_list]:
            self.error_count += 1
            self.undecorated_class.append((node.lineno, node.name))

    def check(self) -> None:
        """
        This method prints the various identified violations.
        """
        self.visit(self.tree)

        if self.call_violation:
            print("Call violations\n---------------")
            for l, v, c in self.call_violation:
                print(
                    f"Error (Line: {l}): Function `{v}` called in `{c}` but not allowed in contract."
                )
            print("\n")

        if self.import_violation:
            print("Import violations\n-----------------")
            for l, v in self.import_violation:
                print(f"Error (Line: {l}): `{v}` Imported but not allowed in contract.")
            print("\n")

        if self.undeclared_func:
            print("Undeclared function\n---------------")
            for l, v in self.undeclared_func:
                print(
                    f"Error (Line: {l}): Function `{v}` defined but not declared in contract."
                )
            print("\n")

        if self.undefined_func:
            print("Undefined function\n---------------")
            for l in self.undefined_func:
                print(
                    f"Error: Function `{l}` declared in contract global `functions`, but undefined"
                )
            print("\n")

        if self.undecorated_class:
            print("Undecorated Class\n---------------")
            for l, v in self.undecorated_class:
                print(f"Error (Line {l}): Class `{v}` defined but undecorated")
            print("\n")

        print(f"Total Violations: {self.error_count}")


def load_file(filename: str) -> Tuple[bool, str]:
    """
    Loads the file for parsing.
    """
    try:
        with open(filename, "r") as f:
            content = f.read()
            return True, content
    except:
        return False, None


def verify_contract_schema(contract: dict, schema="v1_schema"):
    """
    This function will take in a contract dictionary and return
    True if the contract is valid, False otherwise.
    """
    try:
        schema = importlib.import_module(schema)
    except Exception as e:
        raise IOError(f"verify_contract_schema(): e = {e}")

    # check global keys
    for k, v in schema.schema_globals.items():
        if k not in contract or not isinstance(contract[k], v):
            raise ContractValidationException(
                f"Either `{k}` not in contract or not instance of `{v}`."
            )

    # check functions
    for f in contract["functions"]:
        if f not in contract:
            raise ContractValidationException(
                f"The function `{f}` declared in functions but not defined."
            )
        for fkwn, fkwv in schema.schema_functions.items():
            if fkwn not in contract[f] or not isinstance(contract[f][fkwn], fkwv):
                raise ContractValidationException(
                    f"Either `{fkwn}` not in contract['{f}'] or not instance of `{fkwv}`"
                )


def main(args):
    contract = None
    try:
        c = importlib.import_module(args.contract)
        contract = c.c
        verify_contract_schema(contract)
    except ContractValidationException as ce:
        log.error(f"Unable to validate contract. Error: {ce}")
        exit()
    except Exception as e:
        log.exception(f"Unable to load contract. Error: {e}")
        exit()

    if not args.file:
        log.info("Contract passes schema validation.")
        exit(0)

    ok, file = load_file(args.file)
    if not ok:
        log.error("Unable to read the file!")
        return -1

    visitor = ASTVisitor(contract, file, args.debug)
    visitor.check()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ensure program matches contract")
    parser.add_argument(
        "-f",
        "--file",
        help="Validate module matches contract",
        required=False,
    )
    parser.add_argument(
        "-c",
        "--contract",
        help="Contract against which to validate file (omit the file extension)",
        default="contract",
        required=False,
    )
    parser.add_argument(
        "-d",
        "--debug",
        help="Add debug information to output",
        action="store_true",
        required=False,
    )
    args = parser.parse_args()
    main(args)
