# How to create timing markers

Timing markers draw a measured arrow between two waveform points, annotating the time interval between them. Use `create_timing_marker` in the TCL console.

## Command syntax

```
create_timing_marker  -name name
                      -from select:uid
                      -to select:uid
                      [-at y_coord]
                      [-style (inner_both)|inner_right|inner_left|outer]
                      [-anchor (none)|from|to]
                      [-label_x rel_x]
                      [-label_y rel_y]
                      [-help]
```

## Key parameters

| Parameter | Description |
|---|---|
| `-name` | Marker label. Use `""` to display the measured time value directly; a non-empty name stores the value and displays the name instead. |
| `-from` | Start measurement point as `select:uid` (e.g. `end:uid_1_3`). |
| `-to` | End measurement point as `select:uid`. |
| `-at` | Y position of the marker line on the canvas (pixels). |
| `-style` | Arrow style (see below). Default: `inner_both`. |
| `-anchor` | `none` (absolute y), `from`, or `to` (y relative to the anchored signal slot). |
| `-label_x` | Horizontal offset of the label from the marker midpoint (px). |
| `-label_y` | Vertical offset of the label from the marker line (px). |

## Measurement point syntax: `select:uid`

The `select` part specifies which point on the waveform element to measure:

| Selector | Meaning |
|---|---|
| `full` | Mid-point of the full element bounding box |
| `start` | Left edge of the element bounding box |
| `end` | Right edge of the element bounding box |
| `middle` | Horizontal centre of the element bounding box |

`uid` is the unique tag of a waveform element (e.g. `uid_1_3`). UIDs are shown when you click on a waveform element in the canvas.

## Marker styles

| Style | Description |
|---|---|
| `inner_both` | Arrow line between the two legs, arrows on both ends (default) |
| `inner_right` | Arrow on right end only |
| `inner_left` | Arrow on left end only |
| `outer` | Two outward arrows pointing at the measurement points |

> **TODO:** Add a diagram or screenshot illustrating each of the four styles side by side.

## Step-by-step example

### 1. Display the measured time as the label

```tcl
create_timing_marker -name "" \
                     -from end:uid_1_2 \
                     -to start:uid_2_1 \
                     -at 80
```

> **TODO:** Add screenshot showing the auto-labelled marker on the canvas.

### 2. Named marker (value stored for later use)

```tcl
create_timing_marker -name "tsu" \
                     -from end:uid_1_2 \
                     -to start:uid_2_1 \
                     -at 80 \
                     -anchor from \
                     -style inner_both
```

The value is stored in the timings dictionary and is accessible as `$tsu` in subsequent TCL expressions.

> **TODO:** Add screenshot.

## How to find UIDs

Click on a waveform element in the canvas. The status bar (or console) will report the UID of the element under the cursor.

> **TODO:** Add screenshot showing the UID display.

---

*Previous: [How to create input/output signal(s)](04_io_signals.md) | Next: [How to save and load](06_save_load.md)*
