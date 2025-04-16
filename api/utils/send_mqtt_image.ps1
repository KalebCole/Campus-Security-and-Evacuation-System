# --- Configuration ---
# IMPORTANT: Update this path to the ACTUAL location of EMP001.jpg on your system
$imagePath = "C:\Users\kaleb\Documents\00_College\Senior Capstone\api\static\images\test\invalid.jpg" 

$mqttBroker = "localhost" 
$mqttPort = 1883
$mqttTopic = "campus/security/session"
$deviceId = "powershell-file-pub-01"
$containerName = "mosquitto" 

# Temporary file paths
$tempPayloadFileHost = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "mqtt_payload_$(Get-Random).json")
$tempPayloadFileContainer = "/tmp/mqtt_payload.json" # Path inside the container
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

# --- Execute Docker Commands ---
try {
    # 1. Copy the temp file into the container
    Write-Host "Copying payload file into container '$containerName'..."
    docker cp "$tempPayloadFileHost" "${containerName}:$tempPayloadFileContainer"
    if ($LASTEXITCODE -ne 0) { throw "Docker cp failed!" }
    Write-Host "File copied successfully."

    # 2. Execute mosquitto_pub using the file inside the container
    Write-Host "Executing mosquitto_pub inside container using file..."
    # Note: No complex escaping needed for the payload now
    $dockerExecCommand = "docker exec $containerName sh -c `"mosquitto_pub -h $mqttBroker -p $mqttPort -t `"`"$mqttTopic`"`" -f $tempPayloadFileContainer`""
    Write-Host "Running command: $dockerExecCommand"
    Invoke-Expression $dockerExecCommand
    if ($LASTEXITCODE -ne 0) { Write-Warning "Mosquitto_pub might have encountered an issue (check container logs)." } else { Write-Host "Mosquitto_pub executed." }

    # 3. (Optional) Clean up the file inside the container
    Write-Host "Cleaning up file inside container..."
    $dockerRmCommand = "docker exec $containerName rm $tempPayloadFileContainer"
    Invoke-Expression $dockerRmCommand

} catch {
    Write-Error "An error occurred during Docker operations: $_"
} finally {
    # 4. Clean up the temporary file on the host
    if (Test-Path $tempPayloadFileHost) {
        Write-Host "Cleaning up temporary file on host: $tempPayloadFileHost"
        Remove-Item $tempPayloadFileHost -Force
    }
}

Write-Host "`nScript finished. Check API logs for session $sessionId."
