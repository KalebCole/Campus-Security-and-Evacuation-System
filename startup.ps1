# Set mock value here
$MOCK_VALUE = $true

# Get the directory of the script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Save the current location
$originalLocation = Get-Location

try {
    # Print mock value
    Write-Host "MOCK_VALUE=$MOCK_VALUE"


    # Define virtual environment path
    $venvPath = "$scriptDir\venv"

    # Check if virtual environment exists
    if (!(Test-Path -Path $venvPath)) {
        Write-Host "Virtual environment not found. Creating..."
        & "python.exe" -m venv $venvPath
    }

    # Activate the virtual environment
    & "$venvPath\Scripts\activate"

    # Install base requirements
    Write-Host "Installing base requirements..."
    & "$venvPath\Scripts\pip" install -r "$scriptDir\requirements.txt"

    # Install model requirements only if not mocked
    if (!$MOCK_VALUE) {
        Write-Host "Installing model requirements..."
        & "$venvPath\Scripts\pip" install -r "$scriptDir\requirements-model.txt"
    }

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