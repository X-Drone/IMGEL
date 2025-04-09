import re
from dependences.peco.peco import *


def define_grammar():
    # base elements
    space = eat(r'[\s\n]*')
    token = lambda f: seq(space, f)
    tok = lambda c: token(push(eat(c)))
    skip = lambda c: token(eat(c))

    # header
    async_kw = tok(r'async')
    return_type = tok(r'(?:std::future<.*?>|[a-zA-Z_][a-zA-Z0-9_]*)')
    func_name = tok(r'[a-zA-Z_][a-zA-Z0-9_]*')

    # parameters
    param_type = tok(r'[a-zA-Z_][a-zA-Z0-9_:*]*')
    param_name = tok(r'[a-zA-Z_][a-zA-Z0-9_]*')
    param = group(seq(param_type, space, param_name))
    params = seq(skip(r'\('), group(list_of(param, skip(','))), skip(r'\)'))

    # function body
    body = seq(skip(r'{'), tok(r'[^}]*'), skip(r'}'))

    # async function
    return seq(
        async_kw,
        return_type,
        func_name,
        params,
        body,
        to(lambda async_kw_, return_type_, func_name_, params_, body_:
           (async_kw_, return_type_, func_name_, params_, body_))
    )


def generate_code(ast_node):
    if ast_node[0] == 'async':
        return_type, func_name, params, body = ast_node[1:]
        param_str = ', '.join(f"{t} {n}" for t, n in params)

        transformed_body = re.sub(r'\bawait\s*(.+?);', r'\1.get();', body, flags=re.DOTALL)

        lambda_body = f"[=](){{\n{transformed_body}\n}}"
        return f"std::future<{return_type}> {func_name}({param_str}) " \
               f"{{ return std::async({lambda_body}); }}\n"
    return str(ast_node)


def main():
    src = """
    async int fetchData(int q, string url)
    {
       Data data = await download(url); 
       return process(data);
    }
    """

    parser = define_grammar()
    ast = parse(src, parser)
    print("AST:", ast)
    print("\nGenerated Code:\n")
    print(generate_code(ast.stack[0]))


if __name__ == '__main__':
    main()
