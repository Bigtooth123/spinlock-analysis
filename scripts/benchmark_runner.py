import re
import subprocess
import tempfile
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = ROOT_DIR / "benchmarks"

BENCHMARKS = {
    "ticket": BENCHMARK_DIR / "ticket_lock.c",
    "mcs": BENCHMARK_DIR / "mcs_lock.c",
}


def compile_benchmark(lock_name):
    source = BENCHMARKS[lock_name]
    output_dir = Path(tempfile.gettempdir()) / "qspinlock-analysis-benchmarks"
    output_dir.mkdir(parents=True, exist_ok=True)
    binary = output_dir / f"{lock_name}_lock"

    subprocess.run(
        [
            "gcc",
            str(source),
            "-pthread",
            "-o",
            str(binary),
        ],
        check=True,
    )

    return binary


def run_benchmark(binary, threads):
    result = subprocess.run(
        [str(binary), str(threads)],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def parse_throughput(output):
    match = re.search(r"總吞吐量 \(次/秒\):\s*(\d+)", output)
    if not match:
        raise ValueError(f"Cannot parse throughput from output:\n{output}")
    return int(match.group(1))


def parse_probabilities(output, threads):
    probabilities = [0.0] * threads

    for line in output.splitlines():
        match = re.search(r"P_(\d+)\s*:\s*([0-9.]+)%", line)
        if not match:
            continue

        k = int(match.group(1))
        if 1 <= k <= threads:
            probabilities[k - 1] = float(match.group(2))

    if not any(probabilities):
        raise ValueError(f"Cannot parse P_k distribution from output:\n{output}")

    return probabilities


def collect_throughput(max_threads=8, runs=1):
    binaries = {
        "ticket": compile_benchmark("ticket"),
        "mcs": compile_benchmark("mcs"),
    }

    ticket_values = []
    mcs_values = []

    for threads in range(1, max_threads + 1):
        ticket_samples = []
        mcs_samples = []

        for _ in range(runs):
            ticket_output = run_benchmark(binaries["ticket"], threads)
            mcs_output = run_benchmark(binaries["mcs"], threads)

            ticket_samples.append(parse_throughput(ticket_output))
            mcs_samples.append(parse_throughput(mcs_output))

        ticket_values.append(sum(ticket_samples) / len(ticket_samples))
        mcs_values.append(sum(mcs_samples) / len(mcs_samples))

    return ticket_values, mcs_values


def collect_probabilities(threads=8, runs=1):
    binaries = {
        "ticket": compile_benchmark("ticket"),
        "mcs": compile_benchmark("mcs"),
    }

    ticket_totals = [0.0] * threads
    mcs_totals = [0.0] * threads

    for _ in range(runs):
        ticket_output = run_benchmark(binaries["ticket"], threads)
        mcs_output = run_benchmark(binaries["mcs"], threads)

        ticket_pk = parse_probabilities(ticket_output, threads)
        mcs_pk = parse_probabilities(mcs_output, threads)

        ticket_totals = [a + b for a, b in zip(ticket_totals, ticket_pk)]
        mcs_totals = [a + b for a, b in zip(mcs_totals, mcs_pk)]

    ticket_avg = [value / runs for value in ticket_totals]
    mcs_avg = [value / runs for value in mcs_totals]

    return ticket_avg, mcs_avg
