#!/usr/bin/env python3
"""detach.py - start a long job in a session of its own, so it outlives the shell and the tool call that started it.

Linux and macOS alike: Python's start_new_session does what `setsid nohup ... &` does, and macOS has no setsid.
The job's output and errors go to --log, which is replaced; its stdin is /dev/null. Give absolute paths: the
shell's working directory resets between tool calls. Prints the job's pid, which leads the job's session and
process group, so `kill -- -<pid>` stops the job and everything it started. Poll the log on demand; never follow it.

  detach.py --log <abs log> -- <command> [args ...]

Exit 0 when the job is running (or already finished cleanly), 1 when it failed at once, 2 on a usage error.
"""
import os
import subprocess
import sys
import time

USAGE = "usage: detach.py --log <abs log> -- <command> [args ...]"


def main(argv):
    if len(argv) > 1 and argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if "--" not in argv:
        print(USAGE, file=sys.stderr)
        return 2
    cut = argv.index("--")
    opts, cmd = argv[1:cut], argv[cut + 1:]
    if len(opts) != 2 or opts[0] != "--log" or not cmd:
        print(USAGE, file=sys.stderr)
        return 2
    log = opts[1]
    if not os.path.isabs(log):
        print(f"--log must be an absolute path, got {log}", file=sys.stderr)
        return 2
    os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, "wb") as out:
        try:
            job = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        except OSError as e:
            print(f"could not start {cmd[0]}: {e}", file=sys.stderr)
            return 2
    time.sleep(0.5)
    rc = job.poll()
    if rc is not None:
        if rc != 0:
            print(f"the job exited {rc} at once; read {log}", file=sys.stderr)
            return 1
        print(f"the job finished at once (exit 0); log {log}")
        return 0
    print(f"detached: pid {job.pid} leads its own session and process group; log {log}; stop it with kill -- -{job.pid}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
