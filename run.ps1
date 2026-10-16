param([Parameter(Mandatory=$false)][string]$Url)
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
if ($Url) {
    & $python "$PSScriptRoot\vocal_remover.py" $Url @args
} else {
    & $python "$PSScriptRoot\vocal_remover.py" @args
}

