"""Generic plugin registry with entry point discovery."""

from collections.abc import MutableMapping, Iterator
from importlib.metadata import entry_points
from typing import TypeVar, Generic

T = TypeVar('T')

_ENTRY_POINT_GROUP_PREFIX = 'skill.'


class Registry(MutableMapping, Generic[T]):
    """A name-keyed registry of typed objects with lazy entry point discovery.

    Each ``Registry`` wraps a dict and can auto-discover plugins registered
    via ``importlib.metadata`` entry points under the group
    ``skill.<registry_name>``.

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
    """

    def __init__(self, name: str, *, entry_point_group: str | None = None):
        self._name = name
        self._items: dict[str, T] = {}
        self._entry_point_group = (
            entry_point_group or f'{_ENTRY_POINT_GROUP_PREFIX}{name}'
        )
        self._entry_points_loaded = False

    @property
    def name(self) -> str:
        """Registry name (also used to derive the entry point group).

        >>> Registry('agents').name
        'agents'
        """
        return self._name

    def register(self, name: str, item: T) -> T:
        """Register an item and return it (usable as a decorator factory).

        >>> r = Registry('demo')
        >>> r.register('x', lambda: 1)  # doctest: +ELLIPSIS
        <function ...>
        >>> 'x' in r
        True
        """
        self._items[name] = item
        return item

    def _load_entry_points(self) -> None:
        """Discover and load plugins from entry points (once)."""
        if self._entry_points_loaded:
            return
        self._entry_points_loaded = True
        try:
            eps = entry_points(group=self._entry_point_group)
        except TypeError:
            # Python 3.10/3.11 compat: entry_points() may not accept group kwarg
            eps = entry_points().get(self._entry_point_group, [])
        for ep in eps:
            if ep.name not in self._items:
                try:
                    self._items[ep.name] = ep.load()
                except Exception:
                    pass  # Skip broken plugins gracefully

    # -- MutableMapping interface --

    def __getitem__(self, key: str) -> T:
        self._load_entry_points()
        return self._items[key]

    def __setitem__(self, key: str, value: T) -> None:
        self._items[key] = value

    def __delitem__(self, key: str) -> None:
        del self._items[key]

    def __iter__(self) -> Iterator[str]:
        self._load_entry_points()
        return iter(self._items)

    def __len__(self) -> int:
        self._load_entry_points()
        return len(self._items)

    def __contains__(self, key: object) -> bool:
        self._load_entry_points()
        return key in self._items

    def __repr__(self) -> str:
        self._load_entry_points()
        return f"Registry({self._name!r}, keys={list(self._items)})"
