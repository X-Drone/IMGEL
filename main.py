import re
from dependences.peco.peco import *

class Converter:
    def __init__(self):
        self.parser_async_func = self.define_async_func_grammar()
        self.parser_await_call = self.define_await_call_grammar()

    def convert(self, source_code: str) -> str:
        ast = parse(source_code, self.parser_async_func)
        code = self.generate_async_func(ast.stack[0])

        # now extract body and handle await calls
        #return code
        flat_code = code
        await_ast = parse(flat_code, self.parser_await_call)
        print('AST: ', await_ast.stack[0])
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



def main():
    src = """
#include <iostream>
#include <async_await>

async Data fetchData(string url)
{
    Data data = await download(url);
    Data processed = process(data);
    return processed;
}

async bool pushData(Data data, string url)
{
    bool check = await push(url, data); 
    return check;
}

int main()
{
    Data processed_data = await async Data(string url) {
        return fetchData(url);
    } ("google.com");
    if (await pushData(processed_data, "my_serv.com"))
        std::cout << "pushed";
    else std::cout << "not pushed";
}

"""
    src_recur = """
async int fetchData(int q, string url)
{
   Data data = await async Data (string url)
        { connect(url); return download(); } (url); 
   return process(data);
}

"""

    converter = Converter()
    print(converter.convert(src))


if __name__ == '__main__':
    main()
