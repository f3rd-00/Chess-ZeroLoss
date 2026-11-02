param([switch]$Force)

$ErrorActionPreference = 'Stop'

$projectRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$modelDirectory = Join-Path $projectRoot 'stockfish-windosws-x86-64-universal\stockfish'
$enginePath = Join-Path $modelDirectory 'stockfish-windows-x86-64-universal.exe'
$releaseUrl = 'https://github.com/official-stockfish/Stockfish/releases/latest/download'
$archiveName = 'stockfish-windows-x86-64-universal.zip'
$downloadUrl = "$releaseUrl/$archiveName"

if ((Test-Path -LiteralPath $enginePath) -and -not $Force) {
    Write-Host "O motor já existe em: $enginePath"
    Write-Host 'Use .\setup.ps1 -Force para instalar a versão mais recente.'
    exit 0
}

$tempName = "stockfish-setup-$([Guid]::NewGuid().ToString('N'))"
$tempDirectory = Join-Path ([IO.Path]::GetTempPath()) $tempName
$archivePath = Join-Path $tempDirectory 'stockfish.zip'
$extractDirectory = Join-Path $tempDirectory 'extracted'

try {
    New-Item -ItemType Directory -Path $tempDirectory -Force | Out-Null
    New-Item -ItemType Directory -Path $extractDirectory -Force | Out-Null
    New-Item -ItemType Directory -Path $modelDirectory -Force | Out-Null

    Write-Host 'Baixando Stockfish oficial para Windows x86-64...'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $downloadUrl -OutFile $archivePath -UseBasicParsing

    Write-Host 'Extraindo o executável...'
    Expand-Archive -LiteralPath $archivePath -DestinationPath $extractDirectory -Force

    $engineFile = Get-ChildItem -LiteralPath $extractDirectory -Filter '*.exe' -File -Recurse |
        Where-Object { $_.Name -match '^stockfish.*windows.*x86-64.*\.exe$' } |
        Select-Object -First 1

    if (-not $engineFile) {
        $engineFile = Get-ChildItem -LiteralPath $extractDirectory -Filter '*.exe' -File -Recurse |
            Where-Object { $_.Name -match '^stockfish.*\.exe$' } |
            Select-Object -First 1
    }

    if (-not $engineFile) {
        throw 'O arquivo baixado não contém um executável Stockfish para Windows.'
    }

    Copy-Item -LiteralPath $engineFile.FullName -Destination $enginePath -Force
    $hash = (Get-FileHash -LiteralPath $enginePath -Algorithm SHA256).Hash
    Write-Host "Stockfish instalado em: $enginePath"
    Write-Host "SHA-256: $hash"
}
finally {
    if (Test-Path -LiteralPath $tempDirectory) {
        Remove-Item -LiteralPath $tempDirectory -Recurse -Force
    }
}
