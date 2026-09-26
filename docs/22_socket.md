# How to drive TimeIt from another program (remote console over a socket)

TimeIt is driven by its Tcl console: every command a script, a dialog or the console runs goes through the same interpreter. The utility script `scripts/timeit_socket.tcl` exposes that console on a TCP socket, so any program able to open a socket can drive the running TimeIt: a terminal tool such as `nc` or `telnet`, a Python script, an IDE task, or an AI assistant or agent, on the same machine or, when allowed, from another one.

The script is opt-in: TimeIt opens no socket unless it is sourced. Everything received over the socket is run **as if it had been typed in the console**: same command set, the line echoed in the history pane, written to the command log, and whatever the console prints for it sent back to the remote side. The local console keeps working at the same time, so the diagram can be driven from both.

## Starting the server

Start TimeIt as usual and, in the console, source the script:

```tcl
source /path/to/TimeIt/scripts/timeit_socket.tcl
```

**File → Load Script** works too. The script's first line, `# TimeIt utility script`, tells TimeIt that the file is not a diagram: it is sourced without becoming the current file (so a later **Ctrl+S** saves the diagram, never over the script) and without clearing the diagram. Any script starting with that line is treated this way.

The history pane reports where the server listens:

```
timeit_socket: listening on 127.0.0.1:7777
```

The default port is **7777**. When it is busy the next ports are tried in turn (7778, 7779, … up to ten), each failure is reported, and the port that worked is the one printed. `::timeit_socket::status` prints it again at any time.

## Connecting

One command per line, terminated by a newline (the client must flush on `<Enter>`). The reply to a command is exactly what the history pane shows for it, followed by the prompt `% `. From a terminal:

```
$ nc localhost 7777
TimeIt console over socket. One command per line; "help" lists the commands; "exit" disconnects.
% create_clock -name clk -topology source -period {10} -rise_at {0} -fall_at {5} -show 4 -visible
% create_input -name d -launch_clock clk -high_edges {2P} -low_edges {0} -visible
% expr {3 * 4}
12
% exit
bye
```

From Python:

```python
import socket

s = socket.create_connection(("127.0.0.1", 7777))
s.sendall(b"help\n")
print(s.recv(4096).decode())
```

## Protocol details

- A line whose braces, brackets or quotes are still open is held: the continuation prompt `> ` is sent and the block runs when the closing line arrives, as in the console.
- A client can read up to the `% ` prompt to know a command has finished. The prompts can be disabled by setting `::timeit_socket::prompt` and `::timeit_socket::prompt_more` to the empty string.
- `exit` or `quit` alone on a line closes that connection only; TimeIt keeps running. Several clients may be connected at once.
- Errors come back as the same `Error: …` line the pane shows.
- The socket is served by the Tk event loop: a command runs when TimeIt is idle, and a long one (a large `source`) delays the next.
- Lines received over the socket are not undo steps, exactly like lines typed in the console.

## Controlling the server

| Command | Effect |
|---|---|
| `::timeit_socket::start ?port? ?addr?` | (Re)start the server. Sourcing the script calls it with the defaults. |
| `::timeit_socket::stop` | Close the server and every client. |
| `::timeit_socket::status` | Print where the server listens and how many clients are connected. |

The defaults (`port_default`, `port_tries`, `bind_addr`, `prompt`, `prompt_more`) can be preset before sourcing:

```tcl
namespace eval ::timeit_socket {variable port_default 9000}
source /path/to/TimeIt/scripts/timeit_socket.tcl
```

## Remote access and security

By default the server binds to `127.0.0.1`: only programs on the same machine can connect. To accept connections from other machines, bind to all interfaces:

```tcl
::timeit_socket::start 7777 0.0.0.0
```

Anyone who can reach the port then runs arbitrary Tcl, including file access and `exec`, with the rights of the TimeIt process. Only do this on a trusted network, with the port firewalled to the hosts that need it.

## Reading and saving the diagram from the socket

`write_script -file {/tmp/state.tcl} -copy` writes the complete diagram as a script without changing the user's current file: a program can read it back to know the state. `write_script -file {...}` (without `-copy`) saves and makes the file the current one, and a bare `write_script` rewrites the current file, as Ctrl+S does.

## The `console_eval` command

The script is built on one command, `console_eval <script>`, which runs a script exactly as a line typed in the console and returns everything the console printed for it (results, `puts` output, help notices, error lines). It is available in the console too:

```tcl
set out [console_eval {help}]
```

See `console_eval -help` for the details.
