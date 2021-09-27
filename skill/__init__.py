"""
Extract code exercises from code itself

Example uses:

```python
from skill import snippets_of_funcs
import ut.util.uiter as m  # find here: https://github.com/thorwhalen/ut/blob/master/util/uiter.py

for snippet in snippets_of_funcs(m, max_code_lines=4, max_doc_lines=30):
    if not snippet.startswith('_'):
        print(snippet)
        print()
```

To get random exercises:

```python
from skill import Exercises
import more_itertools.more as m
e = Exercises(m)

# and then repeatedly ask for random exercises.
e.print_random_exercise()
```

This `Exercises` class is meant to be subclassed to include tracking of exercises presented,
and possibly performance metrics (explicitly self-declared or inferred from a response).
These statistics can then be used to chose the exercises not randomly, but so as to
optimize learning.

"""
from inspect import getsourcelines, getdoc, ismodule, signature
from random import randint


def callables_of_module(m):
    for func in filter(lambda func: getattr(func, '__module__', None) == m.__name__,
                       filter(callable, map(lambda a: getattr(m, a), dir(m)))):
        yield func


def snippets_of_funcs(funcs, max_code_lines=12, max_doc_lines=15,
                      ignored_exceptions=(ValueError,)):
    if ismodule(funcs):
        funcs = callables_of_module(funcs)

    for func in funcs:
        doc = getdoc(func)
        if doc:
            try:
                n_doc_lines = len(doc.split('\n'))
                source_lines = getsourcelines(func)
                if (n_doc_lines <= max_doc_lines
                        and (len(source_lines) - n_doc_lines) <= max_code_lines):
                    yield f"{func.__name__}{signature(func)}\n\'\'\'{doc}\'\'\'"
            except ignored_exceptions:
                pass


class Exercises:
    def __init__(self, funcs, max_code_lines=12, max_doc_lines=15,
                 ignored_exceptions=(ValueError,)):
        _gen = snippets_of_funcs(funcs, max_code_lines, max_doc_lines, ignored_exceptions)
        self.snippets = list(_gen)

    def print_random_exercise(self):
        i = randint(0, len(self.snippets))
        print(self.snippets[i])
