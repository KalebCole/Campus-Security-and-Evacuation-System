# Get the directory of the script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Set the location to the server directory relative to the script's location
Set-Location -Path "$scriptDir\server"

# Activate the virtual environment
& "$scriptDir\server\venv\Scripts\activate"

# Start the server
& "python.exe" "$scriptDir\server\app.py"