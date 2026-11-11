#define _GNU_SOURCE
#include <dlfcn.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>

enum { schedule_mask = 7, blocking = 4, hip_unknown_error = 999, hsa_error = 0x1000 };
typedef int (*HipInit)(unsigned);
typedef int (*GetFlags)(unsigned *);
typedef int (*SetFlags)(unsigned);
typedef int (*Synchronize)(void);
typedef struct { uint64_t handle; } Agent;
typedef struct Queue Queue;
typedef void (*QueueError)(int, Queue *, void *);
typedef int (*CreateQueue)(Agent, uint32_t, int, QueueError, void *, uint32_t, uint32_t, Queue **);

static pthread_once_t hip_once = PTHREAD_ONCE_INIT;
static pthread_once_t hsa_once = PTHREAD_ONCE_INIT;
static pthread_mutex_t startup_lock = PTHREAD_MUTEX_INITIALIZER;
static HipInit init_hip;
static GetFlags get_flags;
static SetFlags set_flags;
static Synchronize synchronize;
static CreateQueue create_queue;
static unsigned queues_started;
static int initialized;
static atomic_int configured;
static atomic_uint syncs;

static void load_hip(void)
{
    void *hip = dlopen("libamdhip64.so.7", RTLD_NOW | RTLD_NOLOAD);
    if (hip) {
        init_hip = (HipInit)dlsym(hip, "hipInit");
        get_flags = (GetFlags)dlsym(hip, "hipGetDeviceFlags");
        set_flags = (SetFlags)dlsym(hip, "hipSetDeviceFlags");
        synchronize = (Synchronize)dlsym(hip, "hipDeviceSynchronize");
    }
}

static void load_hsa(void)
{
    void *hsa = dlopen("libhsa-runtime64.so.1", RTLD_NOW | RTLD_NOLOAD);
    if (hsa)
        create_queue = (CreateQueue)dlsym(hsa, "hsa_queue_create");
}

int hipInit(unsigned flags)
{
    pthread_once(&hip_once, load_hip);
    if (!init_hip)
        return hip_unknown_error;
    const int status = init_hip(flags);
    if (status)
        return status;

    pthread_mutex_lock(&startup_lock);
    if (!initialized) {
        unsigned before, after;
        initialized = 1;
        if (!queues_started && get_flags && set_flags && !get_flags(&before) &&
            ((before & schedule_mask) == blocking ||
             !set_flags((before & ~schedule_mask) | blocking)) &&
            !get_flags(&after) && (after & schedule_mask) == blocking) {
            atomic_store(&configured, 1);
            fprintf(stderr, "BATMA_HIP_STARTUP configured=4 queues=0 before=%u\n",
                    before & schedule_mask);
        } else {
            fprintf(stderr, "BATMA_HIP_STARTUP setup_failed queues=%u\n", queues_started);
        }
    }
    pthread_mutex_unlock(&startup_lock);
    return status;
}

int hipSetDeviceFlags(unsigned flags)
{
    pthread_once(&hip_once, load_hip);
    if (!set_flags)
        return hip_unknown_error;
    const unsigned mode = flags & schedule_mask;
    // Preserve invalid requests. Valid requests keep the policy chosen at init.
    if (atomic_load(&configured) && (mode == 0 || mode == 1 || mode == 2)) {
        fprintf(stderr, "BATMA_HIP_STARTUP retained=4 requested=%u\n", mode);
        flags = (flags & ~schedule_mask) | blocking;
    }
    return set_flags(flags);
}

int hsa_queue_create(Agent agent, uint32_t size, int type, QueueError callback,
                     void *data, uint32_t private_size, uint32_t group_size, Queue **queue)
{
    pthread_once(&hsa_once, load_hsa);
    if (!create_queue)
        return hsa_error;
    pthread_mutex_lock(&startup_lock);
    if (queues_started++ == 0)
        fprintf(stderr, "BATMA_HIP_STARTUP first_queue configured=%d\n", atomic_load(&configured));
    pthread_mutex_unlock(&startup_lock);
    return create_queue(agent, size, type, callback, data, private_size, group_size, queue);
}

int hipDeviceSynchronize(void)
{
    pthread_once(&hip_once, load_hip);
    if (!synchronize)
        return hip_unknown_error;
    const int status = synchronize();
    const unsigned count = atomic_fetch_add(&syncs, 1) + 1;
    if (!status && (count == 1 || count % 1024 == 0)) {
        unsigned flags;
        if (get_flags && !get_flags(&flags))
            fprintf(stderr, "BATMA_HIP_STARTUP syncs=%u actual=%u\n", count, flags & schedule_mask);
    }
    return status;
}
