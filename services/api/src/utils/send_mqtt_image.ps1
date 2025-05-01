# --- Configuration ---
$imagePath = "C:\Users\kaleb\Documents\00_College\Senior Capstone\api\static\images\tests\Griffin.jpg" 

# --- MQTT Broker Address --- 
# Uncomment the desired broker address:
# Option 1: Local Docker container (if running mosquitto via docker-compose)
# $mqttBroker = "localhost" 
# $mqttBroker = "mosquitto" # Use this if running the script outside docker but connecting to the docker network

# Option 2: Deployed Fly.io broker (use hostname or IP)
$mqttBroker = "z8002768.ala.us-east-1.emqxsl.com"
# --------------------------

$mqttPort = 8883
$mqttUsername = "kalebcole" 
$mqttPassword = "cses" 
# --------------------------------------

$mqttTopic = "campus/security/session"
$deviceId = "powershell-file-pub-01"


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

# --- REMOVED Save payload to temporary file on Host ---
# try {
#     Write-Host "Saving payload to temporary file: $tempPayloadFileHost"
#         # Use UTF8 encoding WITHOUT BOM
#         # Use .NET methods for UTF8 without BOM
#     $Utf8NoBomEncoding = New-Object System.Text.UTF8Encoding($False) # $False means DO NOT emit BOM
#     [System.IO.File]::WriteAllLines($tempPayloadFileHost, $payloadJson, $Utf8NoBomEncoding)
# } catch {
#     Write-Error "Error saving payload to temporary file: $_"
#     exit 1
# }

# --- Publish MQTT Message (using locally installed mosquitto_pub) ---
try {
    Write-Host "Publishing payload to ${mqttBroker}:${mqttPort} on topic '$mqttTopic' using local mosquitto_pub.exe via stdin..."
    # Ensure mosquitto_pub.exe is in your PATH (which it should be based on Get-Command)
    # Add username and password flags
    # Add --cafile for TLS connection
    # Use -s to read payload from stdin and pipe $payloadJson to it
    $payloadJson | mosquitto_pub.exe -h $mqttBroker -p $mqttPort -u $mqttUsername -P $mqttPassword --cafile ../certs/emqxsl-ca.crt -t "$mqttTopic" -s
    if ($LASTEXITCODE -ne 0) { 
        Write-Warning "Mosquitto_pub.exe finished with exit code $LASTEXITCODE. Check connection & broker logs."
    } else {
        Write-Host "Mosquitto_pub.exe executed successfully."
    } 
} catch {
    Write-Error "An error occurred during MQTT publishing: $_"
} finally {
    # --- REMOVED Clean up the temporary file on the host ---
    # if (Test-Path $tempPayloadFileHost) {
    #     Write-Host "Cleaning up temporary file on host: $tempPayloadFileHost"
    #     Remove-Item $tempPayloadFileHost -Force
    # }
}

Write-Host "`nScript finished. Check API logs for session $sessionId."
