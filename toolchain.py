"""Montagem e execução com limites de tempo. Sem shell intermediário."""
import shutil
import subprocess
import tempfile
from pathlib import Path
from executor import ExecutionResult

def build(assembly, output):
    gcc = shutil.which('riscv64-linux-gnu-gcc') or shutil.which('riscv64-elf-gcc')
    if gcc is None:
        raise RuntimeError('GNU RISC-V ausente. Use o contêiner fornecido.')
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp)/'program.S'
        source.write_text(assembly)
        subprocess.run([gcc, '-march=rv64im', '-mabi=lp64', '-nostdlib', '-static', '-no-pie', '-Wl,--no-relax', '-Wl,-e,_start', str(source), '-o', str(output)], check=True, capture_output=True, timeout=10)

def execute(assembly):
    qemu = shutil.which('qemu-riscv64')
    if qemu is None:
        raise RuntimeError('qemu-riscv64 ausente. Use o contêiner fornecido.')
    with tempfile.TemporaryDirectory() as tmp:
        binary = Path(tmp)/'program'
        build(assembly, binary)
        result = subprocess.run([qemu, str(binary)], capture_output=True, timeout=10)
        if len(result.stderr) != 8:
            raise RuntimeError(f'execução sem retorno de teste: {result.stderr!r}')
        value = int.from_bytes(result.stderr, 'little', signed=True)
        if result.returncode != value % 256:
            raise RuntimeError('status de execução incompatível')
        return ExecutionResult(result.stdout.decode('utf-8'), value, 0)
