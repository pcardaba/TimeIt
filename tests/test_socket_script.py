# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""console_eval and the socket server script (scripts/timeit_socket.tcl).

The script turns a TCP connection into a remote console: a line received is
run through console_eval, which echoes it in the history pane and returns
what the pane printed, and that text goes back to the client. The tests
connect with a plain Python socket and pump the Tk event loop by hand, since
the server is driven by that loop.
"""

from __future__ import annotations

import socket
import time
import unittest

from TimeIt.tests.apphelper import AppTestCase, SCRIPTS

SOCKET_SCRIPT = SCRIPTS / "timeit_socket.tcl"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestConsoleEval(AppTestCase):

    def pane_text(self) -> str:
        return self.app.console._output.get("1.0", "end")

    def test_returns_what_the_pane_shows(self):
        out = self.tcl('console_eval {puts hello; expr {1 + 2}}')
        self.assertEqual(out, "hello\n3\n")
        ## Echoed like a typed line: prompt + command, and in the history.
        self.assertIn("% puts hello; expr {1 + 2}\n", self.pane_text())
        self.assertEqual(self.app.console.history[-1], "puts hello; expr {1 + 2}")

    def test_runs_timeit_commands(self):
        self.tcl("console_eval {create_clock -name clk -topology source -period {10} -rise_at {0} -fall_at {5} -show 4 -visible}")
        self.assertSignals("clk")
        self.assertNoErrors()

    def test_error_is_returned_not_raised(self):
        out = self.tcl("console_eval {expr {1 /}}")
        self.assertTrue(out.startswith("Error: "), out)
        self.assertError("Error: ")

    def test_handler_errors_are_returned_too(self):
        out = self.tcl("console_eval {create_input -name d -launch_clock nosuchclk}")
        self.assertIn("nosuchclk", out)

    def test_help_and_arity(self):
        self.tcl("console_eval -help")
        self.assertIn("console_eval", "".join(t for _, t in self.log))
        self.assertNoErrors()
        self.tcl("console_eval a b")
        self.assertError("exactly one argument")

    def test_captures_nest(self):
        ## The outer capture sees the puts output and, as for any typed line,
        ## the inner command's return value printed as a result.
        out = self.tcl("console_eval {console_eval {puts inner}}")
        self.assertEqual(out, "inner\ninner\n\n")


class SocketTestCase(AppTestCase):
    """Boots the server on a free port and offers a pumped client."""

    def setUp(self) -> None:
        super().setUp()
        self.port = free_port()
        self.clients: list[socket.socket] = []

    def tearDown(self) -> None:
        for c in self.clients:
            try:
                c.close()
            except OSError:
                pass
        try:
            self.app.console.interp.eval("::timeit_socket::stop")
        except Exception:  # noqa: BLE001 - never mask the test outcome
            pass
        super().tearDown()

    def start_server(self, port: int | None = None) -> None:
        port = self.port if port is None else port
        self.tcl(f"namespace eval ::timeit_socket {{variable port_default {port}}}")
        self.source(SOCKET_SCRIPT)

    def bound_port(self) -> int:
        return int(self.tcl("set ::timeit_socket::port"))

    def connect(self) -> socket.socket:
        c = socket.create_connection(("127.0.0.1", self.bound_port()), timeout=5)
        c.setblocking(False)
        self.clients.append(c)
        return c

    def read_until(self, c: socket.socket, marker: str, timeout: float = 5.0) -> str:
        """Pump the Tk loop until the client has received ``marker``."""
        data = b""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.root.update()
            try:
                chunk = c.recv(65536)
            except BlockingIOError:
                chunk = b""
            if chunk == b"" and data and marker.encode() in data:
                break
            data += chunk
            if marker.encode() in data:
                break
            time.sleep(0.01)
        text = data.decode("utf-8")
        self.assertIn(marker, text, f"timed out waiting for {marker!r}; got {text!r}")
        return text

    def send(self, c: socket.socket, line: str) -> None:
        c.sendall((line + "\n").encode("utf-8"))

    def command(self, c: socket.socket, line: str) -> str:
        """Send one line and return its response, prompt stripped."""
        self.send(c, line)
        text = self.read_until(c, "% ")
        return text[: text.rindex("% ")]


class TestSocketScript(SocketTestCase):

    def test_reports_port_and_answers_prompt(self):
        self.start_server()
        self.assertEqual(self.bound_port(), self.port)
        log = "".join(t for _, t in self.log)
        self.assertIn(f"listening on 127.0.0.1:{self.port}", log)
        c = self.connect()
        banner = self.read_until(c, "% ")
        self.assertIn("TimeIt console over socket", banner)

    def test_command_runs_and_is_logged_like_the_console(self):
        self.start_server()
        c = self.connect()
        self.read_until(c, "% ")
        out = self.command(c, "create_clock -name clk -topology source -period {10} -rise_at {0} -fall_at {5} -show 4 -visible")
        self.assertEqual(out, "")
        self.assertSignals("clk")
        self.assertNoErrors()
        pane = self.app.console._output.get("1.0", "end")
        self.assertIn("% create_clock -name clk -topology source -period {10} -rise_at {0} -fall_at {5} -show 4 -visible\n", pane)
        self.assertEqual(self.app.console.history[-1],
                         "create_clock -name clk -topology source -period {10} -rise_at {0} -fall_at {5} -show 4 -visible")

    def test_output_and_errors_come_back(self):
        self.start_server()
        c = self.connect()
        self.read_until(c, "% ")
        self.assertEqual(self.command(c, "puts hello; expr {6 * 7}"), "hello\n42\n")
        self.assertIn("Available commands", self.command(c, "help"))
        self.assertTrue(self.command(c, "expr {1 /}").startswith("Error: "))

    def test_multiline_block(self):
        self.start_server()
        c = self.connect()
        self.read_until(c, "% ")
        self.send(c, "if {1} {")
        self.read_until(c, "> ")
        out = self.command(c, "puts inside }")
        self.assertEqual(out, "inside\n")

    def test_console_keeps_working_alongside(self):
        self.start_server()
        c = self.connect()
        self.read_until(c, "% ")
        self.command(c, "create_clock -name clk -topology source -period {10} -rise_at {0} -fall_at {5} -show 4 -visible")
        self.app.console.execute("create_input -name d -launch_clock clk -high_edges {2P} -low_edges {0}")
        self.assertSignals("clk", "d")
        self.assertEqual(self.command(c, "llength [info commands create_*]").strip(),
                         str(len([n for n in self.app.console.commands
                                  if n.startswith("create_")])))

    def test_exit_closes_only_the_connection(self):
        self.start_server()
        c = self.connect()
        self.read_until(c, "% ")
        self.send(c, "exit")
        self.read_until(c, "bye")
        deadline = time.monotonic() + 5
        closed = False
        while time.monotonic() < deadline and not closed:
            self.root.update()
            try:
                closed = c.recv(10) == b""
            except BlockingIOError:
                time.sleep(0.01)
        self.assertTrue(closed)
        ## The server is still up and the app untouched.
        self.assertEqual(self.tcl("::timeit_socket::status"), str(self.port))
        c2 = self.connect()
        self.read_until(c2, "% ")

    def test_falls_back_to_next_port_when_busy(self):
        blocker = socket.socket()
        blocker.bind(("127.0.0.1", self.port))
        blocker.listen(1)
        try:
            self.start_server()
            self.assertEqual(self.bound_port(), self.port + 1)
            log = "".join(t for _, t in self.log)
            self.assertIn(f"port {self.port} not available", log)
            self.assertIn(f"listening on 127.0.0.1:{self.port + 1}", log)
        finally:
            blocker.close()

    def test_resourcing_restarts_on_the_same_port(self):
        self.start_server()
        self.start_server()
        self.assertEqual(self.bound_port(), self.port)
        c = self.connect()
        self.read_until(c, "% ")

    def test_stop(self):
        self.start_server()
        self.tcl("::timeit_socket::stop")
        with self.assertRaises(OSError):
            socket.create_connection(("127.0.0.1", self.port), timeout=1)
        self.assertEqual(self.tcl("::timeit_socket::status"), "")


if __name__ == "__main__":
    unittest.main()
