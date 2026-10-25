# Revisa que todo esté instalado y hace una prueba chiquita de punta a punta, sin material de nadie:
# arma un video de prueba de 6 s (con la voz de Windows), lo transcribe, mide su estilo, le quita las pausas,
# le pone subtítulos, lo mezcla con un riser y lo entrega. Tarda 1–3 minutos. Es el de Windows; en Mac:
# bash herramientas/chequeo.sh
#
#   powershell -ExecutionPolicy Bypass -File herramientas\chequeo.ps1           todo
#   powershell -ExecutionPolicy Bypass -File herramientas\chequeo.ps1 -Rapido   sólo revisa que esté instalado
param([switch]$Rapido)

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$RAIZ = Split-Path -Parent $PSScriptRoot
Set-Location $RAIZ
$script:FALLAS = 0
function Ok($t)  { Write-Output "✅ $t" }
function Mal($t) { Write-Output "❌ $t"; $script:FALLAS++ }
$ARREGLO = 'powershell -ExecutionPolicy Bypass -File herramientas\instalar.ps1'

# Lo recién instalado con winget puede no estar en el PATH de esta ventana: se vuelve a leer.
$todo = @([Environment]::GetEnvironmentVariable('Path', 'Machine'), [Environment]::GetEnvironmentVariable('Path', 'User'),
          (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links'), (Join-Path $env:ProgramFiles 'WinGet\Links'),
          (Join-Path $env:ProgramData 'chocolatey\bin'), $env:Path) | Where-Object { $_ }
$env:Path = ($todo -join ';')

$PY = Join-Path $RAIZ '.venv\Scripts\python.exe'
$hayVenv = Test-Path $PY
if (-not $hayVenv) { $c = Get-Command python -ErrorAction SilentlyContinue; $PY = if ($c) { $c.Source } else { 'python' } }

Write-Output 'Editar con IA · chequeo (Windows)'
if (Get-Command winget -ErrorAction SilentlyContinue) { Ok 'winget' } else { Write-Output '·  winget no está (sólo hace falta para instalar; ver PROMPT-DE-INSTALACION.md)' }

# Lo que encuentran los scripts (herramientas\comun.py), para que el chequeo vea lo mismo que ellos.
$info = $null
try { $info = (& $PY herramientas\comun.py 2>$null | Out-String) | ConvertFrom-Json } catch { $info = $null }
if (-not $info) { $info = [pscustomobject]@{ ffmpeg = $null; ffprobe = $null; whisper = $null; 'yt-dlp' = $null; modelo = '' } }

if ($info.ffmpeg) {
    $v = ((& $info.ffmpeg -version 2>$null) | Select-Object -First 1) -split ' '
    Ok "ffmpeg $($v[2])"
} else { Mal "ffmpeg  → $ARREGLO" }
if ($info.ffprobe) { Ok 'ffprobe' } else { Mal "ffprobe  → $ARREGLO" }
if ($info.whisper) { Ok "whisper-cpp ($(Split-Path -Leaf $info.whisper))" } else { Mal "whisper-cpp  → $ARREGLO" }
if ($info.'yt-dlp') { Ok 'yt-dlp (para links)' } else { Mal "yt-dlp  → $ARREGLO" }
if ($info.modelo) { Ok "modelo de Whisper ($(Split-Path -Leaf $info.modelo))" } else { Mal "modelo de Whisper  → $ARREGLO" }
if ($hayVenv) { Ok 'Python del proyecto (.venv)' } else { Mal "Python del proyecto (.venv)  → $ARREGLO" }
& $PY -c 'import PIL, numpy' 2>$null
if ($LASTEXITCODE -eq 0) { Ok 'Pillow y numpy' } else { Mal "Pillow y numpy  → $ARREGLO" }
Write-Output '·  caras y textos: no se miden solos en Windows (Claude los revisa en la hoja de cuadros)'
if (Get-ChildItem 'material\03-musica-y-efectos\risers\*.wav' -ErrorAction SilentlyContinue) { Ok 'efectos de sonido propios' } else { Mal "efectos propios  → $ARREGLO" }
Write-Output '·  voz IA local: por ahora sólo en Mac (opcional)'

if ($Rapido) {
    Write-Output ''
    if ($script:FALLAS -eq 0) { Write-Output 'Todo instalado.' } else { Write-Output "$($script:FALLAS) cosa(s) por arreglar." }
    exit $script:FALLAS
}
if ($script:FALLAS -gt 0) {
    Write-Output ''
    Write-Output "Faltan $($script:FALLAS) cosa(s): corre  $ARREGLO  y vuelve a probar."
    exit 1
}

# La prueba de punta a punta es la misma en Mac y en Windows (herramientas\prueba_completa.py).
& $PY herramientas\prueba_completa.py
exit $LASTEXITCODE
