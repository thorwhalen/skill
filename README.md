# skill
Extract code exercises from code itself

To install:	```pip install skill```

There's so many extremely useful gems in builtins (there's also a lot of useless noise).
Personally, I use `collections`, `itertools` and `functools` as well as `map` and `zip` constantly. 
Also recently, `contextlib`. 

Sometimes, you can avoid a many line function simply by putting a few right builtin elements together. 

Knowing what's out there is a first step. 

But it's not enough. You got to think of these components when a problem arises. 
So you need actual practice. 

For example, what would the one liner be to implement this function:

```python
def nth(iterable, n, default=None):
    "Returns the nth item or a default value"
    return ...  # fill in the blans
```

See the answer in [itertools recipes](https://docs.python.org/3/library/itertools.html#itertools-recipes).
The latter contains many more oportunities for such exercises. 

But it would be nice to be able to extract these automatically from code. So here's my little version of that.

# Examples:

## `more_itertools`

To get random exercises for the `more_itertools` module 
(need to pip install it if you don't have it).

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


## itertools recipes

I don't know of a pip installable package for the 
 [itertools recipes](https://docs.python.org/3/library/itertools.html#itertools-recipes)
so I copied that code and put in a local file under `.../ut/util/uiter.py`.

Using that setup, in the following I'll print out all the exercises that 
have no more than 30 lines of docs and 4 lines of code. 
This filtering helps to not get exercises that are too large in their 
description (the docs) or their solution (the code).

```python
from skill import snippets_of_funcs
import ut.util.uiter as m  
# find the file for uiter here: 
#   https://github.com/thorwhalen/ut/blob/master/util/uiter.py

for snippet in snippets_of_funcs(m, max_code_lines=4, max_doc_lines=30):
    if not snippet.startswith('_'):
        print(snippet)
        print()
```

The output is:

```python
accumulate(iterable, func=<built-in function add>)
'''Return running totals'''

batch(iterable, n=1, return_tail=True)
'''Iterator yielding batches of size n of the input iterable.
See also grouper and seq_batch.
:param iterable: in put iterable
:param n: batch size
:param return_tail: whether to return the last chunk (even if it's length is not the batch size)
:return: an iterator'''

consume(iterator, n)
'''Advance the iterator n-steps ahead. If n is none, consume entirely.'''

first_elements_and_full_iter(it, n=1)
'''Given an iterator it, returns the pair (first_elements, it) (where it is the full original
iterator).
This is useful when you need to peek into an iterator before actually processing it (say
because the way you will process it will depend on what you see in there).
:param it: an iterator
:param n: the number of first elements you want to peek at
:return:
    first_elements: A list of the first n elements of the iterator
    it: The original (full) iterator'''

flatten(listOfLists)
'''Flatten one level of nesting'''

grouper(iterable, n=1, fillvalue='drop')
'''Returns an iterable that feeds tuples of size n corresponding to chunks of the input iterable.
See also batch and seq_batch.
:param iterable: Input iterable
:param n: chunk (batch) size
:param fillvalue: The element to use to fill the last chunk, or 'drop' to keep only elements of the iterable,
meaning that the last tuple grouper will feed will be of size < n
:return: An iterable that feeds you chunks of size n of the input iterable

>>> list(grouper('ABCDEFG', 3, 'x'))
[('A', 'B', 'C'), ('D', 'E', 'F'), ('G', 'x', 'x')]
>>> list(grouper('ABCDEFG', 3, 'drop'))
[('A', 'B', 'C'), ('D', 'E', 'F'), ('G',)]'''

grouper_no_fill(iterable, n)
'''grouper_no_fill('ABCDEFG', 3) --> ABC DEF G'''

iter_except(func, exception, first=None)
'''Call a function repeatedly until an exception is raised.

Converts a call-until-exception interface to an iterator interface.
Like __builtin__.iter(func, sentinel) but uses an exception instead
of a sentinel to end the loop.

Examples:
    bsddbiter = iter_except(db.next, bsddb.error, db.first)
    heapiter = iter_except(functools.partial(heappop, h), IndexError)
    dictiter = iter_except(d.popitem, KeyError)
    dequeiter = iter_except(d.popleft, IndexError)
    queueiter = iter_except(q.get_nowait, Queue.Empty)
    setiter = iter_except(s.pop, KeyError)'''

ncycles(iterable, n)
'''Returns the sequence elements n times'''

nth(iterable, n, default=None)
'''Returns the nth item or a default value'''

padnone(iterable)
'''Returns the sequence elements and then returns None indefinitely.

Useful for emulating the behavior of the built-in map() function.'''

pairwise(iterable)
'''s -> (s0,s1), (s1,s2), (s2, s3), ...'''

powerset(iterable)
'''powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)'''

print_iter_progress(iterator, print_progress_every=None, header_template='{hour:02.0f}:{minute:02.0f}:{second:02.0f} - iteration {iteration}', data_msg_intro_str='', data_to_string=None)
'''Wraps an iterator, allowing one to use the iterator as one would, but will print progress messages every
print_progress_every iterations.

header of print string can be specified through header_template
data information can be printed too through data_msg_intro_str and data_to_string (a function) specifications

Examples (but the doctest won't work, since time will be different):

>>> for x in print_iter_progress(xrange(50), print_progress_every=10):
...     pass
...
9:30:5 - iteration 0
9:30:5 - iteration 10
9:30:5 - iteration 20
9:30:5 - iteration 30
9:30:5 - iteration 40

>>> for x in print_iter_progress(xrange(50),
...     print_progress_every=15,
...     data_msg_intro_str="data times two is: {data_str}",
...     data_to_string=lambda x: x * 2):
...     pass
...
9:30:55 - iteration 0data times two is: 0
9:30:55 - iteration 15data times two is: 30
9:30:55 - iteration 30data times two is: 60
9:30:55 - iteration 45data times two is: 90'''

quantify(iterable, pred=<class 'bool'>)
'''Count how many times the predicate is true'''

random_combination(iterable, r)
'''Random selection from combinations(iterable, r)'''

random_combination_with_replacement(iterable, r)
'''Random selection from combinations_with_replacement(iterable, r)'''

random_permutation(iterable, r=None)
'''Random selection from itertools.permutations(iterable, r)'''

random_product(*args, **kwds)
'''Random selection from itertools.product(*args, **kwds)'''

random_subset(iterator, K)
'''Uses reservoir sampling to get a sample from an iterator without knowing how many points there are
in advance.'''

repeatfunc(func, times=None, *args)
'''Repeat calls to func with specified arguments.

Example:  repeatfunc(random.random)'''

roundrobin(*iterables)
'''roundrobin('ABC', 'D', 'EF') --> A D E B F C'''

running_mean(it, chk_size=2, chk_step=1)
'''Running mean (moving average) on iterator.
Note: When input it is list-like, ut.stats.smooth.sliders version of running_mean is 4 times more efficient with
big (but not too big, because happens in RAM) inputs.
:param it: iterable
:param chk_size: width of the window to take means from
:return:

>>> list(running_mean([1, 3, 5, 7, 9], 2))
[2.0, 4.0, 6.0, 8.0]
>>> list(running_mean([1, 3, 5, 7, 9], 2, chk_step=2))
[2.0, 6.0]
>>> list(running_mean([1, 3, 5, 7, 9], 2, chk_step=3))
[2.0, 8.0]
>>> list(running_mean([1, 3, 5, 7, 9], 3))
[3.0, 5.0, 7.0]
>>> list(running_mean([1, -1, 1, -1], 2))
[0.0, 0.0, 0.0]
>>> list(running_mean([-1, -2, -3, -4], 3))
[-2.0, -3.0]'''

seq_batch(seq, n=1, return_tail=True, fillvalue=None)
'''An iterator of equal sized batches of a sequence.
See also grouper and seq_batch.
:param seq: a sequence (should have a .__len__ and a .__getitem__ method)
:param n: batch size
:param return_tail:
    * True (default): Return the tail (what's remaining if the seq len is not a multiple of the batch size),
        as is (so the last batch might not be of size n
    * None: Return the tail, but fill it will the value specified in the fillvalue argument, to make it size n
    * False: Don't return the tail at all
:param fillvalue: Value to be used to fill the tail if return_tail == None

>>> seq = [1, 2, 3, 4, 5, 6, 7]
>>> list(seq_batch(seq, 3, False))
[[1, 2, 3], [4, 5, 6]]
>>> list(seq_batch(seq, 3, True))
[[1, 2, 3], [4, 5, 6], [7]]
>>> list(seq_batch(seq, 3, None))
[[1, 2, 3], [4, 5, 6], [7, None, None]]
>>> list(seq_batch(seq, 3, None, 0))
[[1, 2, 3], [4, 5, 6], [7, 0, 0]]'''

tabulate(function, start=0)
'''Return function(0), function(1), ...'''

take(n, iterable)
'''Return first n items of the iterable as a list'''

tee_lookahead(t, i)
'''Inspect the i-th upcomping value from a tee object
while leaving the tee object at its current position.

Raise an IndexError if the underlying iterator doesn't
have enough values.'''

unique_everseen(iterable, key=None)
'''List unique elements, preserving order. Remember all elements ever seen.
>>> list(unique_everseen('AAAABBBCCDAABBB'))
['A', 'B', 'C', 'D']
>>> import string
>>> list(unique_everseen('ABBCcAD', string.lower))
['A', 'B', 'C', 'D']'''

unique_justseen(iterable, key=None)
'''List unique elements, preserving order. Remember only the element just seen.
>>> list(unique_justseen('AAAABBBCCDAABBB'))
['A', 'B', 'C', 'D', 'A', 'B']
>>> import string
>>> list(unique_justseen('ABBCcAD', string.lower))
['A', 'B', 'C', 'A', 'D']'''

window(seq, n=2)
'''Returns a sliding window (of width n) over data from the iterable'''
```

