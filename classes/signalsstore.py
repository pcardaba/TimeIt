from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from .signal import Signal

@dataclass
class SignalsStore:
    """Owns signals and optionally notifies UI on change."""
    _on_change: Callable[[], None] | None = None
    _signals: dict[str, Signal] = field(default_factory=dict)
    _signals_by_uid: dict[str, Signal] = field(default_factory=dict)
    _suspend_depth: int = 0
    _dirty: bool = False

    # ---- core API ----
    def add(self, name: str, signal: Signal) -> None:
        if name in self._signals:
            return
        self._signals[name] = signal
        self._signals_by_uid[str(signal.uid)] = signal
        self._changed()

    def clear(self) -> None:
        # Removes all.
        self._signals.clear()
        self._signals_by_uid.clear()
        self._changed()
        
    def remove(self, name: str) -> None:
        if name in self._signals:
            uid = self._signals[name].uid
            del self._signals[name]
            del self._signals_by_uid[str(uid)]
            self._changed()

    def find(self, name: str) -> Signal | None:
        return self._signals.get(name)

    def find_by_uid(self, uid: str)  -> Signal | None:
        return self._signals_by_uid.get(uid)
        
    def exists(self, name: str) -> bool:
        return name in self._signals

    # ---- safe "views" ----
    def values(self):
        return self._signals.values()

    def items(self):
        return self._signals.items()

    def names(self):
        return self._signals.keys()

    # ---- pythonic helpers (optional) ----
    def __len__(self) -> int:
        return len(self._signals)

    def __contains__(self, name: str) -> bool:
        return name in self._signals

    def __iter__(self) -> Iterator[Signal]:
        return iter(self._signals.values())

    # ---- notification control ----
    def set_on_change(self, cb: Callable[[], None] | None) -> None:
        self._on_change = cb

    @contextmanager
    def batch(self):
        """Group multiple modifications into a single redraw."""
        self._suspend_depth += 1
        try:
            yield self
        finally:
            self._suspend_depth -= 1
            if self._suspend_depth == 0 and self._dirty:
                self._dirty = False
                self._notify()

    def _changed(self) -> None:
        if self._suspend_depth > 0:
            self._dirty = True
            return
        self._notify()

    def _notify(self) -> None:
        if self._on_change is not None:
            self._on_change()





