# Get the directory of the script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Save the current location
$originalLocation = Get-Location

try {
    # Set the location to the server directory relative to the script's location
    Set-Location -Path "$scriptDir\server"

    # Activate the virtual environment
    & "$scriptDir\server\venv\Scripts\activate"

    # Start the server
    & "python.exe" "$scriptDir\server\app.py"
} catch {
    Write-Error $_
} finally {
    # Return to the original location
    Set-Location -Path $originalLocation
}