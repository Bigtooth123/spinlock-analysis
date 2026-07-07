import matplotlib.pyplot as plt
import numpy as np 

def plot_throughput(ticket_lock, mcs_lock):
    cores = [i for i in range(1, len(ticket_lock) + 1)]

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

    plt.savefig('theory_lock_throughput_comparison.png')
    plt.show() # 加上 show 顯示圖片

# ==========================================
# 繪製 P_k 機率分佈的函數
# ==========================================
def plot_pk(ticket_pk, mcs_pk, N):
    cores = np.arange(1, N + 1)
    width = 0.35  

    plt.figure(figsize=(10, 6))
    
    # 畫出並排的長條圖
    bars1 = plt.bar(cores - width/2, ticket_pk, width, label='Ticket Lock (Predicted)', color='salmon', alpha=0.8, edgecolor='black')
    bars2 = plt.bar(cores + width/2, mcs_pk, width, label='MCS Lock (Predicted)', color='skyblue', alpha=0.8, edgecolor='black')

    # 在柱狀圖上方加上數值標籤
    def add_labels(bars):
        for bar in bars:
            height = bar.get_height()
            plt.annotate(f'{height:.2f}%',
                         xy=(bar.get_x() + bar.get_width() / 2, height),
                         xytext=(0, 3),  
                         textcoords="offset points",
                         ha='center', va='bottom', 
                         fontsize=8, rotation=45)

    add_labels(bars1)
    add_labels(bars2)

    plt.title(f'Theoretical State Probability Distribution ($P_k$) at N={N}', fontsize=14, fontweight='bold')
    plt.xlabel('Number of threads in system ($k$)', fontsize=12)
    plt.ylabel('Probability (%)', fontsize=12)
    plt.xticks(cores)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend(fontsize=12)
    plt.tight_layout()

    plt.savefig(f'theory_pk_distribution_{N}.png')
    plt.show()


# ==========================================
# [1] 物理參數設定區 (單位: 奈秒 ns)
# ==========================================
E = 10.0        # 臨界區執行時間 (對應 for i<50)
T_arrive = 50.0 # 休息與重新發起請求的時間 (對應 for i<200)
c = 60.0        # 跨 CPU 快取無效化與交接成本
MAX_N = 8       # 模擬的最大核心數

# ==========================================
# [2] Ticket Lock 馬可夫鏈預測函數
# ==========================================
def predict_ticket_lock(N, E, T_arrive, c):
    W = [0.0] * (N + 1)
    W[0] = 1.0  
    
    for k in range(1, N + 1):
        A_k = (N - (k - 1)) / T_arrive  
        if k == 1:
            S_k = 1.0 / E                   
        else:
            S_k = 1.0 / (E + (k * c) / 2.0) 
            
        W[k] = W[k-1] * (A_k / S_k)
        
    total_W = sum(W)
    P = [w / total_W for w in W]
    
    expected_throughput = 0.0
    for k in range(1, N + 1):
        if k == 1:
            S_k = 1.0 / E
        else:
            S_k = 1.0 / (E + (k * c) / 2.0)
        expected_throughput += P[k] * S_k
        
    return expected_throughput * 1e9, P

# ==========================================
# [3] MCS Lock 馬可夫鏈預測函數
# ==========================================
def predict_mcs_lock(N, E, T_arrive, c):
    W = [0.0] * (N + 1)
    W[0] = 1.0
    
    for k in range(1, N + 1):
        A_k = (N - (k - 1)) / T_arrive
        if k == 1:
            S_k = 1.0 / E          
        else:
            S_k = 1.0 / (E + c)    
            
        W[k] = W[k-1] * (A_k / S_k)
        
    total_W = sum(W)
    P = [w / total_W for w in W]
    
    expected_throughput = 0.0
    for k in range(1, N + 1):
        if k == 1:
            S_k = 1.0 / E
        else:
            S_k = 1.0 / (E + c)
        expected_throughput += P[k] * S_k
        
    return expected_throughput * 1e9, P

# ==========================================
# [4] 主程式：印出數據對比表並繪圖
# ==========================================
print(f"=== 物理參數設定 ===")
print(f"臨界區執行時間 (E): {E} ns")
print(f"請求到達間隔 (T): {T_arrive} ns")
print(f"快取交接成本 (c): {c} ns\n")

print(f"{'核心數(N)':<10} | {'Ticket 預測 (次/秒)':<20} | {'MCS 預測 (次/秒)':<20}")
print("-" * 55)

ticket_lock = []
mcs_lock = []

for n in range(1, MAX_N + 1): # n 代表參預競爭的核心數量
    ticket_ops, ticket_P = predict_ticket_lock(n, E, T_arrive, c)
    mcs_ops, mcs_P = predict_mcs_lock(n, E, T_arrive, c)

    print(f"{n:<10} | {int(ticket_ops):<20,} | {int(mcs_ops):<20,}")

    ticket_lock.append(ticket_ops)
    mcs_lock.append(mcs_ops)
    
    # 處理並繪製 P_k 機率直方圖 (取出 k=1 到 k=n，並轉成百分比)
    ticket_pk_percent = [p * 100 for p in ticket_P[1:]]
    mcs_pk_percent = [p * 100 for p in mcs_P[1:]]

    plot_pk(ticket_pk_percent, mcs_pk_percent, n)

print("-" * 55)

# 1. 繪製並儲存 Throughput 折線圖
plot_throughput(ticket_lock, mcs_lock)