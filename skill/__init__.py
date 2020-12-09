from inspect import getsourcelines, getdoc, ismodule, signature

def callables_of_module(m):
    for func in filter(lambda func: getattr(func, '__module__', None) == m.__name__, 
                       filter(callable, map(lambda a: getattr(m, a), dir(m)))):
        yield func
        

def snippets_of_funcs(funcs, max_code_lines=12, max_doc_lines=15):
    if ismodule(funcs):
        funcs = callables_of_module(funcs)
        
    for func in funcs:
        doc = getdoc(func)
        if doc:
            n_doc_lines = len(doc.split('\n'))
            source_lines = getsourcelines(func)
            if (n_doc_lines <= max_doc_lines 
                and (len(source_lines) - n_doc_lines) <= max_code_lines):
                yield f"{func.__name__}{signature(func)}\n\'\'\'{doc}\'\'\'"
                
                
