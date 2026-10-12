# Elevator algorithm

The elevator algorithm, or SCAN, is a disk-scheduling algorithm to determine the motion of the disk's arm and head in servicing read and write requests.
This algorithm is named after the behavior of a building elevator, where the elevator continues to travel in its current direction (up or down) until empty, stopping only to let individuals off or to pick up new individuals heading in the same direction.  
From an implementation perspective, the drive maintains a buffer of pending read/write requests, along with the associated cylinder number of the request, in which lower cylinder numbers generally indicate that the cylinder is closer to the spindle, and higher numbers indicate the cylinder is farther away.
The algorithm is largely obsolete for data storage. With the current generation of magnetic disks it is not possible to know the location of specific data on the disk and solid state memory devices have a constant seek time independent of location.

## History

The earliest published treatment of the algorithm is in Donald Knuth's classic book The Art of Computer Programming Volume 1 where he describes a theoretical simulation of a single elevator in the Mathematics building at the California Institute of Technology in order to discuss coroutines and doubly linked lists. By the 1980s the problem had been extended to n elevators.  It is now considered to be a classic problem of Software Engineering and the formal specification of programming languages.

## Description

When a new request arrives while the drive is idle, the initial arm/head movement will be in the direction of the cylinder where the data is stored, either in or out.  As additional requests arrive, requests are serviced only in the current direction of arm movement until the arm reaches the edge of the disk. When this happens, the direction of the arm reverses, and the requests that were remaining in the opposite direction are serviced, and so on.

## Variations

One variation of this method ensures all requests are serviced in only one direction, that is, once the head has arrived at the outer edge of the disk, it returns to the beginning and services the new requests in this one direction only (or vice versa). This is known as the "Circular Elevator Algorithm" or C-SCAN.  Although the time of the return seek is wasted, this results in more equal performance for all head positions, as the expected distance from the head is always half the maximum distance, unlike in the standard elevator algorithm where cylinders in the middle will be serviced as much as twice as often as the innermost or outermost cylinders.
Other variations include:

FSCAN
LOOK
C-LOOK
N-Step-SCAN

## Example

The following is an example of how to calculate average disk seek times for both the SCAN and C-SCAN algorithms.

Example list of pending disk requests (listed by track number): 100, 50, 10, 20, 75.
The starting track number for the examples will be 35.
The list will need to be sorted in ascending order: 10, 20, 50, 75, 100.
Both SCAN and C-SCAN behave in the same manner until they reach the last track queued. For the sake of this example let us assume that the SCAN algorithm is currently going from a lower track number to a higher track number (like the C-SCAN is doing). For both methods, one takes the difference in magnitude (i.e. absolute value) between the next track request and the current track.

Seek 1: 50 − 35 = 15
Seek 2: 75 − 50 = 25
Seek 3: 100 − 75 = 25
At this point both have reached the highest (end) track request. SCAN will just reverse direction and service the next closest disk request (in this example, 20) and C-SCAN will always go back to track 0 and start going to higher track requests.

Seek 4 (SCAN): 20 − 100 = 80
Seek 5 (SCAN): 10 − 20 = 10
Total (SCAN): 155
Average (SCAN): 155 ÷ 5 = 31
Seek 4 (C-SCAN): 0 − 100 = 0 head movement as cylinders are treated as a  circular list (C-SCAN always goes back to the first track)
Seek 5 (C-SCAN): 10 − 0 = 10
Seek 6 (C-SCAN): 20 − 10 = 10
Total (C-SCAN): 85
Average (C-SCAN): 85 ÷ 5 = 17
Even though six seeks were performed using the C-SCAN algorithm, only five I/Os were actually done.

## Analysis

For both versions of the elevator algorithm, the arm movement is less than twice the number of total cylinders and produces a smaller variance in response time. The algorithm is also relatively simple. 
The elevator algorithm is not always better than shortest seek first, which is slightly closer to optimal, but can result in high variance in response time and even in starvation when new requests continually get serviced prior to existing requests. Anti-starvation techniques can be applied to the shortest seek time first algorithm to guarantee a maximum response time.
