# System Architecture

<!-- TODO: Improve this architecture by adding in motion sensors and comparing with the architecture diagram in the other file -->
```mermaid
flowchart TD
    %% Input Devices
    RFID[Arduino Uno R4<br>RFID Reader] -->|POST /rfid| API
    Camera[ESP32 Camera] -->|POST /image| API
    
    %% API Layer
    subgraph API["API Layer (Routes)"]
        rfid_endpoint["/rfid endpoint"]
        image_endpoint["/image endpoint"]
        status_endpoint["/status/:session_id endpoint"]
        verify_user["verify_user() function"]
        
        rfid_endpoint --> verify_user
        image_endpoint --> verify_user
    end
    
    %% Session Management
    subgraph SessionMgmt["Session Management"]
        SessionManager["SessionManager<br>- create_session()<br>- update_session()<br>- get_session()<br>- clean_expired_sessions()"]
        Sessions[(Active Sessions)]
        
        SessionManager <--> Sessions
    end
    
    verify_user <--> SessionManager
    
    %% Worker Management
    subgraph WorkerMgmt["Worker Management"]
        WorkerManager["WorkerManager<br>- start_worker()<br>- stop_worker()<br>- _process_complete_sessions()<br>- _clean_stale_sessions()"]
        VerificationProcess["_perform_verification()<br>- Compare embeddings<br>- Make access decision"]
        
        WorkerManager --> VerificationProcess
    end
    
    %% Database
    DB[(User Database<br>RFID & Facial Embeddings)]
    verify_user -.->|Query user by RFID| DB
    VerificationProcess -.->|Compare embeddings| DB
    
    %% Notification
    NotificationSvc["Notification Service<br>- SMS<br>- NTFY"]
    VerificationProcess -->|Send Results| NotificationSvc
    
    %% Door Control
    subgraph DoorControl["Door Control System"]
        AccessController["Access Controller"]
        DoorLock["Door Lock Mechanism"]
        
        AccessController --> DoorLock
    end
    
    %% Connections between components
    SessionManager <--> WorkerManager
    VerificationProcess -->|Access Granted| AccessController
    
    %% System Flow
    Sessions -->|Complete Sessions with RFID + Image| WorkerManager
    WorkerManager -->|Clean expired| Sessions
    
```


# System Component Diagrams

## Verification Process

```mermaid
flowchart TD
    %% Main components
    API[API Routes]
    WM[Worker Manager]
    SM[Session Manager]
    NS[Notification Service]
    FR[Face Recognition Model]
    DL[Door Lock Mechanism <br> Arduino Uno R4] 
    
    %% Worker Manager internals
    subgraph WM["Worker Manager"]
        PCS[Process Complete Sessions]
        PV[Perform Verification]
        CSS[Clean Stale Sessions]
    end
    
    %% Connections for verification flow
    API -->|Stores RFID & image data| SM
    SM -->|Provides complete sessions| WM
    PCS -->|For each complete session| PV
    PV -->|Compare embeddings| FR
    PV -->|Send verification results| NS
    PV -->|Send unlock signal on success| DL
    CSS -->|Remove expired sessions| SM
```

## Client Management

```mermaid
flowchart TD
    %% Position RFID in top left, Camera in top right, UDP in middle
    RFID["Arduino Uno R4<br>(RFID Reader)"] ---|"Scans RFID tag"| UDP
    CAM["ESP32-Cam Module"] ---|"Captures Image"| UDP
    
    %% Place UDP broadcast in middle
    UDP["UDP Broadcast<br>Channel"]
    
    %% API at bottom
    API["Flask Server API"]
    
    %% Connection flows
    UDP -->|"Broadcast Session ID"| RFID
    UDP -->|"Broadcast Session ID"| CAM
    RFID -->|"POST /rfid<br>(with session ID)"| API
    CAM -->|"POST /image<br>(with session ID)"| API
    
    %% Position styling
    classDef leftNode fill:#f9f,stroke:#333,stroke-width:2px;
    classDef rightNode fill:#bbf,stroke:#333,stroke-width:2px;
    classDef centerNode fill:#ff9,stroke:#333,stroke-width:2px;
    
    class RFID leftNode;
    class CAM rightNode;
    class UDP centerNode;
    
    %% Force layout positioning
    RFID:::leftNode -. invisible .- UDP:::centerNode -. invisible .- CAM:::rightNode
    ```