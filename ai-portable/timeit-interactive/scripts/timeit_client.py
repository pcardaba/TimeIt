#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Send commands to a running TimeIt over its socket console and print the replies.

TimeIt must be running with scripts/timeit_socket.tcl sourced (or started with
timeit_serve.py). Standard library only.

    timeit_client.py 'help'                          one command
    timeit_client.py 'cmd 1' 'cmd 2'                 several, in order
    timeit_client.py --file diagram.tcl              send a script line by line
    timeit_client.py --file d.tcl 'export_canvas -file /tmp/d.svg'   script first, then commands
    timeit_client.py < commands.txt                  read commands from stdin
    timeit_client.py --probe                         find the server, print its port

The server is looked for on 127.0.0.1, ports 7777 to 7786 (the range the socket
script falls back over), unless --host/--port or TIMEIT_HOST/TIMEIT_PORT say
otherwise. The reply of every command is printed as the TimeIt history pane
shows it. Exit status is 1 when any reply contains an "Error:" line, 2 when no
server was found or the connection broke.
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
import time

BANNER = "TimeIt console over socket"
PROMPT = "% "
PROMPT_MORE = "> "
DEFAULT_PORTS = range(7777, 7787)


class TimeItClient:
    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.timeout = timeout
        self.banner = self._read_until_prompt()

    def _read_until_prompt(self) -> str:
        """Read until the text ends with a prompt; return it without the prompt."""
        buf = b""
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                chunk = self.sock.recv(65536)
            except socket.timeout:
                chunk = b""
            if chunk:
                buf += chunk
                text = buf.decode("utf-8", errors="replace")
                if text.endswith(PROMPT) or text.endswith(PROMPT_MORE):
                    self.last_prompt = text[-2:]
                    return text[:-2]
            elif chunk == b"" and not self.sock.gettimeout():
                raise ConnectionError("connection closed by TimeIt")
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"no prompt from TimeIt within {self.timeout}s; got {buf!r}")

    def run(self, command: str) -> str:
        """Send one command (may span lines) and return what TimeIt printed."""
        ## Line by line, as a terminal would: a block held open by the server
        ## answers "> " to each line and prints when it closes, so the replies
        ## of every line are kept (a script may hold several complete blocks).
        reply = ""
        for line in command.split("\n"):
            self.sock.sendall(line.encode("utf-8") + b"\n")
            reply += self._read_until_prompt()
        if self.last_prompt == PROMPT_MORE:
            ## Unbalanced braces/quotes: the server waits for more. Cancel.
            raise ValueError(
                "command is incomplete (unbalanced braces, brackets or quotes):\n"
                + command)
        return reply

    def close(self) -> None:
        try:
            self.sock.sendall(b"exit\n")
        except OSError:
            pass
        self.sock.close()


def probe(host: str, ports, timeout: float = 1.0) -> int | None:
    """First port in ``ports`` that answers with the TimeIt banner."""
    for port in ports:
        try:
            c = TimeItClient(host, port, timeout)
        except (OSError, TimeoutError):
            continue
        ok = c.banner.startswith(BANNER)
        c.close()
        if ok:
            return port
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("commands", nargs="*", help="Tcl commands, one per argument")
    ap.add_argument("--host", default=os.environ.get("TIMEIT_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int,
                    default=int(os.environ["TIMEIT_PORT"]) if os.environ.get("TIMEIT_PORT") else None,
                    help="server port (default: probe 7777-7786)")
    ap.add_argument("--file", help="send this script file, line by line")
    ap.add_argument("--timeout", type=float, default=60.0,
                    help="seconds to wait for each reply (default 60)")
    ap.add_argument("--probe", action="store_true",
                    help="only find the server and print host:port")
    ap.add_argument("--quiet", action="store_true", help="do not echo the commands")
    args = ap.parse_args()

    port = args.port
    if port is None:
        port = probe(args.host, DEFAULT_PORTS)
        if port is None:
            print(f"no TimeIt socket server found on {args.host} ports "
                  f"{DEFAULT_PORTS.start}-{DEFAULT_PORTS.stop - 1}. Is TimeIt running "
                  "with scripts/timeit_socket.tcl sourced?", file=sys.stderr)
            return 2
    if args.probe:
        print(f"{args.host}:{port}")
        return 0

    ## The script file goes first, then the command arguments: "load this
    ## diagram, then export it" is the common shape.
    commands = []
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            commands.append(f.read().rstrip("\n"))
    commands += list(args.commands)
    if not commands and not sys.stdin.isatty():
        commands.append(sys.stdin.read().rstrip("\n"))
    if not commands:
        ap.error("no command given (arguments, --file or stdin)")

    try:
        client = TimeItClient(args.host, port, args.timeout)
    except OSError as exc:
        print(f"cannot connect to {args.host}:{port}: {exc}", file=sys.stderr)
        return 2

    status = 0
    try:
        for cmd in commands:
            if not args.quiet:
                print("% " + cmd.replace("\n", "\n> "))
            reply = client.run(cmd)
            if reply:
                sys.stdout.write(reply if reply.endswith("\n") else reply + "\n")
            if any(line.startswith("Error:") for line in reply.splitlines()):
                status = 1
            sys.stdout.flush()
    except (OSError, TimeoutError, ValueError) as exc:
        print(f"timeit_client: {exc}", file=sys.stderr)
        return 2
    finally:
        client.close()
    return status


if __name__ == "__main__":
    sys.exit(main())
