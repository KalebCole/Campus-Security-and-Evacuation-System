# Get the directory of the script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Save the current location
$originalLocation = Get-Location

try {
    # Set the location to the server directory relative to the script's location
    Set-Location -Path "$scriptDir\server"

    # Define virtual environment path
    $venvPath = "$scriptDir\server\venv"

    # Check if virtual environment exists
    if (!(Test-Path -Path $venvPath)) {
        Write-Host "Virtual environment not found. Creating..."
        # Create virtual environment
        & "python.exe" -m venv $venvPath
        Write-Host "Virtual environment created."
    }

    # Activate the virtual environment
    & "$venvPath\Scripts\activate"

    # Install requirements
    Write-Host "Installing requirements from requirements.txt..."
    & "$venvPath\Scripts\pip" install -r "$scriptDir\requirements.txt"

    # Start the server
    Write-Host "Starting the server..."
    & "python.exe" "$scriptDir\server\app.py"

} catch {
    Write-Error "An error occurred:"
    Write-Error $_
    exit 1 # Exit the script if the problem persists
} finally {
    # Return to the original location
    Set-Location -Path $originalLocation
}