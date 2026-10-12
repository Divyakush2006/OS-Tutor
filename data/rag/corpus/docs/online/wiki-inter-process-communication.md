# Inter-process communication

In computer science, inter-process communication (IPC) is the sharing of data between running processes in a computer system, or between multiple such systems. Mechanisms for IPC may be provided by an operating system. Applications which use IPC are often categorized as using clients and servers, where the client process requests data and the server process responds to client requests..
IPC is very important to the design process for microkernels and nanokernels, which reduce the number of functionalities provided by the kernel. Those functionalities are then obtained by messaging with IPC servers (specialized coordination application), leading to a large increase in communication when compared to a regular monolithic kernel (central, with less spawn independent processes). IPC interfaces generally encompass variable analytic framework structures. This IPCs methods ensure compatibility between the multi-vector protocols upon which IPC models rely.
An IPC mechanism is either synchronous or asynchronous. Synchronization primitives may be used to have synchronous behavior with an asynchronous IPC mechanism.

## Disadvantages

Merging data from two processes can often incur significantly higher costs compared to processing the same data on a single thread, potentially by two or more orders of magnitude due to overheads such as inter-process communication and synchronization.

## Approaches

Different IPC approaches are tailored to different process requirements (inside an application), such as performance, modularity, and system circumstances such as network bandwidth (an optimal consideration, but depends on the application distribution) and latency (general cost and density of generating and processing requests).

## Applications

### Remote procedure call interfaces

Java's Remote Method Invocation (RMI)
ONC RPC
XML-RPC or SOAP
JSON-RPC
Message Bus (Mbus) (specified in RFC 3259) (not to be confused with M-Bus)
.NET Remoting
gRPC

### Platform communication stack

The following are messaging, and information systems that utilize IPC mechanisms but don't implement IPC themselves:

### Operating system communication stack

The following are platform or programming language-specific APIs:

### Distributed object models

The following are platform or programming language specific-APIs that use IPC, but do not themselves implement it:
