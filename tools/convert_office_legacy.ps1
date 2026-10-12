# Convert legacy Office files (.ppt, .doc) to .pptx / .docx with the installed Office apps,
# so the RAG ingester only has to read the modern formats.
#
#   powershell -ExecutionPolicy Bypass -File tools\convert_office_legacy.ps1 <src dir> <out dir>
#
# The converted copy keeps its relative path; the original is left untouched.
param([Parameter(Mandatory)] [string]$Src, [Parameter(Mandatory)] [string]$Out)

$Src = (Resolve-Path $Src).Path
New-Item -ItemType Directory -Force $Out | Out-Null
$Out = (Resolve-Path $Out).Path
$files = @(Get-ChildItem -Path $Src -Recurse -File | Where-Object { $_.Extension -in '.ppt', '.doc' -and $_.Name -notlike '~$*' } | Sort-Object Extension -Descending)

$ppt = $null; $word = $null
foreach ($f in $files) {
    $rel = $f.FullName.Substring($Src.Length).TrimStart('\')
    $dest = Join-Path $Out ($rel + 'x')
    New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
    if (Test-Path $dest) { Write-Output "skip  $rel"; continue }
    if ($f.Extension -eq '.ppt') {
        if (-not $ppt) { $ppt = New-Object -ComObject PowerPoint.Application }
        $p = $ppt.Presentations.Open($f.FullName, $true, $false, $false)   # read-only, no window
        $p.SaveAs($dest, 24)                                                 # ppSaveAsOpenXMLPresentation
        $p.Close()
    } else {
        if (-not $word) { $word = New-Object -ComObject Word.Application; $word.Visible = $false; $word.DisplayAlerts = 0 }
        # no conversion prompt, read-only, not in recent files, dummy password so a protected
        # file fails instead of waiting on an invisible dialog; NoEncodingDialog
        $d = $word.Documents.Open($f.FullName, $false, $true, $false, 'x', 'x', $false, 'x', 'x', 0, [Type]::Missing, $false, $false, 0, $true)
        $d.SaveAs2($dest, 16)                                                # wdFormatDocumentDefault
        $d.Close()
    }
    Write-Output "done  $rel"
}
if ($ppt) { $ppt.Quit() }
if ($word) { $word.Quit() }
