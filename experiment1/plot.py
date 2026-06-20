import matplotlib.pyplot as plt

cores = [1, 2, 3, 4, 5, 6, 7, 8]
ticket_lock = [16638523 + 16921260, 25296468 + 25408638, 13949029 + 14396481, 11714140 + 11795145, 8613645 + 9176290, 7556864 + 7885566, 6568712 + 7113296, 5751216 + 5791345]
mcs_lock = [16770505 + 16737875, 23014607 + 23536827, 15918493 + 16301237, 16686074 + 16549528, 15267013 + 16109687, 14742294 + 15187926, 14050993 + 14798794, 13733795 + 14714680]

ticket_lock = [x / 2 for x in ticket_lock]
mcs_lock = [x / 2 for x in mcs_lock]

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