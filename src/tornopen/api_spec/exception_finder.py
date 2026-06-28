import ast
import sys
from collections import ChainMap
from inspect import getclosurevars, getsource
from textwrap import dedent


class _ExceptionsFinder(ast.NodeTransformer):
    def __init__(self):
        self.nodes = []

    def visit_Raise(self, node):
        self.nodes.append(node.exc)


def _get_wrapped_function(func):
    if "__wrapped__" in func.__dict__:
        func = func.__dict__["__wrapped__"]
        return _get_wrapped_function(func)
    return func


def get_exceptions(func):
    func = _get_wrapped_function(func)

    try:
        vars = ChainMap(*getclosurevars(func)[:3])
        source = dedent(getsource(func))
    except TypeError:
        return

    v = _ExceptionsFinder()
    v.visit(ast.parse(source))
    results = []
    for node in v.nodes:
        if not isinstance(node, (ast.Call, ast.Name)):
            continue

        name = node.id if isinstance(node, ast.Name) else node.func.id
        if name in vars:
            node_args = getattr(node, "args", [])
            args = [parse_value(arg, func) for arg in node_args]
            node_kwargs = getattr(node, "keywords", [])
            kwargs = {
                keyword.arg: parse_value(keyword.value, func) for keyword in node_kwargs
            }
            yield vars[name], args, kwargs
            results.append((vars[name], args, kwargs))


def parse_value(keyword_value, func):
    if hasattr(keyword_value, "value"):
        return keyword_value.value
    elif hasattr(keyword_value, "n"):
        return keyword_value.n
    elif hasattr(keyword_value, "s"):
        return keyword_value.s
    else:
        func_lines = getsource(func).splitlines()
        start_line_no = keyword_value.lineno - 1
        end_line_no = keyword_value.end_lineno or start_line_no
        start_col = keyword_value.col_offset
        end_col = keyword_value.end_col_offset

        output = ""
        line_count = end_line_no - start_line_no - 1
        for line_no, line in enumerate(func_lines[start_line_no:end_line_no]):
            start_index = start_col if line_no == 0 else 0
            end_index = end_col if line_no == line_count else sys.maxsize
            output += line[start_index:end_index]
        return output
