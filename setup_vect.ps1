# setup_vect.ps1 — one-shot setup for Vect on Windows
# Run from the project root: .\setup_vect.ps1

Write-Host "Setting up Vect..." -ForegroundColor Cyan

# Create venv with Python 3.11
py -3.11 -m venv venv
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python 3.11 not found. Install from python.org." -ForegroundColor Red
    exit 1
}

# Install dependencies
venv\Scripts\pip install -r requirements.txt --quiet
venv\Scripts\pip install -e . --quiet

# Verify LLVM backend
venv\Scripts\python -c "import llvmlite.binding as llvm; llvm.initialize(); llvm.initialize_native_target(); llvm.initialize_native_asmprinter(); print('LLVM backend OK')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: LLVM backend failed. Check Python version (must be 3.9-3.12)." -ForegroundColor Red
    exit 1
}

# Install VS Code extension
$ext_dest = "$env:USERPROFILE\.vscode\extensions\vect-lang-0.1.0"
if (Test-Path "$env:USERPROFILE\.vscode") {
    if (Test-Path $ext_dest) { Remove-Item -Recurse -Force $ext_dest }
    Copy-Item -Recurse vscode-extension $ext_dest
    Write-Host "VS Code extension installed." -ForegroundColor Green
}

Write-Host ""
Write-Host "Vect is ready!" -ForegroundColor Green
Write-Host "  venv\Scripts\vect run examples\demo.vect    <- run the demo"
Write-Host "  venv\Scripts\vect                           <- start the REPL"
Write-Host "  venv\Scripts\pytest tests\                  <- run tests"
