# Quick Ollama smoke test (no StockScope server required).
# Prerequisites: `ollama serve` running and `ollama pull llama3.1:8b`
# Usage:  powershell -File scripts/test_ollama_prompt.ps1
# Or with custom text file:  powershell -File scripts/test_ollama_prompt.ps1 -PromptFile .\my_prompt.txt

param(
    [string]$Model = "llama3.1:8b",
    [string]$Prompt = "Reply with exactly one word: OK",
    [string]$PromptFile = ""
)

$text = $Prompt
if ($PromptFile -ne "" -and (Test-Path $PromptFile)) {
    $text = Get-Content -Raw $PromptFile
}

$body = @{
    model  = $Model
    prompt = $text.Trim()
    stream = $false
} | ConvertTo-Json

$r = Invoke-RestMethod -Uri "http://localhost:11434/api/generate" -Method Post -Body $body -ContentType "application/json"
Write-Output $r.response
