#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <sched.h>
#include <unistd.h>
#include <stdint.h>
#include <stdatomic.h>

typedef struct {
    atomic_uint ticket;
    atomic_uint serving;
} ticket_lock_t;

void ticket_lock_init(ticket_lock_t *l) {
    atomic_init(&l->ticket, 0);
    atomic_init(&l->serving, 0);
}

void ticket_lock_acquire(ticket_lock_t *l) {
    unsigned int my_ticket = atomic_fetch_add_explicit(&l->ticket, 1, memory_order_acquire);
    
    // 自旋
    while (atomic_load_explicit(&l->serving, memory_order_acquire) != my_ticket) {
        __asm__ __volatile__("pause" ::: "memory"); // x86 暫停指令
    }
}

void ticket_lock_release(ticket_lock_t *l) {
    unsigned int current = atomic_load_explicit(&l->serving, memory_order_relaxed);
    atomic_store_explicit(&l->serving, current + 1, memory_order_release);

    //不要用這個會影響速度 atomic_fetch_add_explicit(&l->serving, 1, memory_order_release);
}




// ==========================================
// 實驗環境設定與全域變數
// ==========================================
// 前四個是大核，後四個是小核
int target_cpus[] = {0, 2, 4, 6, 1, 3, 5, 7};

ticket_lock_t my_lock;
volatile uint64_t global_counter = 0; // 共享臨界區資源
atomic_int running = 1;               // 實驗執行旗標
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

    while (atomic_load_explicit(&running, memory_order_relaxed)) {
        ticket_lock_acquire(&my_lock);
        
        // --- Critical Section ---
        global_counter++; 
        for(volatile int i=0; i<50; i++); // 模擬鎖持有時間 (E)
        // ---------------------------------
        
        ticket_lock_release(&my_lock);
        local_ops++;
        
        // 模擬再次發出請求的間隔 (T_arrive)
        for(volatile int i=0; i<200; i++); 
    }

    thread_ops[thread_id] = local_ops;
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
    ticket_lock_init(&my_lock);

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

    // 印出實驗結果
    printf("核心數: %d | 總吞吐量 (次/秒): %lu | 計數器最終值: %lu\n", 
           num_threads, total_ops, global_counter);
           
    return 0;
}
