import ast
import inspect
from multiprocessing import Process, Queue


class ContractException(Exception):
    pass


class CheckFunctionCalls(ast.NodeVisitor):
    """
    Simple class to looks for function calls.
    """

    def __init__(self):
        self.calls = []

    def visit_Call(self, node):
        self.calls.append(node.func.id)


class Return:
    """
    Class returned from enforce_contract'd functions.

    This object includes an `ok` property which, if True, means that the
    function's return value may be found in the `ret` property.

    If the `ok` property is False, then the `exception` property may be
    examined to determine the cause.
    """

    def __init__(self, contract_exception=None, ret_val=None):
        self.ce = contract_exception
        self.ret = ret_val

    @property
    def exception(self):
        """
        Returns the exception if one exists.
        """
        return self.ce

    @property
    def ok(self):
        """
        Returns True if the decorated function was OK (did not
        throw an exception nor violate the contract) else False.
        """
        return True if not self.ce else False

    @property
    def returns(self):
        """
        Returns the protected function's return value (if one exists).
        """
        return self.ret


def enforce_contract(contract: dict):
    """
    This decorator enforces the specified contract for the execution of a specific function.

    Args:
        contract (dict): Contract to be enforced
    """

    def dec(fn):
        def wrapped(*args, **kwargs):

            # we'll check the calls at runtime and
            # populate a list of
            try:
                function_calls = CheckFunctionCalls()
                function_calls.visit(ast.parse(inspect.getsource(fn)))

                function_name = fn.__name__
                function_caller = inspect.stack()[1].function

                # validate calls...
                for call in function_calls.calls:
                    if function_name not in contract:
                        raise ContractException(
                            f"Function `{function_name}` not declared in contract."
                        )

                    if (
                        call not in contract[function_name]["allowable_calls"]
                        and call not in contract["global_allowed_calls"]
                    ):
                        raise ContractException(
                            f"Function `{function_name}` trying to call `{call}` which is not allowed by the contract."
                        )
                if function_name not in contract["functions"]:
                    raise ContractException("Function not specified in contract.")

                # validate callers
                if function_caller not in contract[function_name]["allowed_callers"]:
                    raise ContractException(
                        f"Caller `{function_caller}` not allowed to call this function (`{function_name}`)"
                    )

                # dict of args and kwargs bound to names
                try:
                    sig = inspect.signature(fn).bind(*args, **kwargs)
                except:
                    raise ContractException(f"Unable to bind passed-in parameters")

                arguments = sig.arguments

                try:
                    for arg, val in arguments.items():
                        if arg not in contract[function_name]["params"]:
                            raise ContractException(
                                f"Parameter `{arg}` used but not defined in contract."
                            )
                except Exception as e:
                    raise ContractException(
                        f" An error validation parameters. Error: {e}"
                    )

                # ensure passed-in params meet the contract specification
                for param, validator_func in contract[function_name]["params"].items():
                    val = arguments[param]
                    if not validator_func(val):
                        raise ContractException(
                            f"Parameter `{param}` out of contract specification."
                        )

                # deal with max_runtime is used
                runtime = contract[function_name]["max_runtime_seconds"]
                if runtime > 0:
                    q = Queue()
                    eq = Queue()

                    def timedfn(fn, *args, **kwargs):
                        """
                        Uses a Queue to snag return value from function
                        """
                        try:
                            r = fn(*args, **kwargs)
                            q.put(r)
                        except Exception as e:
                            eq.put(e)

                    proc = Process(target=timedfn, args=(fn, *args), kwargs=kwargs)
                    proc.start()

                    # try to join after max_runtime_seconds
                    proc.join(runtime)

                    # if it didn't terminate, though... kill it
                    if proc.is_alive():
                        proc.terminate()
                        raise ContractException(
                            f"Function `{function_name}` terminated due to time constraint violation."
                        )
                    else:
                        # if our Process raised and exception, we will want to bubble that up to the caller
                        # because it is not inherently a contract violation and consequently, none of our
                        # business.
                        ret = q.get() if not q.empty() else None
                        if not eq.empty():
                            raise eq.get()
                else:
                    # call the wrapped function...
                    ret = fn(*args, **kwargs)

                # ensure the return valid meets the specification
                if not contract[fn.__name__]["returns"](ret):
                    raise ContractException(
                        f"Return value `{ret}` does not match contract."
                    )
                return Return(None, ret)

            except ContractException as ce:
                if contract["raise_on_contract_exception"]:
                    raise
                else:
                    return Return(ce, None)

        return wrapped

    return dec
