# Shortest seek first

Shortest seek first (or shortest seek time first) is a secondary storage scheduling algorithm to determine the motion of the disk read-and-write head in servicing read and write requests.
An operating system using shortest seek first puts requests for data from the drive into a queue, and services them in order of how long it would take the drive to physically position its drive head over the correct cylinder and sector to read the data. This algorithm prioritizes requests for data that would take less time to handle, which is quicker than handling the requests in the order they are received. However, many requests for data that are physically around the same region in the hard drive will starve requests that are further away.

## Algorithm

A basic description of the shortest seek first algorithm is as follows:

Create a priority queue of unserviced requests. The priority queue is ordered such that requests with a lower distance between the sector and cylinder currently under the head and the sector and cylinder of the request will be serviced first.
While the priority queue is not empty, process the first request in the queue.

## Description

### Magnetic disk storage

The shortest seek first algorithm targets hard disk drives (HDD) featuring magnetic disks. In an HDD, magnetic disks are arranged in a stack, like a stack of CDs, which have information recorded onto them using a magnet.
Data is written to the disks and read by a series of heads, attached to actuator arms, which sit in between and just slightly above the surface of each disk. The arm system physically moves the heads across the disks to access data.
Each disk is subsequently divided into circular tracks, which are themselves divided into sectors. For example, when reading data, the arms physically extend out to a particular cylinder, in what is called the seek time, while the disks rotate beneath them. The time it takes for the disk to rotate to the desired sector is called the "rotational latency."

### Implementation

Shortest seek first is a specific case of the shortest job next scheduling algorithm. It is motivated by the reasonable assumption that time can be saved by prioritizing requests in a way that minimizes the time spent moving the actuator arms.
The drive maintains an incoming buffer of requests, and tied with each request is the cylinder number of the request. Lower cylinder numbers indicate the cylinder is closer to the spindle, while higher numbers indicate the cylinder is further away.
The shortest seek first algorithm determines which request is closest to the current position of the head, and services that request next.

## Analysis

Shortest seek first represents an improvement over the First come, first served algorithm by prioritizing requests that involve less actuator arm movement.
However, since the buffer is always getting new requests, these can skew the service time of requests that may be furthest away from the disk head's current location, if the new requests are all close to the current location; in fact, starvation may result, with the faraway requests never being able to make progress.
