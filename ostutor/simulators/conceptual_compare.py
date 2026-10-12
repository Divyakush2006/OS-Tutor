"""Comparison items: relate two concepts.

Genuine content multiplication rather than permutation. Asking how preemption
relates to the convoy effect is a DIFFERENT question from either concept alone,
and the answer must be constructed from both corrections - so it carries new
training signal instead of restating one entry with different wording.

Pairs are drawn only within the same syllabus AREA, because comparing an inode
with a time quantum teaches nothing.
"""
import itertools
import random

from .conceptual import KB

AREAS = {
    "scheduling": ["preemption", "mlfq_purpose", "convoy_effect", "response_vs_turnaround",
                   "quantum_size", "io_bound_cpu_bound", "sjf_optimality", "aging",
                   "rate_monotonic", "edf_scheduling", "processor_affinity",
                   "load_balancing", "lottery_scheduling", "cfs_scheduler", "nice_values",
                   "hard_vs_soft_realtime", "dispatch_latency"],
    "memory": ["virtual_memory_size", "thrashing", "page_fault_cost", "belady_anomaly",
               "lru_implementation", "internal_vs_external_frag", "tlb_purpose",
               "demand_paging", "working_set", "swapping_vs_paging", "dirty_bit",
               "page_size_tradeoff", "external_fragmentation_compaction",
               "multilevel_page_table", "inverted_page_table", "tlb_reach",
               "effective_access_time", "segmentation", "buddy_allocator",
               "slab_allocator", "mmap_files", "oom_killer", "overcommit",
               "stack_vs_heap", "stack_overflow", "aslr", "swappiness",
               "clock_algorithm", "global_vs_local_replacement", "tlb_shootdown",
               "huge_pages", "numa", "page_table_entry_bits", "base_limit_registers"],
    "sync": ["race_condition", "mutex_vs_semaphore", "busy_waiting",
             "critical_section_requirements", "producer_consumer_semaphores",
             "dining_philosophers", "priority_inversion", "monitor_vs_semaphore",
             "spinlock_uniprocessor", "condition_variable", "signal_vs_broadcast",
             "reader_writer_lock", "test_and_set", "peterson", "memory_barriers",
             "false_sharing", "counting_semaphore", "compare_and_swap", "aba_problem",
             "lock_granularity", "rcu"],
    "deadlock": ["starvation_vs_deadlock", "deadlock_conditions", "banker_purpose",
                 "safe_vs_deadlocked", "livelock", "deadlock_detection",
                 "deadlock_recovery", "wait_for_graph", "lock_ordering", "prevention_vs_avoidance", "rag_cycle"],
    "process": ["process_vs_thread", "context_switch", "system_call", "interrupt_vs_trap",
                "fork_semantics", "zombie_orphan", "copy_on_write",
                "kernel_vs_user_thread", "exec_semantics", "wait_purpose",
                "pipe_semantics", "pipe_eof", "signals", "sigkill_vs_sigterm",
                "pcb_contents", "process_states", "shared_memory_ipc",
                "message_passing", "orphan_reparenting", "thread_pool",
                "thread_local_storage", "init_process"],
    "storage": ["inode_purpose", "raid_redundancy", "hard_vs_soft_link",
                "journaling_purpose", "seek_vs_rotational", "ssd_no_seek",
                "file_descriptor", "file_allocation_contiguous", "file_allocation_linked",
                "file_allocation_indexed", "free_space_bitmap", "directory_structure",
                "mounting", "vfs_layer", "page_cache", "log_structured_fs",
                "raid_levels", "raid5_write_penalty", "fsync_durability",
                "unlink_open_file", "write_back_cache", "block_size_tradeoff", "fat_table",
                "ssd_wear_trim", "cow_snapshots"],
    "io": ["interrupt_handling", "dma", "polling_vs_interrupts", "buffering", "spooling",
           "fsync_durability", "page_cache", "top_bottom_half", "io_multiplexing",
           "write_back_cache"],
    "kernel": ["user_kernel_mode", "monolithic_vs_micro", "loadable_modules",
               "system_call", "interrupt_vs_trap", "boot_process", "proc_filesystem", "kernel_preemption", "vdso",
               "kernel_stack", "top_bottom_half", "dynamic_linking"],
    "protection": ["access_control_lists", "setuid", "least_privilege", "aslr",
                   "user_kernel_mode", "directory_permissions",
                   "sticky_bit", "capabilities_vs_acl"],
    "virtualisation": ["hypervisor_types", "container_vs_vm", "namespaces_cgroups",
                       "trap_and_emulate", "paravirtualization",
                       "memory_ballooning"],
}

BY_TOPIC = {k[0]: k for k in KB}

FRAMINGS = [
    "How does {a} relate to {b}?",
    "A student confuses {a} with {b}. How would you separate them?",
    "Compare {a} and {b}.",
    "In revision I keep mixing up {a} and {b}. What's the distinction?",
    "Are {a} and {b} connected? Explain the relationship.",
    "Exam question: contrast {a} with {b}.",
]


# Each comparison embeds BOTH concepts' correction paragraphs verbatim. Without a
# cap, a concept in a 14-topic area appears in 13 comparisons, so the model reads
# the same paragraph 13+ times per epoch - memorisation pressure that semantic
# dedup cannot see, because every PAIR embeds differently.
MAX_PER_CONCEPT = 4


def generate(n, seed=7, max_per_concept=MAX_PER_CONCEPT):
    rng = random.Random(seed)
    pairs = []
    for area, topics in AREAS.items():
        avail = [t for t in topics if t in BY_TOPIC]
        pairs += [(area, x, y) for x, y in itertools.combinations(avail, 2)]
    rng.shuffle(pairs)
    uses = {}
    out, seen = [], set()
    for area, ta, tb in pairs:
        if len(out) >= n:
            break
        if uses.get(ta, 0) >= max_per_concept or uses.get(tb, 0) >= max_per_concept:
            continue
        A, B = BY_TOPIC[ta], BY_TOPIC[tb]
        q = rng.choice(FRAMINGS).format(a=A[1], b=B[1])
        if q in seen:
            continue
        seen.add(q)
        ans = (f"They sit in the same area ({area}) but answer different questions.\n\n"
               f"**{A[1].capitalize()}.** {A[4]}\n\n"
               f"**{B[1].capitalize()}.** {B[4]}\n\n"
               f"**Where students go wrong.** One common error is to think "
               f"{A[2]}; another is to think {B[2]}. Both come from the same habit of "
               f"reasoning from the name rather than the mechanism.\n\n"
               f"**Putting them together.** {A[5]} By contrast, {B[5][0].lower()}{B[5][1:]}")
        out.append(dict(topic=f"compare_{area}_{ta}_{tb}", question=q, answer=ans,
                        misconception=f"{A[2]} / {B[2]}", seed=rng.randrange(1 << 30),
                        template_id=f"compare_{area}",
                        difficulty=round(rng.uniform(0.5, 0.9), 2)))
        uses[ta] = uses.get(ta, 0) + 1
        uses[tb] = uses.get(tb, 0) + 1
    return out
