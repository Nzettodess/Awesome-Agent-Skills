param(
    [string]$ManifestPath = "sources.json",
    [string]$Filter = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ManifestPath)) {
    throw "Manifest not found: $ManifestPath"
}

$entries = Get-Content $ManifestPath -Raw | ConvertFrom-Json
if ($Filter) {
    $entries = $entries | Where-Object { $_.name -like "*$Filter*" -or $_.local -like "*$Filter*" }
}

if (-not $entries -or $entries.Count -eq 0) {
    Write-Host "No matching entries found." -ForegroundColor Yellow
    exit 0
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("skills-sync-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

$updated = @()
$failed = @()

try {
    # Group by repo + branch so each upstream repo is cloned at most once
    $groups = $entries | Group-Object { "$($_.repo)|$($_.branch)" }

    foreach ($group in $groups) {
        $first = $group.Group[0]
        $repoUrl = $first.repo
        $branch = if ($first.branch) { $first.branch } else { "main" }
        $cloneDir = Join-Path $tempRoot ("repo-" + [guid]::NewGuid().ToString("N").Substring(0, 8))

        $paths = @($group.Group | ForEach-Object { $_.path } | Select-Object -Unique)
        $needsFull = $paths -contains "."

        Write-Host "`n==> Fetching $repoUrl ($branch)" -ForegroundColor Cyan

        $prevPref = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        if ($needsFull) {
            git clone -q --depth 1 --branch $branch $repoUrl $cloneDir 2>&1 | Out-Null
        } else {
            git clone -q --depth 1 --filter=blob:none --no-checkout --branch $branch $repoUrl $cloneDir 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                git -C $cloneDir sparse-checkout init --cone 2>&1 | Out-Null
                git -C $cloneDir sparse-checkout set @paths 2>&1 | Out-Null
                git -C $cloneDir checkout -q $branch 2>&1 | Out-Null
            }
        }
        $ErrorActionPreference = $prevPref

        if ($LASTEXITCODE -ne 0) {
            Write-Host "  [ERROR] Failed to clone $repoUrl" -ForegroundColor Red
            foreach ($item in $group.Group) {
                $failed += "$($item.name) ($repoUrl)"
            }
            continue
        }

        foreach ($item in $group.Group) {
            $srcPath = if ($item.path -eq ".") { $cloneDir } else { Join-Path $cloneDir $item.path }
            $dstPath = Join-Path (Get-Location) $item.local

            if (-not (Test-Path $srcPath)) {
                Write-Host "  [WARN] Path '$($item.path)' not found in $repoUrl (for $($item.name))" -ForegroundColor Yellow
                $failed += "$($item.name) (missing path: $($item.path))"
                continue
            }

            if ($DryRun) {
                Write-Host "  [DRY-RUN] Would sync $($item.name): $($item.path) -> $($item.local)" -ForegroundColor Gray
                $updated += $item.name
                continue
            }

            if (-not (Test-Path $dstPath)) {
                New-Item -ItemType Directory -Path $dstPath -Force | Out-Null
            }

            # Mirror contents while excluding .git
            $robocopyArgs = @($srcPath, $dstPath, "/MIR", "/XD", ".git", "/NFL", "/NDL", "/NJH", "/NJS", "/NP")
            $null = & robocopy @robocopyArgs
            if ($LASTEXITCODE -ge 8) {
                Write-Host "  [ERROR] Robocopy failed for $($item.name) (exit $LASTEXITCODE)" -ForegroundColor Red
                $failed += "$($item.name) (copy error)"
            } else {
                Write-Host "  [OK] Synced $($item.name) -> $($item.local)" -ForegroundColor Green
                $updated += $item.name
            }
        }
    }
}
finally {
    if (Test-Path $tempRoot) {
        Remove-Item -Path $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "`n=== Sync Summary ===" -ForegroundColor Cyan
Write-Host "Processed: $($updated.Count)" -ForegroundColor Green

if (-not $DryRun -and $updated.Count -gt 0 -and (Test-Path "README.md")) {
    $now = Get-Date
    $offset = $now.ToString("zzz")
    $stamp = $now.ToString("yyyy-MM-dd HH:mm") + " (UTC$offset)"
    $readme = Get-Content "README.md" -Raw
    $updatedReadme = [regex]::Replace($readme, '(?m)^> \*\*Last Updated:\*\* .*$', "> **Last Updated:** $stamp")
    if ($updatedReadme -ne $readme) {
        Set-Content -Path "README.md" -Value $updatedReadme -NoNewline
        Write-Host "Updated README.md timestamp: $stamp" -ForegroundColor Cyan
    }
}

if ($failed.Count -gt 0) {
    Write-Host "Failed: $($failed.Count)" -ForegroundColor Red
    $failed | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    exit 1
}
