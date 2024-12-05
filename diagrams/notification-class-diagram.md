# Notitication Class Diagram

```mermaid
classDiagram
    class NotificationType {
        <<enumeration>>
        RFID_ACCESS_GRANTED
        RFID_ACCESS_DENIED
        FACE_RECOGNIZED
        FACE_NOT_RECOGNIZED
        SYSTEM_ALERT
    }

    class SeverityLevel {
        <<enumeration>>
        INFO
        WARNING
        CRITICAL
    }

    class Notification {
        +str id
        +NotificationType notification_type
        +SeverityLevel severity_level
        +datetime timestamp
        +Optional[str] location
        +Optional[str] rfid_id
        +Optional[str] face_id
        +Optional[str] message
        +Optional[str] actions_required
        +Optional[str] image_url
        +str status
        +__str__() str
    }

    Notification --> NotificationType : uses
    Notification --> SeverityLevel : uses
    ```