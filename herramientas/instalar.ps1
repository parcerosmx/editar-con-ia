# Instala lo que necesita «Editar con IA» en Windows 10/11 (64 bits). Se puede correr las veces que sea:
# lo que ya está, se salta.
#
#   powershell -ExecutionPolicy Bypass -File herramientas\instalar.ps1        dice qué falta y pregunta antes
#   powershell -ExecutionPolicy Bypass -File herramientas\instalar.ps1 -Si    instala sin preguntar (ya dijiste que sí)
#   powershell -ExecutionPolicy Bypass -File herramientas\instalar.ps1 -Ayuda muestra esto
#
# Qué instala (todo corre en tu computadora; nada de tus videos sale a internet):
#   · ffmpeg        corta, une y mide el video y el audio            (winget: Gyan.FFmpeg)
#   · yt-dlp        baja videos de un link para estudiarlos           (winget: yt-dlp.yt-dlp)
#   · Python 3.12   si no tienes uno                                  (winget: Python.Python.3.12)
#   · whisper.cpp   transcribe lo que se dice, con el segundo exacto  (zip oficial de GitHub → herramientas\whisper\)
#   · el modelo de Whisper que entiende español (large-v3-turbo, ~1,6 GB) en herramientas\modelos\
#   · un Python propio del proyecto (.venv) con Pillow y numpy
#   · efectos de sonido propios (risers, woosh, ding) en material\03-musica-y-efectos\
#
# winget es el instalador de programas que trae Windows. Si no está, se usa Chocolatey sólo si ya existe
# (así corre la prueba automática de GitHub). WHISPER_MODELO_NOMBRE=ggml-base.bin baja un modelo chico (sólo
# para esa prueba). Nunca pide ni escribe contraseñas: si Windows pregunta «¿Permitir cambios?», le das Sí tú.
param([switch]$Si, [switch]$Voz, [switch]$Ayuda)

$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'      # Invoke-WebRequest es 10 veces más lento con la barra
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch {}

$RAIZ = Split-Path -Parent $PSScriptRoot
Set-Location $RAIZ

if ($Ayuda) {
    Get-Content $PSCommandPath -Encoding UTF8 | Select-Object -Skip 0 -First 19 | ForEach-Object { $_ -replace '^# ?', '' }
    exit 0
}

function Ok($t)   { Write-Output "✅ $t" }
function Depurar($t) { if ($env:EDITAR_DEPURAR) { [Console]::Error.WriteLine("   [depurar] $t") } }
function Nota($t) { Write-Output "   $t" }
function Mal($t)  { Write-Output "❌ $t" }

$MODELO = if ($env:WHISPER_MODELO_NOMBRE) { $env:WHISPER_MODELO_NOMBRE } else { 'ggml-large-v3-turbo.bin' }
$MINIMO = if ($MODELO -like '*large*') { 1500000000 } else { 30000000 }
$URL_MODELO = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$MODELO"
$WHISPER_DIR = Join-Path $RAIZ 'herramientas\whisper'
$MODELOS_DIR = Join-Path $RAIZ 'herramientas\modelos'
$VENV_PY = Join-Path $RAIZ '.venv\Scripts\python.exe'

# ── utilidades ─────────────────────────────────────────────────────────────

function Refrescar-Path {
    # Lo que winget acaba de instalar todavía no está en el PATH de esta ventana: se vuelve a leer.
    $maq = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $usr = [Environment]::GetEnvironmentVariable('Path', 'User')
    $extra = @(
        (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links'),
        (Join-Path $env:ProgramFiles 'WinGet\Links'),
        (Join-Path $env:ProgramData 'chocolatey\bin')
    )
    $extra += Get-ChildItem -Path (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages') -Directory -Filter 'Gyan.FFmpeg*' -ErrorAction SilentlyContinue |
        ForEach-Object { Get-ChildItem $_.FullName -Directory -ErrorAction SilentlyContinue } |
        ForEach-Object { Join-Path $_.FullName 'bin' }
    $todo = @($maq, $usr) + $extra | Where-Object { $_ -and (Test-Path $_) }
    $env:Path = ($todo -join ';')
}

function Tiene($nombre) { return [bool](Get-Command $nombre -ErrorAction SilentlyContinue) }

function Python-Real {
    # Un Python 3.9+ de verdad (no el atajo de la Microsoft Store que sólo abre la tienda).
    # Devuelve @(programa, argumentos...) o $null.
    $intentos = @(@('py', '-3.12'), @('py', '-3.11'), @('py', '-3'), @('python'), @('python3'))
    foreach ($i in $intentos) {
        $cmd = Get-Command $i[0] -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        if ($cmd.Source -like '*WindowsApps*') { continue }
        $resto = @($i | Select-Object -Skip 1)
        & $cmd.Source @resto -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>$null | Out-Null
        Depurar "python: $($cmd.Source) $resto → $LASTEXITCODE"
        if ($LASTEXITCODE -eq 0) { return ,(@($cmd.Source) + $resto) }
    }
    return $null
}

function Whisper-Exe {
    $w = Get-ChildItem -Path $WHISPER_DIR -Recurse -Filter 'whisper-cli.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($w) { return $w.FullName }
    return $null
}

function Preguntar($texto) {
    if ($Si) { return $true }
    $interactivo = [Environment]::UserInteractive
    try { if ([Console]::IsInputRedirected) { $interactivo = $false } } catch {}
    if (-not $interactivo) {
        Nota 'Para instalarlo sin preguntar: powershell -ExecutionPolicy Bypass -File herramientas\instalar.ps1 -Si'
        return $false
    }
    $r = Read-Host "   $texto [s/N]"
    return ($r -match '^(s|si|sí)$')
}

function Bajar($url, $destino) {
    # Con curl.exe (viene con Windows 10/11) se sigue donde se quedó si se corta; si no, Invoke-WebRequest.
    $part = "$destino.part"
    $curl = Get-Command 'curl.exe' -ErrorAction SilentlyContinue
    if ($curl) {
        & $curl.Source -L --fail --retry 3 --progress-bar -C - -o $part $url | Out-Null
        Depurar "curl $url → $LASTEXITCODE"
        if ($LASTEXITCODE -ne 0) {
            # si curl no pudo (proxy, antivirus…), se intenta una vez con Invoke-WebRequest, desde cero
            Remove-Item $part -Force -ErrorAction SilentlyContinue
            try { Invoke-WebRequest -Uri $url -OutFile $part -UseBasicParsing } catch { Depurar "$_"; return $false }
        }
    } else {
        try { Invoke-WebRequest -Uri $url -OutFile $part -UseBasicParsing } catch { Depurar "$_"; return $false }
    }
    Move-Item -Force $part $destino
    return $true
}

# ── 0 · ¿esta computadora sirve? ───────────────────────────────────────────

if ($env:OS -ne 'Windows_NT') { Mal 'Esto es para Windows. En Mac: bash herramientas/instalar.sh'; exit 1 }
if (-not [Environment]::Is64BitOperatingSystem) { Mal 'Hace falta Windows de 64 bits.'; exit 1 }
Write-Output "Editar con IA · instalación en $RAIZ"
Write-Output ''
Refrescar-Path

# ── 1 · qué falta ──────────────────────────────────────────────────────────

$paquetes = @()       # @(id de winget, id de choco, nombre)
if (Tiene 'ffmpeg') { Ok 'ffmpeg' } else { $paquetes += ,@('Gyan.FFmpeg', 'ffmpeg', 'ffmpeg') }
if (Tiene 'yt-dlp') { Ok 'yt-dlp' } else { $paquetes += ,@('yt-dlp.yt-dlp', 'yt-dlp', 'yt-dlp') }
$py = Python-Real
if ($py) { Ok "Python ($($py -join ' '))" } else { $paquetes += ,@('Python.Python.3.12', 'python312', 'Python 3.12') }
$whisper = Whisper-Exe
if ($whisper) { Ok 'whisper.cpp' }
$destModelo = Join-Path $MODELOS_DIR $MODELO
$hayModelo = (Test-Path $destModelo) -and ((Get-Item $destModelo).Length -gt $MINIMO)
if ($hayModelo) { Ok "modelo de Whisper ($MODELO)" }
$hayVenv = $false
if (Test-Path $VENV_PY) { & $VENV_PY -c 'import PIL, numpy' 2>$null; $hayVenv = ($LASTEXITCODE -eq 0) }
if ($hayVenv) { Ok 'Python del proyecto (.venv con Pillow y numpy)' }

$plan = @()
foreach ($p in $paquetes) { $plan += "$($p[2]) (con winget)" }
if (-not $whisper) { $plan += 'whisper.cpp (zip oficial de GitHub, ~5 MB, en herramientas\whisper)' }
if (-not $hayModelo) {
    $peso = if ($MODELO -like '*large*') { '~1,6 GB, se baja una vez' } else { 'modelo chico de prueba' }
    $plan += "el modelo de Whisper que entiende español: $MODELO ($peso)"
}
if (-not $hayVenv) { $plan += 'el Python del proyecto en .venv (Pillow y numpy, ~60 MB)' }

if ($plan.Count -gt 0) {
    Write-Output ''
    Write-Output '• Voy a instalar:'
    foreach ($x in $plan) { Nota "· $x" }
    if (-not (Preguntar '¿Lo instalo?')) { Mal 'No instalé nada. Vuelve a correr esto cuando quieras.'; exit 1 }
}

# ── 2 · programas con winget (o Chocolatey si no hay winget, como en la prueba de GitHub) ─────────

if ($paquetes.Count -gt 0) {
    $winget = Get-Command 'winget' -ErrorAction SilentlyContinue
    $choco = Get-Command 'choco' -ErrorAction SilentlyContinue
    if (-not $winget -and -not $choco) {
        Mal 'Falta winget, el instalador de programas de Windows.'
        Nota '1. Abre la Microsoft Store (búscala en el menú Inicio).'
        Nota '2. Busca «Instalador de aplicación» (App Installer) y dale Instalar o Actualizar.'
        Nota '3. Cuando termine, vuelve aquí y corre otra vez este instalador.'
        exit 2
    }
    foreach ($p in $paquetes) {
        Write-Output "• Instalando $($p[2])… (si Windows pregunta «¿Permitir cambios?», dale Sí)"
        if ($winget) {
            & $winget.Source install --id $p[0] -e --source winget --accept-source-agreements --accept-package-agreements --silent --disable-interactivity
            $codigo = $LASTEXITCODE
            # -1978335189 = ya estaba instalado y no hay versión nueva: también sirve
            $bien = ($codigo -eq 0 -or $codigo -eq -1978335189 -or $codigo -eq -1978335135)
        } else {
            & $choco.Source install $p[1] -y --no-progress
            $codigo = $LASTEXITCODE
            $bien = ($codigo -eq 0)
        }
        if (-not $bien) { Mal "No se pudo instalar $($p[2]) (código $codigo). Pásale esto a Claude."; exit 1 }
        Ok "instalado: $($p[2])"
    }
    Refrescar-Path
    if (-not (Tiene 'ffmpeg')) { Mal 'ffmpeg quedó instalado pero esta ventana no lo ve: cierra y abre Claude, y vuelve a correr esto.'; exit 2 }
    $py = Python-Real
}

# ── 3 · whisper.cpp: el zip oficial (CPU, 64 bits) ─────────────────────────

if (-not $whisper) {
    Write-Output '• Bajando whisper.cpp (la última versión publicada en GitHub)…'
    New-Item -ItemType Directory -Force -Path $WHISPER_DIR | Out-Null
    $url = $null
    try {
        $cab = @{ 'User-Agent' = 'editar-con-ia' }
        if ($env:GITHUB_TOKEN) { $cab['Authorization'] = "Bearer $env:GITHUB_TOKEN" }
        $rel = Invoke-RestMethod -Uri 'https://api.github.com/repos/ggml-org/whisper.cpp/releases/latest' -Headers $cab -UseBasicParsing
        $url = ($rel.assets | Where-Object { $_.name -eq 'whisper-bin-x64.zip' } | Select-Object -First 1).browser_download_url
        if ($url) { Nota "versión $($rel.tag_name)" }
    } catch { Depurar "API de GitHub: $_" }
    if (-not $url) { $url = 'https://github.com/ggml-org/whisper.cpp/releases/latest/download/whisper-bin-x64.zip' }
    $zip = Join-Path $WHISPER_DIR 'whisper-bin-x64.zip'
    if (-not (Bajar $url $zip)) { Mal 'No se pudo bajar whisper.cpp (¿internet?). Vuelve a correr esto.'; exit 1 }
    try { Expand-Archive -Path $zip -DestinationPath $WHISPER_DIR -Force } catch { Mal "No se pudo abrir el zip de whisper.cpp: $_"; exit 1 }
    Remove-Item $zip -Force -ErrorAction SilentlyContinue
    $whisper = Whisper-Exe
    if (-not $whisper) { Mal 'El zip de whisper.cpp no traía whisper-cli.exe. Pásale esto a Claude.'; exit 1 }
    Ok 'whisper.cpp'
}
# ¿arranca? Si falta el «Visual C++» de Microsoft (pasa en Windows recién instalados), se instala.
& $whisper --help *> $null
if ($LASTEXITCODE -eq -1073741515) {
    Write-Output '• A whisper.cpp le falta una pieza de Windows (Visual C++ Redistributable).'
    $winget = Get-Command 'winget' -ErrorAction SilentlyContinue
    if ($winget -and (Preguntar '¿La instalo?')) {
        & $winget.Source install --id Microsoft.VCRedist.2015+.x64 -e --source winget --accept-source-agreements --accept-package-agreements --silent --disable-interactivity
    }
    & $whisper --help *> $null
    if ($LASTEXITCODE -eq -1073741515) { Mal 'whisper.cpp no arranca: falta Visual C++ Redistributable (x64) de Microsoft.'; exit 1 }
}

# ── 4 · el modelo de Whisper ───────────────────────────────────────────────

if (-not $hayModelo) {
    New-Item -ItemType Directory -Force -Path $MODELOS_DIR | Out-Null
    $cache = Join-Path $HOME ".cache\whisper.cpp\$MODELO"
    if ((Test-Path $cache) -and ((Get-Item $cache).Length -gt $MINIMO)) {
        Copy-Item $cache $destModelo
        Ok 'modelo de Whisper (ya estaba en esta computadora; se copió, no se volvió a bajar)'
    } else {
        Write-Output "• Bajando el modelo de Whisper ($MODELO)… si se corta, vuelve a correr esto: sigue donde se quedó."
        if (-not (Bajar $URL_MODELO $destModelo)) { Mal 'No se pudo bajar el modelo (¿internet?). Vuelve a correr esto: sigue donde se quedó.'; exit 1 }
        Ok "modelo de Whisper ($MODELO)"
    }
}

# ── 5 · el Python del proyecto ─────────────────────────────────────────────

if (-not $hayVenv) {
    if (-not $py) { Mal 'No encontré Python. Cierra y abre Claude (para que vea lo instalado) y vuelve a correr esto.'; exit 2 }
    Write-Output '• Creando el Python del proyecto en .venv…'
    $prog = $py[0]; $resto = @($py | Select-Object -Skip 1)
    & $prog @resto -m venv .venv
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VENV_PY)) { Mal 'No se pudo crear .venv'; exit 1 }
    & $VENV_PY -m pip install -q --disable-pip-version-check --upgrade pip
    & $VENV_PY -m pip install -q --disable-pip-version-check -r herramientas\requirements.txt
    if ($LASTEXITCODE -ne 0) { Mal 'No se pudieron instalar Pillow y numpy en .venv'; exit 1 }
    Ok 'Python del proyecto'
}

# ── 6 · efectos de sonido propios ──────────────────────────────────────────

if (Get-ChildItem 'material\03-musica-y-efectos\risers\*.wav' -ErrorAction SilentlyContinue) {
    Ok 'efectos de sonido propios'
} else {
    & $VENV_PY herramientas\sintetizar_efectos.py | Out-Null
    if ($LASTEXITCODE -eq 0) { Ok 'efectos de sonido propios (risers, woosh, ding)' } else { Mal 'No se pudieron crear los efectos de sonido'; exit 1 }
}

if ($Voz) { Nota 'La voz IA local (ClearerVoice) por ahora sólo se instala en Mac. La «mejora de voz» de CapCut da algo parecido.' }

Write-Output ''
Write-Output 'Listo. Para comprobar que todo funciona:  powershell -ExecutionPolicy Bypass -File herramientas\chequeo.ps1'
exit 0
