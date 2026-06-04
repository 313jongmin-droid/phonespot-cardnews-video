$ErrorActionPreference = "Stop"

$root = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$archive = Join-Path $root "CODEX_LEGACY_PATCHES_20260601.zip"

function Assert-InWorkspace {
    param([string]$Path)

    $resolved = (Resolve-Path -LiteralPath $Path).Path
    $prefix = $root + [IO.Path]::DirectorySeparatorChar
    if (-not $resolved.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to modify a path outside the Codex workspace: $resolved"
    }
    return $resolved
}

$activeFiles = @(
    "RUN_APPLY_CODEX_CURRENT_BASELINE.bat",
    "APPLY_CODEX_KOREAN_CAPTION_GUARD.py",
    "APPLY_CODEX_SOURCE_IMAGE_ONCE_GUARD.py",
    "APPLY_CODEX_VIDEO_DESK.py",
    "APPLY_CODEX_GUIDE_BASELINE.py",
    "APPLY_CODEX_MASTER_VIDEO_GUIDE.py",
    "RUN_APPLY_CODEX_MASTER_VIDEO_GUIDE.bat",
    "CODEX_MASTER_VIDEO_GUIDE.md",
    "APPLY_CODEX_DISABLE_CAPTION_HIGHLIGHT.py",
    "RUN_APPLY_CODEX_DISABLE_CAPTION_HIGHLIGHT.bat",
    "CODEX_DISABLE_CAPTION_HIGHLIGHT_GUIDE.md",
    "APPLY_CODEX_FIXED_CAPTION_RHYTHM.py",
    "RUN_APPLY_CODEX_FIXED_CAPTION_RHYTHM.bat",
    "CODEX_FIXED_CAPTION_RHYTHM_GUIDE.md",
    "ROLLBACK_CODEX_FIXED_CAPTION_RHYTHM.py",
    "RUN_ROLLBACK_CODEX_FIXED_CAPTION_RHYTHM.bat",
    "APPLY_CODEX_TTS_CAPTION_LOCKSTEP.py",
    "RUN_APPLY_CODEX_TTS_CAPTION_LOCKSTEP.bat",
    "CODEX_TTS_CAPTION_LOCKSTEP_GUIDE.md",
    "APPLY_CODEX_RESULTS_PACKAGE_V2.py",
    "RUN_APPLY_CODEX_RESULTS_PACKAGE_V2.bat",
    "CODEX_RESULTS_PACKAGE_V2_GUIDE.md",
    "APPLY_CODEX_FAST_ILLUSTRATION_DESK.py",
    "APPLY_CODEX_CLEAN_ILLUSTRATION_SCOUT.py",
    "OPEN_CODEX_VIDEO_DESK.bat",
    "CODEX_REGRESSION_AUDIT.py",
    "RUN_CODEX_REGRESSION_AUDIT.bat",
    "CODEX_TOKEN_DIET.md",
    "CODEX_CURRENT_BASELINE_GUIDE.md",
    "CODEX_BASELINE_AUDIT_20260601.md",
    "BACKUP_CODEX_CURRENT_BASELINE.py",
    "RUN_BACKUP_CODEX_CURRENT_BASELINE.bat",
    "CLEAN_CODEX_CONFIRMED_JUNK.ps1",
    "RUN_PREVIEW_CODEX_CONFIRMED_JUNK.bat",
    "RUN_DELETE_CODEX_CONFIRMED_JUNK.bat",
    "CLEAN_CODEX_WORKSPACE.ps1",
    "RUN_CLEAN_CODEX_WORKSPACE.bat",
    "CODEX_LEGACY_PATCHES_20260601.zip"
)

$legacyFiles = @(
    Get-ChildItem -LiteralPath $root -File |
        Where-Object {
            $activeFiles -notcontains $_.Name -and
            $_.Extension -in ".py", ".bat", ".ps1", ".md"
        }
)

$generatedDirs = @(
    "promo_review_frames",
    "cardnews_review_frames",
    "video_review_frames",
    "__pycache__",
    "_korean_guard_fixture",
    "_korean_guard_fixture_v2",
    "_fixed_caption_fixture_20260602",
    "_fixed_caption_fixture_v2_20260602",
    "_fixed_caption_fixture_v3_20260602",
    "_rollback_empty_fixture_20260602",
    "_desk_migration_fixture_20260602"
)

Write-Host "============================================================"
Write-Host " PhoneSpot Codex - Workspace Cleanup"
Write-Host "============================================================"
Write-Host ""
Write-Host "Active runtime files are preserved."
Write-Host "Legacy patch files to archive: $($legacyFiles.Count)"

if ($legacyFiles.Count -gt 0) {
    if (Test-Path -LiteralPath $archive) {
        Remove-Item -LiteralPath $archive -Force
    }

    $legacyFiles | ForEach-Object { Assert-InWorkspace $_.FullName | Out-Null }
    Compress-Archive -LiteralPath $legacyFiles.FullName -DestinationPath $archive -CompressionLevel Optimal

    if (-not (Test-Path -LiteralPath $archive)) {
        throw "Legacy archive was not created."
    }

    foreach ($file in $legacyFiles) {
        $safePath = Assert-InWorkspace $file.FullName
        Remove-Item -LiteralPath $safePath -Force
    }
}

$deletedDirs = 0
foreach ($name in $generatedDirs) {
    $path = Join-Path $root $name
    if (Test-Path -LiteralPath $path) {
        $safePath = Assert-InWorkspace $path
        Remove-Item -LiteralPath $safePath -Recurse -Force
        $deletedDirs++
    }
}

Write-Host ""
Write-Host "[OK] Archived legacy files: $($legacyFiles.Count)"
Write-Host "[OK] Deleted generated folders: $deletedDirs"
Write-Host "[OK] Archive: $archive"
Write-Host ""
