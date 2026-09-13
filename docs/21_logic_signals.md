# How to create logic and sampled signals

A **derived signal** is not drawn from a list of edges like an input or an output: its waveform is *computed* from other signals of the diagram. Two commands create them:

- `create_logic` combines any number of signals with `and`, `or`, `xor`, `nand`, `nor`, or inverts one with `not`.
- `create_sampled` resamples a signal on a clock edge, the way a flip-flop does.

Derived signals are recomputed on every redraw. Editing an operand, changing a timing variable or moving an edge updates every signal that depends on it, with no extra command to run.

They also compose: the result of a derived signal is expressed exactly like any other waveform, so it can be measured by a timing marker, be annotated, or feed another derived signal.

## The value domain

Every waveform is reduced to four values before being combined or sampled:

| Waveform | Value |
|---|---|
| Low | `0` |
| High | `1` |
| Unknown | `x` |
| Bus data | `D` |
| Hi-Z | `1` when the signal was created `-pulled_up`, `x` otherwise |
| **A transition window** | `x` |

The last row is the important one. The gap between two states in an input or output signal is the min/max uncertainty window computed from its delays: the signal is *in transition* there, and its value is genuinely not known. Derived signals treat it as unknown, which is what makes the computed waveform show the real uncertainty instead of an idealized one.

A hi-Z interval resolves to `1` with a pull-up because a released open-drain net is pulled to logic 1; without one it floats and is unknown.

## Combining signals

```tcl
create_logic -name busy -op and -inputs {req ack} -visible
```

`-inputs` is a Tcl list of the operand names. `-op` accepts `and`, `or`, `xor`, `nand` and `nor` (two or more inputs) and `not` (exactly one input). The default is `and`.

The operands do **not** need to share a clock. The waveforms are combined in the time domain: every transition of every operand appears in the result, so signals launched by unrelated clocks combine correctly.

### The operator tables

Unknown propagates, except where a controlling value masks it:

| `and` | `0` | `1` | `x` |
|---|---|---|---|
| **`0`** | `0` | `0` | `0` |
| **`1`** | `0` | `1` | `x` |
| **`x`** | `0` | `x` | `x` |

| `or` | `0` | `1` | `x` |
|---|---|---|---|
| **`0`** | `0` | `1` | `x` |
| **`1`** | `1` | `1` | `1` |
| **`x`** | `x` | `1` | `x` |

| `xor` | `0` | `1` | `x` |
|---|---|---|---|
| **`0`** | `0` | `1` | `x` |
| **`1`** | `1` | `0` | `x` |
| **`x`** | `x` | `x` | `x` |

`nand` and `nor` are the inverted `and` and `or` tables, so `0 nand x` is `1` and `1 nor x` is `0`. `not` maps `0` to `1`, `1` to `0` and leaves `x` unknown. With more than two inputs the operator is applied across all of them: a single `0` forces an `and` low, a single `1` forces an `or` high, and `xor` gives the parity.

So `0 AND x` is `0` and `1 OR x` is `1`: a controlling value on one input hides the other input's uncertainty, exactly as a real gate does. `xor` has no controlling value, so any unknown on either input makes the result unknown.

### Gate delay

`-tpd_max {expr}` and `-tpd_min {expr}` delay the whole result by the gate propagation delay:

```tcl
create_logic -name busy -op and -inputs {req ack} \
   -tpd_max {$tANDmax} -tpd_min {$tANDmin} -visible
```

Both are Tcl expressions, like every timing quantity of TimeIt. `-tpd_max` defaults to 0 and `-tpd_min` defaults to the value of `-tpd_max`, so a single value shifts the waveform without changing it. When the two differ, the spread between them widens every transition window of the result, exactly like the min/max delays of an input or output signal: the output is only established once the slow path has propagated, and may start changing as soon as the fast path does. A pulse narrower than the spread becomes entirely uncertain.

### What cannot be an operand

- **A clock.** Use the clock's waveform through an input or output signal instead.
- **A signal carrying bus data** (`-data_edges`). A bus window has no scalar value to combine.
- **An analog (PWL) signal.**
- **The signal itself, or anything that already reads it.** A definition that would close a dependency loop is refused, naming the input through which the loop would close.

## Visibility

`-visible` draws the signal; without it the signal is computed but not shown. A hidden derived signal is still recomputed and can still be read by others, which is the way to build an intermediate term without cluttering the diagram:

```tcl
# Not drawn, but usable as an operand.
create_logic -name sel -op xor -inputs {a b}

create_logic -name out -op and -inputs {sel en} -visible
```

## Removing a derived signal or its operands

A derived signal holds a direct reference to its operands, so removing a signal that one of them reads is **refused**, with a message naming the dependents. Remove the derived signals first, or edit them to read something else.

## Limitations

- Derived signals are **not** written to SDC by `write_sdc`. They model internal nodes, not I/O pins, and are silently omitted.
- A derived signal can not be the enable signal (`-enabled_by`) of a gated clock. Only inputs and outputs may gate a clock.
- A signal whose operands or delays cannot be resolved cannot be drawn, and TimeIt **removes any signal it cannot draw**. It is not merely hidden. Check the console for the reason.

Run `create_logic -help` or `create_sampled -help` for the full syntax.

---

*Previous: [How to create PWL (analog) signals](20_pwl_signals.md) | Back to [Introduction](00_introduction.md)*
