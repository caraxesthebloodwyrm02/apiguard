# APIGuard Architecture Overview

## Component Architecture

```mermaid
graph TB
    subgraph "Core Components"
        TB[TokenBucket<br/>bucket.py]
        CB[CircuitBreaker<br/>circuit.py]
        RH[RetryHandler<br/>retry.py]
    end
    
    subgraph "Composition Layer"
        RLC[RateLimitedClient<br/>client.py]
        BR[BucketRegistry<br/>registry.py]
    end
    
    subgraph "HTTP Integration"
        ARC[AsyncRateLimitedClient<br/>adapters/httpx.py]
        HTTPX[httpx.AsyncClient]
    end
    
    subgraph "Support Components"
        LOG[StructuredLogger<br/>logging.py]
        EX[Exceptions<br/>exceptions.py]
    end
    
    %% Component Relationships
    RLC --> TB
    RLC --> RH
    RLC --> CB
    RLC --> EX
    
    ARC --> TB
    ARC --> RH
    ARC --> CB
    ARC --> HTTPX
    ARC --> EX
    
    BR --> TB
    BR --> LOG
    
    TB --> LOG
    CB --> LOG
    RH --> LOG
    ARC --> LOG
    
    %% Data Flow
    User[User Application] --> RLC
    User --> ARC
    
    %% Styling
    classDef core fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef composition fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef integration fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef support fill:#fff3e0,stroke:#e65100,stroke-width:2px
    
    class TB,CB,RH core
    class RLC,BR composition
    class ARC,HTTPX integration
    class LOG,EX support
```

## Data Flow Architecture

```mermaid
flowchart TD
    subgraph "Request Flow"
        A[Incoming Request] --> B{Rate Limit Check}
        B -->|Tokens Available| C{Circuit State}
        B -->|No Tokens| D[Reject: Rate Limited]
        
        C -->|CLOSED| E[Execute Request]
        C -->|OPEN| F[Reject: Circuit Open]
        C -->|HALF_OPEN| G[Test Request]
        
        E --> H{Response Status}
        G --> H
        
        H -->|Success| I[Record Success]
        H -->|Retryable| J[Apply Backoff]
        H -->|Failure| K[Record Failure]
        
        J --> L{Retry Attempts}
        L -->|Remaining| E
        L -->|Exhausted| M[Reject: Retry Exhausted]
        
        I --> N[Return Response]
        K --> O[Update Circuit State]
        G --> P{Success Threshold}
        P -->|Met| Q[Close Circuit]
        P -->|Not Met| R[Open Circuit]
        
        O --> S[Return Error]
    end
    
    subgraph "Logging Events"
        T[Rate Limit Events]
        U[Circuit Events]
        V[Retry Events]
        
        B --> T
        C --> U
        J --> V
        I --> V
        K --> U
    end
    
    %% Styling
    classDef flow fill:#f0f4f8,stroke:#2d3748,stroke-width:2px
    classDef decision fill:#fef5e7,stroke:#f39c12,stroke-width:2px
    classDef reject fill:#ffe6e6,stroke:#e74c3c,stroke-width:2px
    classDef success fill:#e6ffe6,stroke:#27ae60,stroke-width:2px
    
    class A,E,G,N flow
    class B,C,H,L,P decision
    class D,F,M,S reject
    class I,Q success
```

## Thread Safety Architecture

```mermaid
graph LR
    subgraph "Thread-Safe Components"
        TB1[TokenBucket]
        CB1[CircuitBreaker]
        BR1[BucketRegistry]
    end
    
    subgraph "Synchronization Mechanisms"
        LOCK1[threading.Lock<br/>Token Refill]
        LOCK2[threading.Lock<br/>State Updates]
        LOCK3[threading.Lock<br/>Registry Access]
    end
    
    subgraph "Atomic Operations"
        ATOM1[Token Acquisition]
        ATOM2[State Transitions]
        ATOM3[Bucket Creation]
    end
    
    TB1 --> LOCK1
    CB1 --> LOCK2
    BR1 --> LOCK3
    
    LOCK1 --> ATOM1
    LOCK2 --> ATOM2
    LOCK3 --> ATOM3
    
    %% Styling
    classDef component fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef sync fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef atomic fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    
    class TB1,CB1,BR1 component
    class LOCK1,LOCK2,LOCK3 sync
    class ATOM1,ATOM2,ATOM3 atomic
```

## Async Integration Architecture

```mermaid
sequenceDiagram
    participant App as Application
    participant ARC as AsyncRateLimitedClient
    participant TB as TokenBucket
    participant CB as CircuitBreaker
    participant RH as RetryHandler
    participant HTTP as httpx.Client
    
    App->>ARC: async with client:
    ARC->>HTTP: create AsyncClient
    
    App->>ARC: await client.get(url)
    ARC->>CB: check_circuit()
    CB-->>ARC: circuit closed
    
    ARC->>TB: acquire(tokens)
    TB-->>ARC: tokens acquired
    
    ARC->>CB: with breaker:
    CB->>CB: record attempt
    
    ARC->>RH: async for attempt in attempts()
    RH-->>ARC: attempt number
    
    ARC->>HTTP: await request(method, url)
    HTTP-->>ARC: response
    
    alt Success Response
        ARC-->>App: response
        CB->>CB: record_success()
    else Retryable Error
        ARC->>RH: await apply_backoff()
        RH->>RH: calculate delay + jitter
        RH-->>ARC: delay applied
        ARC->>ARC: retry request
    else Exhausted Retries
        ARC-->>App: RetryExhaustedError
        CB->>CB: record_failure()
    end
    
    App->>ARC: exit context
    ARC->>HTTP: await aclose()
```

## Key Architectural Principles

### 1. **Separation of Concerns**
- Each component handles a single responsibility
- Clear interfaces between components
- Minimal coupling, maximum cohesion

### 2. **Composition over Inheritance**
- `RateLimitedClient` composes core components
- HTTPX adapter extends functionality via composition
- Flexible component combinations

### 3. **Thread Safety by Design**
- All shared state protected by locks
- Atomic operations for critical sections
- Race condition prevention

### 4. **Async-First Implementation**
- Native async/await support
- Non-blocking operations throughout
- Seamless HTTPX integration

### 5. **Observability**
- Structured JSON logging at every decision point
- Comprehensive event tracking
- Production-ready monitoring capabilities
