# setup_windows.ps1
# Helper script to prepare the environment on Windows (PowerShell).
# Usage: Open PowerShell in the project directory and run:
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
#   .\setup_windows.ps1

function Write-Err($msg){ Write-Host $msg -ForegroundColor Red }
function Write-Ok($msg){ Write-Host $msg -ForegroundColor Green }

# 1) Detect Python executable (try `python`, then `py` launcher)
$pyCmd = Get-Command python -ErrorAction SilentlyContinue
$pyArgs = @()
if (-not $pyCmd) {
    # Try the py launcher (common on Windows)
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        # Use `py -3` to target Python 3
        $pyArgs = @('-3')
        Write-Host "Using 'py -3' launcher at $($pyCmd.Path)"
    } else {
        Write-Err "Python is not found on PATH and 'py' launcher is not available. Please install Python 3.10+ and ensure it's accessible from PowerShell."
        Write-Host "Download: https://www.python.org/downloads/"
        exit 1
    }
} else {
    Write-Host "Using 'python' at $($pyCmd.Path)"
}

# 2) Create virtualenv
Write-Host "Creating virtual environment 'venv'..."
& $pyCmd.Path @pyArgs -m venv venv

# 3) Activate venv in this script (note: activation persists only in interactive shell)
$activateScript = Join-Path -Path (Get-Location) -ChildPath "venv\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    Write-Host "Activating virtual environment..."
    . $activateScript
} else {
    Write-Err "Activation script not found at $activateScript"
    exit 1
}

# 4) Upgrade pip and install requirements
Write-Host "Upgrading pip and installing requirements..."
& $pyCmd.Path @pyArgs -m pip install --upgrade pip
if (Test-Path "requirements.txt") {
    & $pyCmd.Path @pyArgs -m pip install -r requirements.txt
} else {
    Write-Err "requirements.txt not found. Please create it or install dependencies manually."
    exit 1
}

Write-Ok "Setup complete. To run the app in this shell:"
Write-Host "    python app.py"

Write-Host "If activation is blocked when you try to run the app, run:"
Write-Host "    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"
Write-Host "and then re-open PowerShell and activate the venv with: .\venv\Scripts\Activate.ps1"
