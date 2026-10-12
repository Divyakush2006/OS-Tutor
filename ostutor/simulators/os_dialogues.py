"""OS-domain Socratic tutoring dialogues, built from the misconception knowledge base.

WHY. Until now the tutoring category was entirely MathDial: real tutoring
BEHAVIOUR, but not one dialogue about operating systems. The model would learn
how to tutor from maths and what to teach from procedural data, and the two never
met in a single example. These dialogues put the behaviour and the domain
together.

STRUCTURE follows MathDial's teacher-move taxonomy (measured on its 18,607 teacher
moves: focus 6,808 / generic 4,456 / probing 4,252 / telling 3,091 - telling is
the RAREST move, i.e. good tutors reveal least):

  student   states the misconception as their own belief
  tutor     PROBING - acknowledges why it is tempting, then asks a question
            that makes the belief predict something wrong (no answer revealed)
  student   answers from inside the misconception
  tutor     FOCUS - points at the specific gap, asks them to reconsider
  student   partial revision
  tutor     TELLING, only now - the correction plus a concrete example, and a
            closing check-question so the student has to use it

The first tutor turn never contains the correction, which is exactly what the
`tutoring_leaks_answer_turn1` gate enforces.
"""
import random

from .conceptual import KB
from .conceptual_kb3 import KB3
from .conceptual_kb4 import KB4
from .conceptual_kb5 import KB5

# Socratic probes for the original 6-tuple entries (KB3/KB4 carry their own).
PROBES = {
 "process_vs_thread": "If two threads of one process both increment the same global variable, how many copies of that variable exist?",
 "context_switch": "When the CPU switches to a different process, what happens to the TLB entries that belonged to the old one?",
 "system_call": "When your program calls read(), does the CPU's privilege level change at any point?",
 "interrupt_vs_trap": "If you re-run exactly the same instruction, will a divide-by-zero happen again? Will a disk-completion interrupt?",
 "preemption": "Round Robin serves processes in arrival order, just like FCFS. So is Round Robin preemptive or not?",
 "starvation_vs_deadlock": "In a system where a low-priority process never runs, is the CPU ever idle?",
 "deadlock_conditions": "If processes had to request every resource they need all at once, could a deadlock still form?",
 "banker_purpose": "Does Banker's algorithm ever let the system reach a deadlocked state and then fix it?",
 "race_condition": "On a machine with only one CPU core, can two threads still lose an update to a shared counter?",
 "mutex_vs_semaphore": "In producer-consumer, the producer signals and the consumer waits. Could a mutex, which only its owner may unlock, express that?",
 "busy_waiting": "Is spinning for three instructions' worth of time more or less expensive than two context switches?",
 "virtual_memory_size": "What happens to performance when the pages a process is actively using no longer fit in RAM?",
 "thrashing": "If a faster disk were installed in a thrashing system, would the underlying cause go away?",
 "page_fault_cost": "Which is slower by orders of magnitude: walking a page table in memory, or reading a page from disk?",
 "belady_anomaly": "Under FIFO, is it possible for a process to get MORE page faults after you give it an extra frame?",
 "lru_implementation": "To implement exact LRU, what would have to be updated on every single memory access?",
 "internal_vs_external_frag": "If a 5 KB allocation uses 4 KB pages, how much of the second page is wasted?",
 "fork_semantics": "fork() is called once. How many times does it return?",
 "zombie_orphan": "A zombie process has already terminated. Is it still using any CPU time?",
 "io_bound_cpu_bound": "If you give a process that runs briefly and then waits on disk a high priority, how much CPU does that actually cost?",
 "inode_purpose": "If a file has two hard links with different names, where are those two names stored?",
 "raid_redundancy": "If you accidentally delete a file on a RAID 1 mirror, what happens on the second disk?",
 "mlfq_purpose": "In MLFQ, how does the scheduler find out whether a job is interactive without anyone telling it?",
 "convoy_effect": "Three jobs with bursts 100, 1 and 1 arrive in that order under FCFS. How long do the two short jobs wait?",
 "response_vs_turnaround": "Round Robin starts every job quickly. Does that also mean every job finishes quickly?",
 "quantum_size": "What happens to Round Robin if the time quantum is longer than every job's burst?",
 "tlb_purpose": "Can you have a TLB hit and still have to fetch the data from main memory?",
 "demand_paging": "When a large program starts, are the pages for features you never use ever loaded?",
 "copy_on_write": "If a child calls exec() immediately after fork(), how much of the parent's memory actually got copied?",
 "working_set": "A program allocates 1 GB but spends its time looping over 4 MB. How much memory does it need to run well?",
 "swapping_vs_paging": "When Linux runs low on memory, does it remove whole processes or individual pages?",
 "dirty_bit": "If an evicted page was never modified, does it need to be written back to disk?",
 "page_size_tradeoff": "If pages were made much larger, what would happen to the wasted space at the end of each allocation?",
 "critical_section_requirements": "With strict alternation between two processes, what happens if one of them never wants to enter the critical section?",
 "producer_consumer_semaphores": "With only a mutex around the buffer, what does a consumer do when it finds the buffer empty?",
 "dining_philosophers": "If all five philosophers pick up their left fork at the same moment, what does each one wait for?",
 "priority_inversion": "A high-priority task waits for a lock held by a low-priority task. What happens if a medium-priority task becomes ready?",
 "monitor_vs_semaphore": "With raw semaphores, what happens if a programmer forgets one signal() call on some code path?",
 "file_descriptor": "After fork(), if the child reads from an inherited file descriptor, does the parent's file offset move too?",
 "hard_vs_soft_link": "If you delete the file a symbolic link points to, what happens when you open the link?",
 "journaling_purpose": "After a crash on a journaled file system, is the content of a file you were writing guaranteed to be intact?",
 "seek_vs_rotational": "Which usually takes longer on a hard disk: moving the arm across the platter, or waiting for the sector to rotate under it?",
 "ssd_no_seek": "An SSD has no moving arm. What would SCAN save on an SSD?",
 "kernel_vs_user_thread": "With purely user-level threads, what happens to the other threads when one makes a blocking system call?",
 "external_fragmentation_compaction": "To compact memory, what has to happen to every pointer into the data being moved?",
 "safe_vs_deadlocked": "If the system is in an unsafe state, has a deadlock necessarily already occurred?",
}

OPEN = [
    "I think {mis}. Is that right?",
    "Quick check - {mis}, correct?",
    "My understanding is that {mis}.",
    "I wrote in my notes that {mis}. Does that hold up?",
    "Isn't it true that {mis}?",
    "We were revising and I said {mis}. My friend disagreed.",
]
ACK = [
    "That's a very common intuition, and it isn't unreasonable - {why}.",
    "I can see where that comes from: {why}.",
    "Lots of people start there, because {why}.",
    "It's a natural first guess - {why}.",
]
LINK = [
    "Before I say more, try this:",
    "Let's test it with a question.",
    "Let's check the idea against a concrete case.",
    "Try reasoning through this first:",
]
# Every slot below receives `why`, which is a full CLAUSE ("the PC is the most
# visible piece of CPU state"). Templates therefore wrap it with "that ..." or
# "since ..." - never as a noun phrase, which produced ungrammatical turns such as
# "it treats the PC is the most visible piece of CPU state as the whole story".
STUDENT_GUESS = [
    "I'd still go with what I said, since {why}.",
    "My answer would follow from the fact that {why}.",
    "I think it works the way I described - after all, {why}.",
    "I'm not sure, but my instinct is that it follows because {why}.",
]
FOCUS = [
    "Look closely at the assumption in that answer: it rests on the idea that {why}. "
    "Is that the whole story? What would have to be true for your prediction to hold?",
    "That's the step to question. Your reasoning depends on the fact that {why}. Can "
    "you think of a case where that stops being enough?",
    "Good - you've made the assumption explicit: {why}. Does that actually settle the "
    "question, or is it only part of the picture?",
]
STUDENT_REVISE = [
    "Maybe it's not the whole story... I'm not sure what I'm missing.",
    "I suppose it might not hold in every case. What am I missing?",
    "Now I'm less sure. Could you explain what actually happens?",
    "I think I see a gap, but I can't pin it down.",
]
TELL = [
    "Here's the key idea. {corr}\n\nTo make it concrete: {ex}\n\nSo, back to my earlier "
    "question - how would you answer it now?",
    "Right, here's what's actually going on. {corr}\n\nA concrete case: {ex}\n\nWith "
    "that in mind, can you restate the idea in your own words?",
    "{corr}\n\nFor example: {ex}\n\nNow try the original question again - what changes "
    "in your answer?",
]


def _entries():
    """All KB entries with a probe: (topic, q, mis, why, corr, ex, probe)."""
    out, seen = [], set()
    for e in KB3 + KB4 + KB5:                      # 7-tuples with their own probe
        out.append(tuple(e)); seen.add(e[0])
    for e in KB:                             # original entries: probe from PROBES
        if e[0] in PROBES and e[0] not in seen:
            out.append(tuple(e[:6]) + (PROBES[e[0]],)); seen.add(e[0])
    return out


def _cap(s):
    return s[0].upper() + s[1:] if s else s


def generate(per_topic=3, seed=11):
    """Up to `per_topic` differently-worded dialogues per concept. Semantic dedup
    downstream will keep only the genuinely distinct ones, so asking for more than
    ~3 per concept buys nothing."""
    rng = random.Random(seed)
    out = []
    for topic, q, mis, why, corr, ex, probe in _entries():
        seen = set()
        for _ in range(per_topic * 3):
            if len(seen) >= per_topic:
                break
            parts = (rng.randrange(len(OPEN)), rng.randrange(len(ACK)),
                     rng.randrange(len(LINK)), rng.randrange(len(STUDENT_GUESS)),
                     rng.randrange(len(FOCUS)), rng.randrange(len(STUDENT_REVISE)),
                     rng.randrange(len(TELL)))
            if parts in seen:
                continue
            seen.add(parts)
            o, a, l, g, f, rv, t = parts
            msgs = [
                dict(role="user", content=_cap(OPEN[o].format(mis=mis))),
                dict(role="assistant",
                     content=f"{ACK[a].format(why=why)} {LINK[l]} {probe}"),
                dict(role="user", content=STUDENT_GUESS[g].format(why=why)),
                dict(role="assistant", content=FOCUS[f].format(why=why)),
                dict(role="user", content=STUDENT_REVISE[rv]),
                dict(role="assistant", content=TELL[t].format(corr=corr, ex=ex)),
            ]
            out.append(dict(topic=f"os_dialogue_{topic}", messages=msgs,
                            misconception=mis, seed=rng.randrange(1 << 30),
                            template_id=f"os_dialogue_{topic}"))
    return out
