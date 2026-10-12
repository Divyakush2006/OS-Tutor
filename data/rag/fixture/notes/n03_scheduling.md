# CPU scheduling concepts

## Criteria
A scheduler is judged by CPU utilisation, throughput, turnaround time (completion minus arrival), waiting time (time spent in the ready queue) and response time (first run minus arrival). Interactive systems care most about response time; batch systems care about throughput and turnaround.

## Preemptive and non-preemptive scheduling
A non-preemptive scheduler lets a process keep the CPU until it blocks or finishes. A preemptive scheduler can take the CPU away, for example when a timer interrupt ends a time slice or when a higher-priority process arrives. Round robin and shortest remaining time first are preemptive; FCFS is non-preemptive.

## Convoy effect and starvation
Under FCFS, short processes stuck behind one long CPU-bound process wait a long time; this is the convoy effect. Shortest job first minimises average waiting time but needs burst lengths in advance and can starve long jobs. Priority scheduling can also starve low-priority processes; aging, which raises a process's priority the longer it waits, prevents this.

## Choosing the round-robin quantum
With a very large quantum, round robin behaves like FCFS. With a very small one, the CPU spends a large share of its time context switching. A common rule of thumb is to choose the quantum so that most CPU bursts finish within one slice.
