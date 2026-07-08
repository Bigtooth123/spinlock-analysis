#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <sched.h>
#include <unistd.h>
#include <stdint.h>
#include <stdatomic.h>

struct mcs_spinlock {
	_Atomic(struct mcs_spinlock *) next;
	atomic_int locked; /* 1 if lock acquired */
	int count;  /* nesting count, see qspinlock.c */
};

static inline void cpu_relax(void)
{
	__asm__ __volatile__("pause" ::: "memory");
}

static inline void mcs_spin_lock_init(_Atomic(struct mcs_spinlock *) *lock)
{
	atomic_store_explicit(lock, NULL, memory_order_relaxed);
}

void mcs_spin_lock(_Atomic(struct mcs_spinlock *) *lock,
		   struct mcs_spinlock *node)
{
	struct mcs_spinlock *prev;

	/* Init node */
	atomic_store_explicit(&node->locked, 0, memory_order_relaxed);
	atomic_store_explicit(&node->next, NULL, memory_order_relaxed);

    // prev = *lock;
    // *lock = node;
	prev = atomic_exchange_explicit(lock, node, memory_order_acq_rel);
	if (prev == NULL) {
		/*
		 * Lock acquired, don't need to set node->locked to 1. Threads
		 * only spin on its own node->locked value for lock acquisition.
		 * However, since this thread can immediately acquire the lock
		 * and does not proceed to spin on its own node->locked, this
		 * value won't be used. If a debug mode is needed to
		 * audit lock status, then set node->locked value here.
		 */
		return;
	}
	atomic_store_explicit(&prev->next, node, memory_order_release);

	/* Wait until the lock holder passes the lock down. */
    while (!atomic_load_explicit(&node->locked, memory_order_acquire))
		cpu_relax();
}

void mcs_spin_unlock(_Atomic(struct mcs_spinlock *) *lock,
		     struct mcs_spinlock *node)
{
	struct mcs_spinlock *next = atomic_load_explicit(&node->next, memory_order_acquire);

	if (!next) {
		struct mcs_spinlock *expected = node;

		// 再次確認，若是 NULL 則返回，說明自身是最後一個，無後續動作 
		if (atomic_compare_exchange_strong_explicit(lock,
							    &expected,
							    NULL,
							    memory_order_release,
							    memory_order_relaxed))
			return;
		/* Wait until the next pointer is set */
        // 否則說明在 if 判斷 next 為 NULL 和 atomic_compare_exchange_strong_explicit 之間有 node 插入了，
        // 所以 lock 不等於 expected，必須等到 next 被設置好才能繼續
		while (!(next = atomic_load_explicit(&node->next, memory_order_acquire)))
			cpu_relax();
	}

	/* Pass lock to next waiter. */
    atomic_store_explicit(&next->locked, 1, memory_order_release);
}



// ==========================================
//以下是用來紀錄各個時間的排隊情況與數量，避免 False Sharing，將每個旗標對齊 64 Byte
//並且會每 SAMPLE_RATE 次採樣 1 次，避免破壞 MCS spinlock 本地自旋的目的
// ==========================================
typedef struct {
    atomic_int in_queue;
    char padding[60]; // 填滿剩下的空間，確保每個 struct 獨佔一條 Cache Line
} __attribute__((aligned(64))) thread_state_t;
thread_state_t t_states[8];

//紀錄 P_k 機率的陣列
uint64_t thread_pk_hist[8][10] = {0}; 

//採樣頻率：每 100 次操作才擷取一次快照
#define SAMPLE_RATE 100



// ==========================================
// 實驗環境設定與全域變數
// ==========================================
// 前四個是大核，後四個是小核
int target_cpus[] = {0, 2, 4, 6, 1, 3, 5, 7};

_Atomic(struct mcs_spinlock *) my_lock;
uint64_t global_counter = 0; // 共享臨界區資源
atomic_int running = 1;      // 實驗執行旗標
uint64_t thread_ops[8] = {0};

// ==========================================
// 執行緒工作邏輯 (模擬爭搶 Spinlock)
// ==========================================
void* worker_thread(void* arg) {
    int thread_id = *(int*)arg;
    int cpu_id = target_cpus[thread_id];

    // 嚴格綁定 CPU，避免 OS 排程器干擾實驗結果
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(cpu_id, &cpuset);
    int rc = pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);
    if (rc != 0) {
        fprintf(stderr, "pthread_setaffinity_np failed: %d\n", rc);
    }

    uint64_t local_ops = 0;
    uint64_t local_hist[10] = {0}; // 區域統計，避免寫入全域變數
    struct mcs_spinlock node;

    atomic_store_explicit(&t_states[thread_id].in_queue, 0, memory_order_relaxed); // 用來紀錄該執行緒是否在排隊中初始化為 0

    while (atomic_load_explicit(&running, memory_order_relaxed)) {
        // 宣告自己準備進入鎖區間 (只寫入自己獨佔的 Cache Line，零干擾)
        atomic_store_explicit(&t_states[thread_id].in_queue, 1, memory_order_release);

        // 每 SAMPLE_RATE 次擷取一次系統採樣
        if (local_ops % SAMPLE_RATE == 0) {
            int k = 0;
            // 讀取所有人的旗標 (這會產生極短暫的 Cache Read，但頻率極低)
            for (int j = 0; j < 8; j++) {
                if (atomic_load_explicit(&t_states[j].in_queue, memory_order_acquire)) {
                    k++;
                }
            }
            if (k >= 1 && k <= 8) {
                local_hist[k]++;
            }
        }

        mcs_spin_lock(&my_lock, &node);
        
        // --- Critical Section ---
        global_counter++; 
        for(volatile int i=0; i<50; i++); // 模擬鎖持有時間 (E)
        // ---------------------------------
        
        mcs_spin_unlock(&my_lock, &node);
        atomic_store_explicit(&t_states[thread_id].in_queue, 0, memory_order_release);
        local_ops++;
        
        // 模擬再次發出請求的間隔 (T_arrive)
        for(volatile int i=0; i<200; i++); 
    }

    thread_ops[thread_id] = local_ops;
    for(int i = 1; i <= 8; i++) {
        thread_pk_hist[thread_id][i] = local_hist[i];
    }
    return NULL;
}







int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("用法: %s <執行緒數量 (1-8)>\n", argv[0]);
        return 1;
    }

    int num_threads = atoi(argv[1]);
    if (num_threads < 1 || num_threads > 8) {
        printf("錯誤: 執行緒數量必須介於 1 到 8 之間\n");
        return 1;
    }

    // 初始化鎖
    mcs_spin_lock_init(&my_lock);

    pthread_t threads[8];
    int thread_ids[8];

    // 啟動指定數量的執行緒
    for (int i = 0; i < num_threads; i++) {
        thread_ids[i] = i;
        pthread_create(&threads[i], NULL, worker_thread, &thread_ids[i]);
    }

    // 讓實驗狂跑 1 秒鐘
    sleep(1);
    atomic_store_explicit(&running, 0, memory_order_relaxed); // 通知所有 Thread 停火

    // 收集資料
    uint64_t total_ops = 0;
    for (int i = 0; i < num_threads; i++) {
        pthread_join(threads[i], NULL);
        total_ops += thread_ops[i];
    }



    // ==========================================
    // 印出吞吐量
    // ==========================================
    printf("核心數: %d | 總吞吐量 (次/秒): %lu | 計數器最終值: %lu\n", 
           num_threads, total_ops, global_counter);

    // ==========================================
    // 印出採樣到的 P_k 機率分佈
    // ==========================================
    uint64_t total_pk[9] = {0};
    uint64_t total_samples = 0;

    for (int i = 0; i < num_threads; i++) {
        for (int k = 1; k <= num_threads; k++) {
            total_pk[k] += thread_pk_hist[i][k];
            total_samples += thread_pk_hist[i][k];
        }
    }

    if (total_samples > 0) {
        printf("\n=== 狀態機率分佈 (P_k, 採樣數: %lu) ===\n", total_samples);
        for (int k = 1; k <= num_threads; k++) {
            double prob = (double)total_pk[k] / total_samples;
            printf("P_%d : %6.2f%% (%lu 次)\n", k, prob * 100.0, total_pk[k]);
        }
    }
           
    return 0;
}
