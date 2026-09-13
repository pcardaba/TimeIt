# Tests

Standard-library `unittest` only, no extra dependency (same rule as the
application). Two kinds of tests live here:

- **Unit tests** of pure modules (no Tk needed). They import the module under
  test directly, e.g. `from TimeIt.classes.timeline import combine`.
- **Integration tests** that boot the real application and drive it through
  the Tcl interpreter, via `AppTestCase` in `apphelper.py`. They need a
  display (like the GUI) and are skipped, not failed, without one.

## Running

From the directory **one level above** the repository (the same place
`python3 -m TimeIt.main` is launched from):

```bash
python3 -m unittest discover -s TimeIt/tests -t .
```

One module or one test:

```bash
python3 -m unittest TimeIt.tests.test_apphelper
python3 -m unittest TimeIt.tests.test_apphelper.TestAppHelper.test_example_loads_and_round_trips
```

Headless machine:

```bash
xvfb-run -a python3 -m unittest discover -s TimeIt/tests -t .
```

`unittest` writes its report to stderr; read the final `OK` / `FAILED` line.

## Writing an integration test

```python
from TimeIt.tests.apphelper import AppTestCase, SCRIPTS

class TestThing(AppTestCase):
    def test_it(self):
        self.source(SCRIPTS / "SPI_CPOL0_CPHA0.tcl")   # load a diagram
        self.tcl("create_clock -name c2 -period {10} -visible")
        self.assertNoErrors()                          # console log is clean
        self.assertRoundTrips()                        # save -> load -> save is identical
```

`self.tcl(cmd)` evaluates on the shared interpreter and forces a redraw, so
render-time errors surface too. Command handlers report their errors in the
console log rather than raising: check them with `self.errors()` /
`self.assertError("fragment")`. `self.clear_log()` resets the capture.

The `regression-test` skill (`.claude/skills/regression-test`) is the
complementary smoke run: it sources every git-tracked `scripts/*.tcl` and
replays the VCD import. A new example script is picked up there
automatically once it is tracked.
