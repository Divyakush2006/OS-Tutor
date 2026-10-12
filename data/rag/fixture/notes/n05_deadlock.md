# Deadlocks

## Necessary conditions
A deadlock can arise only if four conditions hold at the same time: mutual exclusion, hold and wait, no preemption and circular wait. These are necessary conditions, not sufficient ones: all four can hold without a deadlock existing yet. Preventing any one of them prevents deadlock.

## Resource-allocation graphs
In a resource-allocation graph, a cycle is required for a deadlock. If every resource type has a single instance, a cycle means a deadlock. If a resource type has several instances, a cycle means only that a deadlock is possible; the system may still be able to finish every process.

## Safe and unsafe states
A state is safe if there is some order in which every process can obtain its maximum claim and finish. A safe state is never deadlocked. An unsafe state is not necessarily deadlocked; it means the system can no longer guarantee to avoid deadlock. The Banker's algorithm grants a request only if the resulting state is still safe, which is why it is called avoidance rather than prevention.

## Detection and recovery
Instead of avoiding deadlock, a system can let it happen, detect it with a wait-for graph or a detection algorithm, and recover by terminating processes or preempting resources. Most general-purpose operating systems ignore deadlock entirely and leave it to applications.
