"""Compile and run the direct route checks or the benchmark."""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
output = ROOT / '.build' / 'Java'
output.mkdir(parents=True, exist_ok=True)
sources = sorted((ROOT / 'src' / 'Java').glob('*.java'))
subprocess.run(['javac', '--release', '17', '-encoding', 'UTF-8', '-d', str(output),
                *map(str, sources), str(ROOT / 'tests' / 'JavaChecks.java')], check=True, timeout=60)
command = ['java', '-Xmx384m', '-cp', str(output), 'Main']
mode = 'benchmark' if '--benchmark' in sys.argv else 'routes'
result = subprocess.run(command[:-1] + ['JavaChecks', mode], capture_output=True,
                        text=True, encoding='utf-8', check=True, timeout=60)
(ROOT / 'tests' / (mode + '_results.txt')).write_text(result.stdout, encoding='utf-8')
print(result.stdout, end='')
