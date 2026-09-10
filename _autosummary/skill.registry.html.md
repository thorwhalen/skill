# skill.registry

Generic plugin registry with entry point discovery.

### Classes

| [`Registry`](#skill.registry.Registry)(name, \*[, entry_point_group])   | A name-keyed registry of typed objects with lazy entry point discovery.   |
|--------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|

### *class* skill.registry.Registry(name, , entry_point_group=None)

Bases: [`MutableMapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping), [`Generic`](https://docs.python.org/3/library/typing.html#typing.Generic)[`T`]

A name-keyed registry of typed objects with lazy entry point discovery.

Each `Registry` wraps a dict and can auto-discover plugins registered
via `importlib.metadata` entry points under the group
`skill.<registry_name>`.

```pycon
>>> r = Registry('demo')
>>> r['foo'] = 42
>>> r['foo']
42
>>> list(r)
['foo']
>>> len(r)
1
>>> del r['foo']
>>> len(r)
0
```

#### *property* name *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

Registry name (also used to derive the entry point group).

```pycon
>>> Registry('agents').name
'agents'
```

#### register(name, item)

Register an item and return it (usable as a decorator factory).

* **Return type:**
  [`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`T`)

```pycon
>>> r = Registry('demo')
>>> r.register('x', lambda: 1)
<function ...>
>>> 'x' in r
True
```
