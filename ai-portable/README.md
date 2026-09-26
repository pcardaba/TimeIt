# AI-portable material

Files meant to be copied out of this repository into an AI assistant or agent
environment, so that the assistant can drive TimeIt on the user's behalf.

## `timeit-interactive/` — an agent skill

A skill in the [Agent Skills](https://agentskills.io) format (a `SKILL.md` with
a name and description, plus bundled `scripts/` and `references/`), the format
read by Claude Code and by a growing number of other agents. It teaches an
assistant how to reach a running TimeIt through the socket console opened by
`scripts/timeit_socket.tcl`, how to learn the command set from TimeIt itself
(`help`, `help <command>`) and from the online documentation, and how to build,
check and hand over a diagram.

```
timeit-interactive/
├── SKILL.md                    instructions (loaded when the skill triggers)
├── references/quickstart.md    the concepts behind the command options
└── scripts/
    ├── timeit_client.py        send commands to the socket, print the replies
    └── timeit_serve.py         start TimeIt with the socket console already open
```

Both scripts use the Python standard library only, like TimeIt itself.

### Installing

- **Claude Code**: copy the `timeit-interactive/` directory into `.claude/skills/`
  of a project (project-wide) or `~/.claude/skills/` (every project). The skill
  is then invoked automatically when TimeIt or a timing diagram comes up, or
  explicitly with `/timeit-interactive`.
- **Claude.ai / Claude Desktop**: upload the directory as a custom skill
  (Settings → Capabilities → Skills), or zip it and upload the archive.
- **Other agents that read `SKILL.md`** (Codex, Cursor, Gemini CLI, OpenCode,
  ...): put the directory where that tool looks for skills; check its
  documentation for the path.
- **Any chat assistant with no skill support**: paste the content of `SKILL.md`
  as a system prompt or "custom instructions", and give the assistant a way to
  run `scripts/timeit_client.py` (or let it open the socket itself: the protocol
  is plain text, one command per line, reply ends with `% `).

### Using

1. Start TimeIt and, in its console, `source /path/to/TimeIt/scripts/timeit_socket.tcl`
   (or let the assistant run `timeit_serve.py`, which does both).
2. Ask the assistant for a diagram in plain words: "draw an SPI mode 0 byte
   transfer at 10 MHz with chip select active low", "add 2 ns of output delay
   to `q`", "export it as SVG". The commands appear in TimeIt's history pane
   as they run and the drawing updates live.
3. Save from TimeIt (Ctrl+S) when happy, or ask the assistant to save it
   (`write_script`) to a file of your choice.

The server only listens on `127.0.0.1` unless told otherwise. Opening it to other
hosts lets anyone who reaches the port run arbitrary Tcl in the TimeIt process;
see the header of `scripts/timeit_socket.tcl`.
