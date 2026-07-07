import matplotlib.pyplot as plt
import numpy as np

from benchmark_runner import collect_probabilities

#這邊的 thread 代表在 C 語言啟動幾顆核心參與競爭
THREADS = 8
RUNS = 1

print("Compiling and running lock benchmarks...")
ticket_pk, mcs_pk = collect_probabilities(threads=THREADS, runs=RUNS)

print("\nMeasured state probability distribution:")
print(f"{'P_k':<8} {'ticket_lock':<15} {'mcs_lock':<15}")
for k, ticket, mcs in zip(range(1, THREADS + 1), ticket_pk, mcs_pk):
    print(f"P_{k:<6} {ticket:<15.2f} {mcs:<15.2f}")

cores = np.arange(1, THREADS + 1)
width = 0.35  # Bar width

plt.figure(figsize=(10, 6))

# Plot bars side by side and store the returned objects for labeling
bars1 = plt.bar(cores - width/2, ticket_pk, width, label='Ticket Lock (Measured)', color='salmon', alpha=0.8, edgecolor='black')
bars2 = plt.bar(cores + width/2, mcs_pk, width, label='MCS Lock (Measured)', color='skyblue', alpha=0.8, edgecolor='black')

# Function to add numerical labels on top of the bars
def add_labels(bars):
    for bar in bars:
        height = bar.get_height()
        # Show all labels regardless of the value
        plt.annotate(f'{height:.2f}%',
                     xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 3),  # 3 points vertical offset
                     textcoords="offset points",
                     ha='center', va='bottom', 
                     fontsize=8, rotation=45) # Added rotation to prevent overlap of small values

# Apply labels to both bar groups
add_labels(bars1)
add_labels(bars2)

plt.title(f'Measured State Probability Distribution ($P_k$) at N={THREADS}', fontsize=14, fontweight='bold')
plt.xlabel('Number of threads in system ($k$)', fontsize=12)
plt.ylabel('Probability (%)', fontsize=12)
plt.xticks(cores)
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.legend(fontsize=12)

plt.tight_layout()
plt.savefig('pk_distribution_comparison.png')
plt.show()
