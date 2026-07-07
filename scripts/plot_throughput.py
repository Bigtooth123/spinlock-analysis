import matplotlib.pyplot as plt

from benchmark_runner import collect_throughput

#這邊的 thread 代表在 C 語言中最多可以啟動幾顆核心參與競爭，我的電腦只有 8 顆核心
MAX_THREADS = 8
RUNS = 1

print("Compiling and running lock benchmarks...")
ticket_lock, mcs_lock = collect_throughput(max_threads=MAX_THREADS, runs=RUNS)
cores = list(range(1, MAX_THREADS + 1))

print("\nMeasured throughput:")
print(f"{'cores':<8} {'ticket_lock':<15} {'mcs_lock':<15}")
for core, ticket, mcs in zip(cores, ticket_lock, mcs_lock):
    print(f"{core:<8} {int(ticket):<15,} {int(mcs):<15,}")

plt.figure(figsize=(10, 6))
plt.plot(cores, ticket_lock, marker='o', linestyle='-', linewidth=2, label='Ticket Lock')
plt.plot(cores, mcs_lock, marker='s', linestyle='-', linewidth=2, label='MCS Lock')

plt.title('Throughput Comparison: Ticket Lock vs MCS Lock', fontsize=14)
plt.xlabel('Number of Cores', fontsize=12)
plt.ylabel('Throughput (Operations / Second)', fontsize=12)
plt.xticks(cores)
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend(fontsize=12)
plt.tight_layout()

plt.savefig('lock_throughput_comparison.png')
