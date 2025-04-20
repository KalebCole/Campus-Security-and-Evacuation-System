# --- Configuration ---
# IMPORTANT: Update this path to the ACTUAL location of EMP001.jpg on your system
$imagePath = "C:\Users\kaleb\Documents\00_College\Senior Capstone\api\static\images\test\invalid.jpg" 

# --- MQTT Broker Address --- 
# Uncomment the desired broker address:
# Option 1: Local Docker container (if running mosquitto via docker-compose)
# $mqttBroker = "localhost" 
# $mqttBroker = "mosquitto" # Use this if running the script outside docker but connecting to the docker network

# Option 2: Deployed Fly.io broker (use hostname or IP)
$mqttBroker = "campus-security-evacuation-system.fly.dev"
# $mqttBroker = "66.241.125.144" # Alternative: Fly.io IP address
# --------------------------

$mqttPort = 1883
$mqttTopic = "campus/security/session"
$deviceId = "powershell-file-pub-01"

# --- Docker Execution Configuration (Only relevant if using mosquitto_pub via Docker exec) ---
# If connecting directly to Fly.io, you might need to install mosquitto-clients locally 
# or adapt the script to use a different MQTT client library for PowerShell.
# The 'docker exec' part below assumes you are publishing *from your host* *to the local docker mosquitto*.
# It won't work directly for publishing to Fly.io unless you adapt it.
# $containerName = "mosquitto" # Only used for docker exec below - REMOVED as we now use local pub
# -----------------------------------------------------------------------------------------

# Temporary file paths
$tempPayloadFileHost = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "mqtt_payload_$(Get-Random).json")
# $tempPayloadFileContainer = "/tmp/mqtt_payload.json" # Path inside the container - REMOVED
# --- End Configuration ---

# Validate image path
if (-not (Test-Path $imagePath)) {
    Write-Error "Image file not found at specified path: $imagePath"
    Write-Error "Please update the `$imagePath variable in the script."
    exit 1
}

# Generate unique session ID
$sessionId = [guid]::NewGuid().ToString()

# Read image and encode to Base64
try {
    $imageBytes = [IO.File]::ReadAllBytes($imagePath)
    $base64Image = [Convert]::ToBase64String($imageBytes)
    $imageSize = $imageBytes.Length
    Write-Host "Read and encoded image '$imagePath' ($imageSize bytes) for session: $sessionId"
} catch {
    Write-Error "Error reading or encoding image: $_"
    exit 1
}

$datauri = "data:image/jpeg;base64," + $base64Image

# Create payload object
$payloadObject = @{
    device_id = $deviceId
    session_id = $sessionId
    timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ") # ISO 8601 format
    session_duration = 1500 # Example value
    image_size = $imageSize
    image = $datauri
    rfid_tag = $null # Explicitly null for Face-Only
    rfid_detected = $false # Set to false for Face-Only
    face_detected = $true  # Set to true for Face-Only
    free_heap = 30000 # Example value
    state = "SESSION"
}

# Convert object to compact JSON string
$payloadJson = $payloadObject | ConvertTo-Json -Depth 10 -Compress

# --- Save payload to temporary file on Host ---
try {
    Write-Host "Saving payload to temporary file: $tempPayloadFileHost"
        # Use UTF8 encoding WITHOUT BOM
        # Use .NET methods for UTF8 without BOM
    $Utf8NoBomEncoding = New-Object System.Text.UTF8Encoding($False) # $False means DO NOT emit BOM
    [System.IO.File]::WriteAllLines($tempPayloadFileHost, $payloadJson, $Utf8NoBomEncoding)
} catch {
    Write-Error "Error saving payload to temporary file: $_"
    exit 1
}

# --- Execute Docker Commands --- NO LONGER USING DOCKER - Renamed Section
# --- Publish MQTT Message (using locally installed mosquitto_pub) ---
try {
    Write-Host "Publishing payload to ${mqttBroker}:${mqttPort} on topic '$mqttTopic' using local mosquitto_pub.exe..."
    # Ensure mosquitto_pub.exe is in your PATH (which it should be based on Get-Command)
    # Using -f to send the payload from the temporary file on the host
    mosquitto_pub.exe -h $mqttBroker -p $mqttPort -t "$mqttTopic" -f $tempPayloadFileHost 
    if ($LASTEXITCODE -ne 0) { 
        Write-Warning "Mosquitto_pub.exe finished with exit code $LASTEXITCODE. Check connection & broker logs."
    } else {
        Write-Host "Mosquitto_pub.exe executed successfully."
    } 
} catch {
    Write-Error "An error occurred during MQTT publishing: $_"
} finally {
    # 4. Clean up the temporary file on the host
    if (Test-Path $tempPayloadFileHost) {
        Write-Host "Cleaning up temporary file on host: $tempPayloadFileHost"
        Remove-Item $tempPayloadFileHost -Force
    }
}

Write-Host "`nScript finished. Check API logs for session $sessionId."
