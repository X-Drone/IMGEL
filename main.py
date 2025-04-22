import re
from dependences.peco.peco import *


def define_grammar():
    # base elements
    space = eat(r'[\s\n]*')
    token = lambda f: seq(space, f)
    tok = lambda c: token(push(eat(c)))
    skip = lambda c: token(eat(c))
    async_func = lambda s: async_func(s)
    async_lambda = lambda s: async_lambda(s)

    btw_async = group(push(eat(r'[\s\S]*?(?=\basync\b)')))

    # header
    async_kw = push(eat(r'async\b'))
    await_kw = tok(r'await\b')
    return_type = tok(r'(?:std::future<.*?>|[a-zA-Z_][a-zA-Z0-9_]*)')
    func_name = tok(r'[a-zA-Z_][a-zA-Z0-9_]*')

    # parameters
    param_type = tok(r'[a-zA-Z_][a-zA-Z0-9_:*]*')
    param_name = tok(r'[a-zA-Z_][a-zA-Z0-9_]*')
    param = group(seq(param_type, space, param_name))
    params = seq(skip(r'\('), group(list_of(param, skip(','))), skip(r'\)'))

    # arguments
    arg = tok(r'[^,()]+')
    args = seq(skip(r'\('), group(list_of(arg, skip(','))), skip(r'\)'))

    # function body
    body = seq(skip(r'{'), alt(async_lambda, tok(r'[^}]*')), skip(r'}'))

    # async function
    async_func = seq(
        async_kw,
        return_type,
        func_name,
        params,
        body,
        to(lambda async_kw_, return_type_, func_name_, params_, body_:
           (async_kw_, return_type_, func_name_, params_, body_))
    )

    # async lambda
    async_lambda = seq(
        skip(r'[^await]*'),
        await_kw,
        async_kw,
        return_type,
        params,
        body,
        args,
        to(lambda await_kw_, async_kw_, return_type_, params_, body_, args_:
           ('await async', return_type_, params_, body_, args_))
    )
    return group(seq(many(seq(btw_async, async_func)), group(push(eat('[\s\S]*')))))


def generate_code(ast):
    code = ''
    for ast_node in ast:
        if ast_node[0] == 'async':
            return_type, func_name, params, body = ast_node[1:]
            param_str = ', '.join(f"{t} {n}" for t, n in params)

            transformed_body = re.sub(r'\bawait\s*(.+?);', r'\1.get();', body, flags=re.DOTALL)

            lambda_body = f"[=](){{\n{transformed_body}\n}}"
            code += f"std::future<{return_type}> {func_name}({param_str}) " \
                    f"{{ return std::async({lambda_body}); }}\n"
        elif ast_node[0] == 'await async':
            _, return_type, params, body, args = ast_node
            param_str = ', '.join(f"{t} {n}" for t, n in params)
            arg_str = ', '.join(args)
            transformed_body = re.sub(r'\bawait\s*(.+?);', r'\1.get();', body, flags=re.DOTALL)
            lambda_body = f"[=](){{\n{transformed_body}\n}}"
            code += f"(std::async([]({param_str}){lambda_body}({arg_str})).get();"
        else:
            code += re.sub(r'\bawait\s*(.+?);', r'\1.get();', ast_node[0], flags=re.DOTALL)
    return code


def main():
    src = """
#include <iostream>
#include <async_await>

async data fetchData(string url)
{
    Data data = await download(url); 
    return process(data);
}

async bool pushData(Data data, string url)
{
    bool check = await push(url, data); 
    return check;
}

int main()
{
    Data processed_data = await fetchData("google.com");
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

    parser = define_grammar()
    ast = parse(src, parser)
    print("Peco:", ast)
    print("AST:", ast.stack[0])
    print("\nGenerated Code:\n")
    print(generate_code(ast.stack[0]))


if __name__ == '__main__':
    main()
