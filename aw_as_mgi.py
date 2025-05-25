import argparse
import sys
from dependences.peco.peco import *

class Converter:
    def __init__(self):
        self.parser_async_func = self.define_async_func_grammar()
        self.parser_await_call = self.define_await_call_grammar()

    def convert(self, source_code: str, verbose: bool = False) -> str:
        """
        Perform two-phase parsing and code generation:
        1. Extract and translate async function definitions.
        2. Rewrite await calls into std::async .get() expressions.
        """
        # Phase 1: async functions
        ast = parse(source_code, self.parser_async_func)
        code = self.generate_async_func(ast.stack[0])

        # Phase 2: await calls
        flat_code = code
        await_ast = parse(flat_code, self.parser_await_call)
        # Print AST only in verbose mode
        if verbose:
            print('AST: ', await_ast.stack[0], file=sys.stderr)
        final_code = self.generate_await_calls(await_ast.stack[0])
        return final_code

    def define_async_func_grammar(self):
        space = eat(r'[\s\n]*')
        token = lambda f: seq(space, f)
        tok = lambda c: token(push(eat(c)))
        skip = lambda c: token(eat(c))

        async_kw = tok(r'async\b')
        return_type = tok(r'(?:std::future<.*?>|[a-zA-Z_][a-zA-Z0-9_]*)')
        func_name = tok(r'[a-zA-Z_][a-zA-Z0-9_]*')

        param_type = tok(r'[a-zA-Z_][a-zA-Z0-9_:*]*')
        param_name = tok(r'[a-zA-Z_][a-zA-Z0-9_]*')
        param = group(seq(param_type, space, param_name))
        params = seq(skip(r'\('), group(list_of(param, skip(','))), skip(r'\)'))

        body = seq(skip(r'{'), tok(r'[^}]*'), skip(r'}'))

        # async function
        async_func = seq(
            async_kw,
            return_type,
            func_name,
            params,
            body,
            to(lambda async_kw_, return_type_, func_name_, params_, body_:
               ('async', return_type_, func_name_, params_, body_))
        )

        btw_async = group(push(eat(r'[\s\S]*?(?=\basync\b)')))
        return group(seq(many(seq(btw_async, async_func)), group(push(eat('[\s\S]*')))))

    def define_await_call_grammar(self):
        space = eat(r'[\s\n]*')
        token = lambda f: seq(space, f)
        tok = lambda c: token(push(eat(c)))
        skip = lambda c: token(eat(c))

        await_kw = tok(r'await\b')
        async_kw = tok(r'async\b')
        return_type = tok(r'(?:std::future<.*?>|[a-zA-Z_][a-zA-Z0-9_]*)')

        param_type = tok(r'[a-zA-Z_][a-zA-Z0-9_:*]*')
        param_name = tok(r'[a-zA-Z_][a-zA-Z0-9_]*')
        param = group(seq(param_type, space, param_name))
        params = seq(skip(r'\('), group(list_of(param, skip(','))), skip(r'\)'))

        args = seq(skip(r'\('), group(list_of(tok(r'[^,()]+'), skip(','))), skip(r'\)'))

        body = seq(skip(r'{'), tok(r'[^}]*'), skip(r'}'))

        # inline await async
        await_async_lambda = seq(
            await_kw,
            async_kw,
            return_type,
            params,
            body,
            args,
            to(lambda await_kw_, async_kw_, return_type_, params_, body_, args_:
               ('await async', return_type_, params_, body_, args_))
        )

        # await expr
        await_expr = seq(
            await_kw,
            tok(r'[^)]+'),
            skip(r'\)'),
            to(lambda await_kw_, expr: ('await', expr))
        )

        btw_await = group(push(eat(r'[\s\S]*?(?=\bawait\b)')))
        return group(seq(many(seq(btw_await, alt(await_async_lambda, await_expr))), push(eat('[\s\S]*'))))

    def generate_async_func(self, ast):
        code = ''
        for ast_node in ast:
            if ast_node[0] == 'async':
                return_type, func_name, params, body = ast_node[1:]
                param_str = ', '.join(f"{t} {n}" for t, n in params)
                lambda_body = f"[=](){{\n{body}\n}}"
                code += f"std::future<{return_type}> {func_name}({param_str}) " \
                        f"{{ return std::async({lambda_body}); }}\n"
            else:
                code += ast_node[0]
        return code

    def generate_await_calls(self, ast_nodes):
        code = ''
        for node in ast_nodes:
            if isinstance(node, str):
                code += node
            elif node[0] == 'await async':
                _, return_type, params, body, args = node
                param_str = ', '.join(f"{t} {n}" for t, n in params)
                arg_str = ', '.join(args)
                lambda_body = f"[=](){{\n{body}\n}}"
                code += f"(std::async([]({param_str}){lambda_body}({arg_str})).get()"
            elif node[0] == 'await':
                expr = node[1]
                code += f"{expr}).get()"
            else:
                code += node[0]
        return code


def run_tests():
    """
    Internal test suite with sample inputs and expected patterns.
    """
    converter = Converter()
    samples = [
        ("int var = await async int(int num) { return 1; } (2);",
         "int var = (std::async([](int num)[=](){\nreturn 1; \n}(2)).get();"),
        ("async int foo(int num) { return 1; }",
         "std::future<int> foo(int num) { return std::async([=](){\nreturn 1; \n}); }"),
        ("await dl(u);",
         "dl(u).get();"),
    ]
    all_pass = True
    for src, expected in samples:
        out = converter.convert(src)
        if expected not in out:
            print(f"[FAIL] Expected '{expected}' in output, got: {out}")
            all_pass = False
        else:
            print(f"[PASS] '{expected}' found.")
    if all_pass:
        print("All tests passed.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='CLI for converting async/await C++ patterns to std::async/std::future usage'
    )
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--test', action='store_true', help='Run internal test suite')
    mode_group.add_argument('-i', '--input', metavar='INPUT', help='Path to the input source file')
    parser.add_argument('-o', '--output', metavar='OUTPUT', help='Path to write converted code')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose debug output')
    args = parser.parse_args()

    if args.test:
        run_tests()
        sys.exit(0)

    if not args.input or not args.output:
        parser.error('Input and output files must be specified when not in test mode')

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            src = f.read()
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        sys.exit(1)

    converter = Converter()
    result = converter.convert(src, verbose=args.verbose)

    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        if args.verbose:
            print(f"Converted code written to {args.output}")
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)
