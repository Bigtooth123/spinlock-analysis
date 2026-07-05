import matplotlib.pyplot as plt
import numpy as np

# Measured percentage data (P_1 to P_8)
# 填入測量數值
ticket_pk = [0.01, 0.00, 0.00, 0.00, 0.00, 0.03, 10.25, 89.70] 
mcs_pk    = [0.01, 0.01, 0.01, 0.01, 0.04, 0.73, 42.70, 56.50]

cores = np.arange(1, 9)
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

plt.title(f'Theoretical State Probability Distribution ($P_k$) at N=8', fontsize=14, fontweight='bold')
plt.xlabel('Number of Queued Threads ($k$)', fontsize=12)
plt.ylabel('Probability (%)', fontsize=12)
plt.xticks(cores)
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.legend(fontsize=12)

plt.tight_layout()
plt.savefig('pk_distribution_comparison.png')
plt.show()