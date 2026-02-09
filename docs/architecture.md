# Architecture Diagram & Design

## Overview

The system follows an event-driven microservices architecture with observability as a first-class concern.

Upstream services publish business events to Kafka.  
The Analytics Service consumes all events, derives metrics, and provides visibility into system behavior.

---

## High-Level Architecture 

<img src="../images/architecture.png" />

--- 
## Design Principles

- Event-driven and loosely coupled
- Observability-first design
- Infrastructure as Code
- Production-like local environment