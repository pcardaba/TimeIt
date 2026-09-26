# TimeIt utility script
# ============================================================================
# timeit_socket.tcl -- drive TimeIt from another program over a TCP socket
# ============================================================================
#
# WHAT IT IS
#
#   A utility script for TimeIt (not a diagram). Once sourced in a running
#   TimeIt, it listens on a TCP port and turns the connection into a remote
#   TimeIt console: every line received is run exactly as if it had been typed
#   in the TimeIt Tcl console (same command set, echoed in the history pane,
#   written to the command log), and whatever the console prints for it is
#   sent back to the remote side. The local console keeps working as usual, so
#   the diagram can be driven from both at the same time. Any program able to
#   open a socket can use it: a terminal tool (nc, telnet), a script, an IDE,
#   an AI assistant or agent, locally or from another machine.
#
# HOW TO USE IT
#
#   1. Start TimeIt as usual (python3 -m TimeIt.main).
#   2. In the TimeIt console type:
#
#          source /path/to/TimeIt/scripts/timeit_socket.tcl
#
#      File -> Load Script also works: the "# TimeIt utility script" first
#      line tells TimeIt that this file is not a diagram, so it is sourced
#      without becoming the current file (a later Ctrl+S saves the diagram,
#      never over this script) and without clearing the diagram.
#   3. The history pane reports the port, for example:
#
#          timeit_socket: listening on 127.0.0.1:7777
#
#      The default port is 7777. If it is busy the next ones are tried in
#      turn (7778, 7779, ... up to 10 ports) and the one that worked is the
#      one reported. Read the pane (or run ::timeit_socket::status) to know
#      which port to connect to.
#   4. Connect from any other program and send commands, one per line:
#
#          nc localhost 7777
#          % create_clock -name clk -topology source -period {10} -rise_at {0} -fall_at {5} -show 4 -visible
#          % create_input -name d -launch_clock clk -high_edges {2P} -low_edges {0} -visible
#          % help
#          % exit
#
#      From Python:
#
#          import socket
#          s = socket.create_connection(("127.0.0.1", 7777))
#          s.sendall(b"help\n")
#          print(s.recv(4096).decode())
#
#      The ai-portable/timeit-interactive skill in the repository bundles a
#      ready-made client (timeit_client.py) and a launcher that starts TimeIt
#      with this server already open (timeit_serve.py).
#
# PROTOCOL
#
#   - Plain text, one command per line, UTF-8. A command is run when its
#     line is complete, i.e. when <Enter> (a newline) is received; clients
#     must therefore send the trailing newline (line buffering / flush).
#   - A line whose braces, brackets or quotes are still open (as reported by
#     Tcl's "info complete") is held, the continuation prompt "> " is sent,
#     and the block runs when the closing line arrives: multi-line commands
#     work as in the console.
#   - The response to a command is exactly what the history pane shows for
#     it (result, "puts" output, help notice or "Error: ..." line), followed
#     by the prompt "% " with no newline. A client can read up to that prompt
#     to know the command has finished. Set ::timeit_socket::prompt and
#     ::timeit_socket::prompt_more to "" to disable the prompts.
#   - "exit" or "quit" alone on a line closes the connection (it does not
#     close TimeIt). Several clients may be connected at once.
#   - The socket is served by the Tk event loop: a command runs when TimeIt
#     is idle, and a long one (a large "source") delays the next.
#   - Lines run through the console are not undo steps, exactly like lines
#     typed in the console.
#
# CONTROL
#
#   ::timeit_socket::start ?port? ?addr?   (re)start the server; sourcing this
#                                          file calls it with the defaults
#   ::timeit_socket::stop                  close the server and every client
#   ::timeit_socket::status                print where the server listens
#
# REMOTE ACCESS AND SECURITY
#
#   By default the server binds to 127.0.0.1: only programs on the same
#   machine can connect. To accept connections from other machines bind to
#   all interfaces:
#
#       ::timeit_socket::start 7777 0.0.0.0
#
#   or preset the default before sourcing (the same works for port_default,
#   port_tries, prompt and prompt_more):
#
#       namespace eval ::timeit_socket {variable bind_addr 0.0.0.0}
#       source /path/to/TimeIt/scripts/timeit_socket.tcl
#
#   Anyone who can reach the port then runs arbitrary Tcl (including file
#   access and "exec") with the rights of the TimeIt process: only do this on
#   a trusted network, with the port firewalled to the hosts that need it.
#
# ============================================================================

namespace eval ::timeit_socket {
    ## --- Configuration: presets (see header) are kept, else defaults ---
    if {![info exists port_default]} { variable port_default 7777 }
    if {![info exists port_tries]}   { variable port_tries   10 }
    if {![info exists bind_addr]}    { variable bind_addr    127.0.0.1 }
    if {![info exists prompt]}       { variable prompt       "% " }
    if {![info exists prompt_more]}  { variable prompt_more  "> " }

    ## --- State (kept across a re-source, so start can close the old server) ---
    if {![info exists server]}  { variable server "" }  ;# listening channel, "" when stopped
    if {![info exists port]}    { variable port   "" }  ;# port actually bound
    if {![info exists addr]}    { variable addr   "" }  ;# address actually bound
    if {![info exists clients]} { variable clients; array set clients {} }
    ;# clients: array, client channel -> pending (incomplete) script
}

## Messages to the history pane. "puts" is TimeIt's own, which prints in the
## pane; the socket channels are written with "chan puts" (see _send).
proc ::timeit_socket::_log {msg} {
    puts stdout "timeit_socket: $msg"
}

proc ::timeit_socket::_warn {msg} {
    puts stderr "timeit_socket: $msg"
}

## Bind the server socket. Tries port, port+1, ... port+port_tries-1 and
## returns the port bound, or "" (with a message in the pane) when none is
## free. An explicit addr of 0.0.0.0 or "*" listens on every interface.
proc ::timeit_socket::start {{first ""} {bindto ""}} {
    variable port_default
    variable port_tries
    variable bind_addr
    variable server
    variable port
    variable addr

    if {$server ne ""} { stop }

    if {$first eq ""} { set first $port_default }
    if {$bindto eq ""} { set bindto $bind_addr }
    if {![string is integer -strict $first] || $first < 1 || $first > 65535} {
        _warn "invalid port \"$first\""
        return ""
    }

    set opts {}
    if {$bindto ni {0.0.0.0 * ""}} { lappend opts -myaddr $bindto }

    set failures {}
    for {set i 0} {$i < $port_tries} {incr i} {
        set p [expr {$first + $i}]
        if {$p > 65535} { break }
        if {![catch {socket -server ::timeit_socket::_accept {*}$opts $p} chan]} {
            set server $chan
            set port $p
            set addr [expr {$bindto in {0.0.0.0 * ""} ? "0.0.0.0" : $bindto}]
            foreach f $failures { _log $f }
            _log "listening on $addr:$port"
            return $port
        }
        lappend failures "port $p not available ($chan), trying [expr {$p + 1}]"
    }
    foreach f $failures { _warn $f }
    _warn "could not open a listening socket (ports $first to [expr {$first + $port_tries - 1}])"
    return ""
}

## Close the server and every client.
proc ::timeit_socket::stop {} {
    variable server
    variable port
    variable addr
    variable clients

    foreach ch [array names clients] { _close_client $ch }
    if {$server ne ""} {
        catch {chan close $server}
        _log "server on $addr:$port closed"
    }
    set server ""
    set port ""
    set addr ""
}

proc ::timeit_socket::status {} {
    variable server
    variable port
    variable addr
    variable clients
    if {$server eq ""} {
        _log "not listening"
    } else {
        _log "listening on $addr:$port, [array size clients] client(s) connected"
    }
    return $port
}

## New connection: line mode, non-blocking, one pending script per client.
proc ::timeit_socket::_accept {ch host peerport} {
    variable clients
    variable prompt
    chan configure $ch -blocking 0 -buffering line -translation {auto lf} -encoding utf-8
    set clients($ch) ""
    chan event $ch readable [list ::timeit_socket::_readable $ch]
    _log "client $host:$peerport connected ($ch)"
    _send $ch "TimeIt console over socket. One command per line; \"help\" lists the commands; \"exit\" disconnects.\n$prompt"
}

proc ::timeit_socket::_close_client {ch} {
    variable clients
    if {[info exists clients($ch)]} {
        unset clients($ch)
        _log "client $ch disconnected"
    }
    catch {chan close $ch}
}

## Write to a client; a failed write (peer gone) drops the client.
proc ::timeit_socket::_send {ch text} {
    if {[catch {
        chan puts -nonewline $ch $text
        chan flush $ch
    }]} {
        _close_client $ch
    }
}

## One readable event: read the available line, run the script when complete.
proc ::timeit_socket::_readable {ch} {
    variable clients
    variable prompt
    variable prompt_more

    if {[catch {chan gets $ch line} count] || $count < 0} {
        ## No complete line yet, or the peer closed the connection.
        if {[catch {chan eof $ch} eof] || $eof} { _close_client $ch }
        return
    }

    if {$clients($ch) eq ""} {
        set clients($ch) $line
    } else {
        append clients($ch) \n $line
    }
    if {![info complete "$clients($ch)\n"]} {
        _send $ch $prompt_more
        return
    }

    set script $clients($ch)
    set clients($ch) ""
    set word [string trim $script]
    if {$word in {exit quit}} {
        _send $ch "bye\n"
        _close_client $ch
        return
    }
    if {$word eq ""} {
        _send $ch $prompt
        return
    }

    ## The console runs the script: echoed in the history pane, logged, and
    ## its printed output (results, puts, errors) comes back to us. At global
    ## level, as a typed line: run from this proc, a "set" or a timing
    ## variable would otherwise be local to this handler and vanish.
    set out [uplevel #0 [list console_eval $script]]
    ## A command may have closed this very client (e.g. ::timeit_socket::stop).
    if {![info exists clients($ch)]} { return }
    if {$out ne "" && [string index $out end] ne "\n"} { append out \n }
    _send $ch "$out$prompt"
}

## Sourcing the file starts the server with the configured defaults.
::timeit_socket::start
