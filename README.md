# TimeIt EDA

**A scriptable graphical editor for creating precise digital timing diagrams for FPGA, ASIC and SoC documentation.**

[![Latest release](https://img.shields.io/github/v/release/pcardaba/TimeIt)](https://github.com/pcardaba/TimeIt/releases)
[![License: GPL-3.0](https://img.shields.io/github/license/pcardaba/TimeIt)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)

TimeIt combines an interactive waveform canvas with a built-in Tcl console. It is designed for digital hardware engineers who need to describe, review and communicate timing relationships involving clocks, inputs, outputs, delays, uncertainty, markers and annotations.

<p align="center">
  <img src="docs/screenshots/QSPI_program_inst.png" alt="QSPI timing diagram created with TimeIt" width="900">
</p>

## Why TimeIt?

Timing diagrams often need to express more than logical high and low levels. They may also need to show launch and capture clocks, input and output delays, timing uncertainty, setup and hold relationships, generated clocks and symbolic timing parameters.

TimeIt provides an EDA-oriented workflow for creating these diagrams:

- **Model hardware timing concepts** such as clocks, input signals, output signals, delays and timing windows.
- **Build parametric diagrams** using named timing variables and mathematical expressions.
- **Combine graphical and scripted editing** through an interactive canvas and Tcl console.
- **Add timing markers and annotations** for design reviews and interface specifications.
- **Save diagrams as Tcl scripts** that can be inspected, version-controlled and reused.
- **Export to PNG, JPEG, SVG, PDF, EPS and PostScript.**
- **Run fully offline** without network connections.
- **Install without administrator rights** by copying the source bundle.
- **Use no third-party Python packages** beyond Python and Tkinter/Tcl-Tk.

> [!NOTE]
> TimeIt is intended for timing specification, documentation and visual reasoning. It does not replace HDL simulation or a static timing analysis engine.

## Typical use cases

- Document FPGA, ASIC and SoC interface timing requirements.
- Explain launch/capture relationships during design reviews.
- Represent setup, hold, input-delay and output-delay requirements.
- Visually cross-check timing concepts before writing SDC constraints.
- Produce scalable diagrams for datasheets, reports and presentations.
- Create reusable protocol illustrations for SPI, QSPI, I²C, JTAG or SWD.
- Explore the effect of changing a clock period or timing parameter across a complete diagram.

## Quick start

### Requirements

- Python **3.10 or later**
- Tkinter / Tcl-Tk

Tkinter is normally bundled with Python. On some Linux distributions, it must be installed separately.

<details>
<summary>Install Tkinter on Linux</summary>

```bash
# Debian / Ubuntu
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch Linux
sudo pacman -S tk
```

</details>

### Clone and launch

Run these commands from the directory in which you want the `TimeIt` folder to be created:

```bash
git clone https://github.com/pcardaba/TimeIt.git
python3 -m TimeIt.main
```

On Windows, depending on your Python installation:

```powershell
git clone https://github.com/pcardaba/TimeIt.git
py -m TimeIt.main
```

> [!IMPORTANT]
> Launch TimeIt from the directory **containing** the `TimeIt` folder, not from inside the package directory.

You can also download a stable source archive from the [Releases](https://github.com/pcardaba/TimeIt/releases) page. Extract it, rename the extracted directory to `TimeIt` when necessary, open a terminal in its parent directory and run the same module command.

For detailed instructions, see the [installation guide](docs/01_install.md) and [launch guide](docs/02_launch.md).

## First steps

After launching TimeIt:

1. Load one of the example Tcl scripts from the [`scripts/`](scripts/) directory.
2. Inspect the commands in the built-in Tcl console.
3. Modify a clock, signal or timing variable.
4. Use the canvas context menus to edit the diagram interactively.
5. Save the result as a Tcl script.
6. Export the complete canvas through **File → Export Canvas…**.

Useful shortcuts:

- `Ctrl` + `S` — save the current diagram
- `Shift` + mouse wheel — zoom the waveform canvas

## Parametric timing diagrams

TimeIt diagrams can use named variables instead of hard-coded numerical values. Variables may also contain expressions derived from other variables.

```tcl
set_app_var -name timings.Tclk \
    -desc {Clock period} \
    -value {10}

set_app_var -name timings.Thalf \
    -desc {Half clock period} \
    -value {$Tclk/2.0}

set_app_var -name timings.tSU \
    -desc {Setup requirement} \
    -value {2.0}

set_app_var -name timings.tHO \
    -desc {Hold requirement} \
    -value {1.0}

create_clock -name clk \
    -topology source \
    -period {$Tclk} \
    -rise_at {0} \
    -fall_at {$Thalf} \
    -visible

create_output -name data_o \
    -specify external \
    -launch_clock clk \
    -data_edges {1P 2P 3P} \
    -rclk_outputdly_max {$tSU} \
    -rclk_outputdly_min {-$tHO} \
    -visible
```

Change `Tclk`, `tSU` or `tHO`, and all signals and markers that reference those variables are recalculated and redrawn.

Read more in [Using timing variables](docs/17_timing_vars.md).

## Main capabilities

| Area | Capabilities |
|---|---|
| **Clocks** | Period, rise/fall positions, uncertainty and clock relationships |
| **Signals** | Input and output waveforms referenced to launch and capture clocks |
| **Timing specification** | Input delays, output delays, timing windows and symbolic expressions |
| **Diagram editing** | Create, copy, move, modify and remove signals interactively |
| **Measurements** | Timing markers between waveform points |
| **Annotations** | Text and colour annotations attached to waveform segments |
| **Layout** | Canvas scaling, signal spacing, grid configuration and display settings |
| **Automation** | Built-in Tcl command interpreter and reusable Tcl scripts |
| **Persistence** | Save and reload complete timing diagrams |
| **Export** | PNG, JPEG, SVG, PDF, EPS and PostScript |

## Examples

TimeIt includes reusable examples for several common digital interfaces:

| Example | Script |
|---|---|
| I²C frame | [`I2C_Frame.tcl`](scripts/I2C_Frame.tcl) |
| I²C frame with pull-up behaviour | [`I2C_Frame_pulledup.tcl`](scripts/I2C_Frame_pulledup.tcl) |
| JTAG timing | [`JTAG_Timing.tcl`](scripts/JTAG_Timing.tcl) |
| QSPI program instruction | [`QSPI_program_inst.tcl`](scripts/QSPI_program_inst.tcl) |
| SPI mode 0 | [`SPI_CPOL0_CPHA0.tcl`](scripts/SPI_CPOL0_CPHA0.tcl) |
| SWD timing | [`SWD_Timing.tcl`](scripts/SWD_Timing.tcl) |

<table>
  <tr>
    <td align="center">
      <img src="docs/screenshots/I2C_frame.png" alt="I2C frame created with TimeIt" width="430">
    </td>
    <td align="center">
      <img src="docs/screenshots/main_application_window.png" alt="TimeIt application window" width="430">
    </td>
  </tr>
  <tr>
    <td align="center"><strong>I²C frame example</strong></td>
    <td align="center"><strong>Interactive canvas and Tcl console</strong></td>
  </tr>
</table>

## Exporting diagrams

Use **File → Export Canvas…** or the Tcl command:

```tcl
# Vector output for technical documentation
export_canvas -file {diagram.svg}

# High-resolution raster output
export_canvas -file {diagram.png} -dpi 600 -background {#f0f0f0}

# Explicit output format
export_canvas -file {report/figure3} -format pdf
```

SVG and PDF preserve vector quality and are recommended for specifications and reports. See the [export guide](docs/08_export.md) for all supported options.

## Documentation

The complete user guide is available in [`docs/`](docs/).

| Topic | Guide |
|---|---|
| Overview and concepts | [Introduction](docs/00_introduction.md) |
| Installation | [How to install TimeIt](docs/01_install.md) |
| Application launch and layout | [How to launch TimeIt](docs/02_launch.md) |
| Clock creation | [Clock signals](docs/03_clock_signal.md) |
| Input and output signals | [I/O signals](docs/04_io_signals.md) |
| Timing measurements | [Timing markers](docs/05_timing_markers.md) |
| Saving and loading | [Save and load](docs/06_save_load.md) |
| Canvas export | [Exporting diagrams](docs/08_export.md) |
| Waveform annotations | [Annotations](docs/09_annotations.md) |
| Layout and display | [Waveform layout](docs/14_layout.md) |
| Built-in command help | [Command help](docs/15_command_help.md) |
| Parametric diagrams | [Timing variables](docs/17_timing_vars.md) |

For changes between versions, see the [changelog](CHANGELOG.md) and [release notes](https://github.com/pcardaba/TimeIt/releases).

## Why Python?

TimeIt is intentionally implemented in Python using the standard library and Tkinter/Tcl-Tk.

This design makes the application:

- easy to inspect and audit;
- suitable for restricted engineering environments;
- deployable as source code without administrator rights;
- independent of external package repositories;
- easy to customise for project-specific workflows;
- fully local, with no network connection made by the application.

The goal is not to compete with a native application on raw rendering performance. The goal is to provide a transparent, portable and practical timing-diagram tool for hardware engineers.

## Contributing

Bug reports, feature requests, documentation improvements, protocol examples and pull requests are welcome.

- Use [GitHub Issues](https://github.com/pcardaba/TimeIt/issues) to report a bug or suggest a feature.
- Use [Pull Requests](https://github.com/pcardaba/TimeIt/pulls) to propose a change.
- Include a minimal Tcl script when reporting a diagram-generation problem.
- Screenshots and exported files are useful when reporting rendering issues.

Before submitting a change, please keep the application’s main deployment goals in mind: offline operation, source transparency and minimal dependencies.

## Contact

For project-related questions:

**timeit.oss+contact@gmail.com**

## License

TimeIt is distributed under the [GNU General Public License version 3](LICENSE).

---

If TimeIt is useful to your work, consider giving the repository a star, sharing it with another digital hardware engineer, or contributing an example script.
