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
    _signals_order: list[str] = field(default_factory=list)
    _suspend_depth: int = 0
    _dirty: bool = False

    # ---- core API ----
    def add(self, name: str, signal: Signal) -> None:
        if name in self._signals:
            return
        self._signals[name] = signal
        self._signals_by_uid[str(signal.uid)] = signal
        self._signals_order.append(name)
        self._changed()

    def clear(self) -> None:
        # Removes all.
        self._signals.clear()
        self._signals_by_uid.clear()
        self._signals_order.clear()
        self._changed()
        
    def remove(self, name: str) -> None:
        if name in self._signals:
            uid = self._signals[name].uid
            del self._signals[name]
            del self._signals_by_uid[str(uid)]
            self._signals_order.remove(name)
            self._changed()

    def replace(self, name: str, signal: Signal) -> None:
        """Substitute the signal stored under `name`, keeping its position."""
        old = self._signals.get(name)
        if old is None:
            return
        del self._signals_by_uid[str(old.uid)]
        self._signals[name] = signal
        self._signals_by_uid[str(signal.uid)] = signal
        self._changed()

    def rename(self, old: str, new: str) -> None:
        """Re-key the signal stored under `old` as `new`, keeping its position."""
        if old == new or old not in self._signals or new in self._signals:
            return
        self._signals[new] = self._signals.pop(old)
        self._signals_order[self._signals_order.index(old)] = new
        self._changed()

    def find(self, name: str) -> Signal | None:
        return self._signals.get(name)

    def find_by_uid(self, uid: str)  -> Signal | None:
        return self._signals_by_uid.get(uid)
        
    def exists(self, name: str) -> bool:
        return name in self._signals

    def index(self, name: str) -> int:
        return self._signals_order.index(name)
    
    def get_index(self, name: str) -> int:
        return self._signals_order.index(name)
    
    def move_up(self, name: str) -> None:
        i = self._signals_order.index(name)
        if i > 0:
            self._signals_order[i - 1], self._signals_order[i] = (
                self._signals_order[i],
                self._signals_order[i - 1],
            )
            self._changed()

    def move_down(self, name: str) -> None:
        i = self._signals_order.index(name)
        if i < len(self._signals_order) - 1:
            self._signals_order[i], self._signals_order[i + 1] = (
                self._signals_order[i + 1],
                self._signals_order[i],
            )
            self._changed()

    def move(self, name: str, direction: str) -> None:
        if direction == "up":
            self.move_up(name)
        else:
            self.move_down(name)

    # ---- dependency rules ----
    @staticmethod
    def _references(signal: Signal) -> tuple:
        """The signals `signal` depends on and must therefore stay below.

        An I/O signal refers to its launch and capture clocks, a generated
        clock to its master clock, and a derived (logic/sampled) signal to
        its operands.
        """
        if signal is None:
            return ()
        refs = list(getattr(signal, "related_clocks", tuple)())
        master = getattr(signal, "master", None)
        if master is not None:
            refs.append(master)
        refs.extend(getattr(signal, "operands", tuple)())
        return tuple(refs)

    @staticmethod
    def cascade_of(signal: Signal) -> list[Signal]:
        """The signals removed together with `signal`.

        Those are its related objects that are signals (an I/O signal goes
        with its clocks, a generated clock with its master), transitively.
        """
        out: list[Signal] = []
        pending = [signal]
        seen = {id(signal)}
        while pending:
            current = pending.pop()
            for obj in getattr(current, "get_related_objs", set)():
                if getattr(obj, "type", None) == "tmarker" or id(obj) in seen:
                    continue
                seen.add(id(obj))
                out.append(obj)
                pending.append(obj)
        return out

    def dependents_of(self, name: str) -> list[str]:
        """Names of the derived signals that read `name` as an operand.

        Includes the readers of any signal that would be cascade removed with
        `name` (an I/O signal launched by a removed clock, for instance). A
        derived signal holds a plain reference to its operands and has no
        cascade registration of its own, so removing one of them has to be
        refused rather than propagated. In store order.
        """
        target = self.find(name)
        if target is None:
            return []
        gone = {id(target)} | {id(sig) for sig in self.cascade_of(target)}
        return [other.name for other in self
                if id(other) not in gone
                and any(id(op) in gone
                        for op in getattr(other, "operands", tuple)())]

    def remove_error(self, name: str) -> str | None:
        """Why `name` can not be removed, None when it can.

        Shared by the GUI and the remove command. A signal read by a derived
        signal (directly, or through a signal cascade removed with it) stays:
        the derived signal has to be removed, or edited to read something
        else, first.
        """
        dependents = self.dependents_of(name)
        if not dependents:
            return None
        return (f"{name} is read by {', '.join(dependents)}: remove or edit "
                f"those derived signals (change their operands) first")

    def move_error(self, name: str, direction: str) -> str | None:
        """Why `name` can not be moved in `direction`, None when it can.

        Shared by the GUI (which shows it in a messagebox) and by the
        move_signal command (which reports it as an error), so a single rule
        governs both. A signal already at the end of the order is not an
        error: the move is simply a no-op.
        """
        signal = self.find(name)
        if signal is None:
            return f"{name} signal not found"

        i = self._signals_order.index(name)

        if direction == "up":
            if i > 0 and self[i - 1] in self._references(signal):
                return ("Signal can not be moved above a signal it refers to "
                        "(its reference clock or an operand).\n"
                        "(The referred signal may be hidden)")
            return None

        if i < len(self._signals_order) - 1 \
           and signal in self._references(self[i + 1]):
            return ("A signal can not be moved below a signal that refers to "
                    "it. Reference clocks and operands shall always be above "
                    "the signals referring to them.")
        return None


    # ---- safe "views" ----
    def values(self):
        return iter(self)

    def items(self):
        return ((name, self._signals[name]) for name in self._signals_order)

    def names(self):
        return self._signals_order[:]

    # ---- pythonic helpers (optional) ----
    def __len__(self) -> int:
        return len(self._signals)

    def __contains__(self, name: str) -> bool:
        return name in self._signals

    def __iter__(self) -> Iterator[Signal]:
        for name in self._signals_order:
            yield self._signals[name]
            
    def __getitem__(self, index: int) -> Signal:
        if index >= len(self._signals_order):
            return None
        name = self._signals_order[index]
        return self._signals[name]
    
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





