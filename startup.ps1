Set-Location -Path "server"

# activate the virtual environment
& "venv\Scripts\activate"

# start the server
& "python.exe" ".\app.py"
