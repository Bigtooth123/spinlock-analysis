import math
import matplotlib.pyplot as plt

def plot(ticket_lock, mcs_lock):
    cores = [1, 2, 3, 4, 5, 6, 7, 8]

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





# ==========================================
# [1] 物理參數設定區 (單位: 奈秒 ns)
# ==========================================
E = 10.0        # 臨界區執行時間 (對應 for i<50)
T_arrive = 50.0 # 休息與重新發起請求的時間 (對應 for i<200)
c = 50.0        # 跨 CPU 快取無效化與交接成本
MAX_N = 8       # 模擬的最大核心數

# ==========================================
# [2] Ticket Lock 馬可夫鏈預測函數
# ==========================================
def predict_ticket_lock(N, E, T_arrive, c):
    W = [0.0] * (N + 1)
    W[0] = 1.0  # 狀態 0 (無人排隊) 的基準權重
    
    # 迭代計算每個狀態的權重 W[k]
    for k in range(1, N + 1):
        A_k = (N - (k - 1)) / T_arrive  # 推力 (到達率)
        if k == 1:
            S_k = 1.0 / E                   # Fast Path: 沒人排隊，無交接成本
        else:
            S_k = 1.0 / (E + (k * c) / 2.0) # Slow Path: 發生踩踏，交接成本從 1c 算起
            
        W[k] = W[k-1] * (A_k / S_k)
        
    # 歸一化，計算出各狀態的真實發生機率 P[k]
    total_W = sum(W)
    P = [w / total_W for w in W]
    
    # 計算期望值吞吐量
    expected_throughput = 0.0
    for k in range(1, N + 1):
        # 【修改點 2】期望值計算也要同步套用分段函數
        if k == 1:
            S_k = 1.0 / E
        else:
            S_k = 1.0 / (E + (k * c) / 2.0)
        expected_throughput += P[k] * S_k
        
    # 將 (次/奈秒) 轉換為 (次/秒)
    return expected_throughput * 1e9, P

# ==========================================
# [3] MCS Lock 馬可夫鏈預測函數
# ==========================================
def predict_mcs_lock(N, E, T_arrive, c):
    W = [0.0] * (N + 1)
    W[0] = 1.0
    
    for k in range(1, N + 1):
        A_k = (N - (k - 1)) / T_arrive
        
        # 實作 MCS 的「分段函數」：有沒有人排隊，決定了 Fast/Slow path
        if k == 1:
            S_k = 1.0 / E          # Fast Path: 沒人排隊，無交接成本
        else:
            S_k = 1.0 / (E + c)    # Slow Path: 有人排隊，固定常數交接成本
            
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
# [4] 主程式：印出數據對比表
# ==========================================
print(f"=== 物理參數設定 ===")
print(f"臨界區執行時間 (E): {E} ns")
print(f"請求到達間隔 (T): {T_arrive} ns")
print(f"快取交接成本 (c): {c} ns\n")

print(f"{'核心數(N)':<10} | {'Ticket 預測 (次/秒)':<20} | {'MCS 預測 (次/秒)':<20}")
print("-" * 55)

ticket_lock = []
mcs_lock = []

for n in range(1, MAX_N + 1):
    ticket_ops, ticket_P = predict_ticket_lock(n, E, T_arrive, c)
    mcs_ops, mcs_P = predict_mcs_lock(n, E, T_arrive, c)

    # 格式化輸出，加上逗號方便閱讀
    print(f"{n:<10} | {int(ticket_ops):<20,} | {int(mcs_ops):<20,}")

    ticket_lock.append(ticket_ops)
    mcs_lock.append(mcs_ops)
    

print("-" * 55)


plot(ticket_lock, mcs_lock)