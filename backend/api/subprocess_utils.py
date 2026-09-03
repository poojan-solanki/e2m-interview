"""Runs a subprocess while streaming its stdout/stderr live to a logger, instead of
buffering everything until it exits. SAM 3 segmentation and the diffusion render
each take minutes — with plain subprocess.run(capture_output=True), nothing is
visible until the process finishes or times out. This streams each line to the
logger as it's printed, so progress is visible in the uvicorn console in real time.
"""

import logging
import subprocess
import threading
from typing import List, Tuple


def run_streaming(cmd: List[str], cwd: str, timeout: int, logger: logging.Logger) -> Tuple[int, str, str]:
    """Runs cmd, logging each stdout/stderr line as it arrives. Returns
    (returncode, full_stdout, full_stderr) — same shape as subprocess.run's
    (.returncode, .stdout, .stderr) so callers can swap this in with minimal change.
    """
    logger.info("$ %s", " ".join(cmd))
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    stdout_lines: List[str] = []
    stderr_lines: List[str] = []

    def _pump(stream, sink: List[str], level: int) -> None:
        for line in iter(stream.readline, ""):
            line = line.rstrip("\n")
            if line:
                logger.log(level, "  | %s", line)
                sink.append(line)
        stream.close()

    t_out = threading.Thread(target=_pump, args=(proc.stdout, stdout_lines, logging.INFO), daemon=True)
    t_err = threading.Thread(target=_pump, args=(proc.stderr, stderr_lines, logging.WARNING), daemon=True)
    t_out.start()
    t_err.start()

    try:
        returncode = proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        logger.error("subprocess exceeded %ss timeout — killing", timeout)
        proc.kill()
        proc.wait()
        t_out.join(timeout=2)
        t_err.join(timeout=2)
        raise

    t_out.join(timeout=5)
    t_err.join(timeout=5)

    logger.info("exit code %s", returncode)
    return returncode, "\n".join(stdout_lines), "\n".join(stderr_lines)
