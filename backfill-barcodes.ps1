# backfill-barcodes.ps1
# Run barcode backfill in batches until complete
#
# Usage: 
#   .\backfill-barcodes.ps1 -Token "your_jwt_token"
#   .\backfill-barcodes.ps1 -Token "your_jwt_token" -DryRun
#   .\backfill-barcodes.ps1 -Token "your_jwt_token" -BatchSize 50

param(
    [Parameter(Mandatory=$true)]
    [string]$Token,
    
    [int]$BatchSize = 100,
    
    [switch]$DryRun
)

$API_URL = "https://collectioncalc-docker.onrender.com"
$headers = @{
    "Authorization" = "Bearer $Token"
    "Content-Type" = "application/json"
}

# Get initial stats
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  CollectionCalc Barcode Backfill" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Fetching current barcode stats..." -ForegroundColor Yellow
try {
    $stats = Invoke-RestMethod -Uri "$API_URL/api/admin/barcode-stats" -Headers $headers -Method Get
    
    Write-Host "  Total sales:      $($stats.total)" -ForegroundColor White
    Write-Host "  Has R2 image:     $($stats.has_r2_image)" -ForegroundColor White
    Write-Host "  Has barcode:      $($stats.has_barcode)" -ForegroundColor Green
    Write-Host "  Needs scanning:   $($stats.needs_scan)" -ForegroundColor Yellow
    Write-Host "  Reprints found:   $($stats.reprints_detected)" -ForegroundColor Magenta
    Write-Host ""
    
    if ($stats.needs_scan -eq 0) {
        Write-Host "All images already scanned! Nothing to do." -ForegroundColor Green
        exit 0
    }
} catch {
    Write-Host "Error fetching stats: $_" -ForegroundColor Red
    exit 1
}

if ($DryRun) {
    Write-Host "*** DRY RUN MODE - No changes will be saved ***`n" -ForegroundColor Magenta
}

$totalProcessed = 0
$totalFound = 0
$totalErrors = 0
$batchNum = 0
$remaining = $stats.needs_scan

# Loop until done
while ($remaining -gt 0) {
    $batchNum++
    Write-Host "----------------------------------------" -ForegroundColor Gray
    Write-Host "Batch $batchNum (processing up to $BatchSize images)..." -ForegroundColor Cyan
    
    $body = @{
        limit = $BatchSize
        dry_run = $DryRun.IsPresent
    } | ConvertTo-Json
    
    try {
        $result = Invoke-RestMethod -Uri "$API_URL/api/admin/backfill-barcodes" `
            -Headers $headers -Method Post -Body $body
        
        $totalProcessed += $result.processed
        $totalFound += $result.barcodes_found
        $totalErrors += $result.errors
        $remaining = $result.remaining
        
        Write-Host "  Processed:  $($result.processed)" -ForegroundColor White
        Write-Host "  Found:      $($result.barcodes_found)" -ForegroundColor Green
        Write-Host "  Errors:     $($result.errors)" -ForegroundColor $(if ($result.errors -gt 0) { "Red" } else { "Gray" })
        Write-Host "  Remaining:  $remaining" -ForegroundColor Yellow
        
        # Show some examples from this batch
        if ($result.details -and $result.details.Count -gt 0) {
            Write-Host "  Examples:" -ForegroundColor Gray
            foreach ($detail in $result.details | Select-Object -First 3) {
                $reprint = if ($detail.is_reprint) { " [REPRINT]" } else { "" }
                Write-Host "    - $($detail.title) #$($detail.issue): $($detail.upc_main)$reprint" -ForegroundColor DarkGray
            }
        }
        
        # Small delay between batches to be nice to the server
        if ($remaining -gt 0) {
            Start-Sleep -Seconds 2
        }
        
    } catch {
        Write-Host "  Error in batch: $_" -ForegroundColor Red
        $totalErrors++
        
        # If we hit an error, wait a bit longer before retrying
        Write-Host "  Waiting 10 seconds before retry..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
    }
}

# Final summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  BACKFILL COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Batches run:      $batchNum" -ForegroundColor White
Write-Host "  Total processed:  $totalProcessed" -ForegroundColor White
Write-Host "  Barcodes found:   $totalFound" -ForegroundColor Green
Write-Host "  Errors:           $totalErrors" -ForegroundColor $(if ($totalErrors -gt 0) { "Red" } else { "Gray" })

$successRate = if ($totalProcessed -gt 0) { [math]::Round(($totalFound / $totalProcessed) * 100, 1) } else { 0 }
Write-Host "  Success rate:     $successRate%" -ForegroundColor $(if ($successRate -gt 50) { "Green" } else { "Yellow" })

if ($DryRun) {
    Write-Host "`n*** This was a DRY RUN - run without -DryRun to save changes ***" -ForegroundColor Magenta
}

# Get final stats
Write-Host "`nFetching final stats..." -ForegroundColor Yellow
try {
    $finalStats = Invoke-RestMethod -Uri "$API_URL/api/admin/barcode-stats" -Headers $headers -Method Get
    Write-Host "  Has barcode:      $($finalStats.has_barcode)" -ForegroundColor Green
    Write-Host "  Reprints found:   $($finalStats.reprints_detected)" -ForegroundColor Magenta
} catch {
    Write-Host "Could not fetch final stats" -ForegroundColor Gray
}

Write-Host ""
