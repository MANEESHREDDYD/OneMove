$ErrorActionPreference = "Stop"

$url = "https://download.geofabrik.de/asia/india/southern-zone-latest.osm.pbf"
$md5Url = "https://download.geofabrik.de/asia/india/southern-zone-latest.osm.pbf.md5"

$outDir = ".\data\osm"
if (!(Test-Path $outDir)) {
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
}

$outFile = Join-Path $outDir "southern-zone-latest.osm.pbf"
$md5File = Join-Path $outDir "southern-zone-latest.osm.pbf.md5"

Write-Host "Downloading MD5 checksum..."
Invoke-WebRequest -Uri $md5Url -OutFile $md5File

$expectedMd5 = (Get-Content $md5File).Split(" ")[0]

if (Test-Path $outFile) {
    Write-Host "File exists, verifying checksum..."
    $stream = [System.IO.File]::OpenRead((Resolve-Path $outFile).Path)
    $hasher = [System.Security.Cryptography.MD5]::Create()
    $hash = [System.BitConverter]::ToString($hasher.ComputeHash($stream)).Replace("-","").ToLower()
    $stream.Close()
    
    if ($hash -eq $expectedMd5) {
        Write-Host "Checksum matches. No need to download."
        exit 0
    } else {
        Write-Host "Checksum mismatch. Redownloading..."
    }
}

Write-Host "Downloading PBF file..."
Invoke-WebRequest -Uri $url -OutFile $outFile

$stream = [System.IO.File]::OpenRead((Resolve-Path $outFile).Path)
$hasher = [System.Security.Cryptography.MD5]::Create()
$hash = [System.BitConverter]::ToString($hasher.ComputeHash($stream)).Replace("-","").ToLower()
$stream.Close()

if ($hash -ne $expectedMd5) {
    Write-Error "Downloaded file checksum ($hash) does not match expected ($expectedMd5)."
} else {
    Write-Host "Download and verification successful."
}
