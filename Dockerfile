FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv gcc-riscv64-linux-gnu binutils-riscv64-linux-gnu qemu-user && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install 'pytest>=8,<10' 'pytest-timeout>=2,<3'
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /work
CMD ["python", "run_tests.py"]
