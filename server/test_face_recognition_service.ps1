# Set base URL
$baseUrl = "http://localhost:5001"

# 1. Health check
Write-Host "`n----- Checking /health endpoint -----"
try {
    $healthResponse = Invoke-RestMethod -Uri "$baseUrl/health" -Method GET
    Write-Host "Health Status:" ($healthResponse | ConvertTo-Json -Depth 10)
} catch {
    Write-Host "Failed to reach /health endpoint" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
}

# 2. Test /embed endpoint
Write-Host "`n----- Testing /embed endpoint -----"

# Path to a test image (you'll need to update this path)
$imagePath = "C:\Users\kaleb\Documents\00_College\Campus-Security-and-Evacuation-System\server\face_recognition\tests\test_images\thomas.jpg"

if (Test-Path $imagePath) {
    # Read image and encode to Base64
    $imageBytes = Get-Content -Path $imagePath -Encoding Byte
    $base64Image = [Convert]::ToBase64String($imageBytes)

    # Build request body
    $body = @{
        image = $base64Image
    } | ConvertTo-Json

    try {
        $embedResponse = Invoke-RestMethod -Uri "$baseUrl/embed" -Method POST -ContentType "application/json" -Body $body
        Write-Host "Embedding Response:" ($embedResponse | ConvertTo-Json -Depth 10)
    } catch {
        Write-Host "Failed to reach /embed endpoint" -ForegroundColor Red
        Write-Host "Error: $_" -ForegroundColor Red
    }
} else {
    Write-Host "Test image not found at $imagePath" -ForegroundColor Red
}

# 3. Test /verify endpoint if embeddings available
if ($embedResponse -and $embedResponse.embedding) {
    $embedding = $embedResponse.embedding

    # Prepare verify request
    $verifyBody = @{
        embedding1 = $embedding
        embedding2 = $embedding  # Using same embedding to test
    } | ConvertTo-Json

    Write-Host "`n----- Testing /verify endpoint -----"
    try {
        $verifyResponse = Invoke-RestMethod -Uri "$baseUrl/verify" -Method POST -ContentType "application/json" -Body $verifyBody
        Write-Host "Verification Response:" ($verifyResponse | ConvertTo-Json -Depth 10)
    } catch {
        Write-Host "Failed to reach /verify endpoint" -ForegroundColor Red
        Write-Host "Error: $_" -ForegroundColor Red
    }
}

Write-Host "`nAll tests complete.`n"