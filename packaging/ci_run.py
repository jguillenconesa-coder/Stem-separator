"""Expose useful failure details in public CI annotations without API credentials."""
from collections import deque
import subprocess
import sys

process = subprocess.Popen(sys.argv[1:], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, encoding='utf-8', errors='replace', bufsize=1)
tail = deque(maxlen=60)
for line in process.stdout:
    print(line, end='', flush=True)
    tail.append(line)
code = process.wait()
if code:
    details = ''.join(tail)[-10000:].replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print('::error title=Build command failed::' + details)
raise SystemExit(code)
