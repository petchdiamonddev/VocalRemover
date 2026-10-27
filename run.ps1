param(
    [Parameter(Mandatory=$false, Position=0)]
    [string]$Url,
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$ExtraArgs
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

$script = Join-Path $PSScriptRoot "vocal_remover.py"

if ($Url) {
    & $python $script $Url @ExtraArgs
} else {
    & $python $script @ExtraArgs
}
