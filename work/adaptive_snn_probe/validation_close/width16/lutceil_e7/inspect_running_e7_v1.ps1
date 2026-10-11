param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9]+$')][string]$Index)
$ErrorActionPreference = 'Stop'
$taskE7Folder = Join-Path $PSScriptRoot 'hardware/replay12_glif_e7_profiled_all_a0_e7'
$taskE7Output = Join-Path $PSScriptRoot 'runtime_inspection_a0'
$taskE7Target = Join-Path $taskE7Output ('snapshot_' + $Index + '.json')
if (Test-Path -LiteralPath $taskE7Target) { throw 'Retain all snapshots; select a new index.' }
$taskE7Processes = Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -in @(30100,28692) } | Select-Object ProcessId,ParentProcessId,Name,KernelModeTime,UserModeTime,WorkingSetSize,CreationDate,CommandLine
$taskE7Files = @('tool_3.log','activity.saif','sim.wdb','xsim.log','xsim.jou','activity.tcl','provenance.json') | ForEach-Object {
  $taskE7Item = Get-Item -LiteralPath (Join-Path $taskE7Folder $_)
  $taskE7Hash = $null
  $taskE7HashStatus = 'active_file_metadata_only_no_content_hash'
  if ($_ -in @('activity.tcl','provenance.json')) {
    $taskE7Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $taskE7Item.FullName).Hash.ToLowerInvariant()
    $taskE7HashStatus = 'saved_source_content_hashed'
  }
  [PSCustomObject]@{path=$taskE7Item.FullName;length=$taskE7Item.Length;last_write_utc=$taskE7Item.LastWriteTimeUtc.ToString('o');sha256=$taskE7Hash;hash_status=$taskE7HashStatus}
}
$taskE7Record = [PSCustomObject]@{
  time_utc=[DateTime]::UtcNow.ToString('o')
  processes=$taskE7Processes
  files=$taskE7Files
  job_receipt_present=(Test-Path -LiteralPath (Join-Path $taskE7Folder 'tool_3.job.json'))
  last_log_lines=(Get-Content -LiteralPath (Join-Path $taskE7Folder 'tool_3.log') -Tail 8)
  read_only_running_job=$true
  process_control_performed=$false
  notes='Process counters indicate activity, not simulated-time advancement. Active file metadata is sampled; buffered/locked contents are not a completion record.'
}
$taskE7Record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $taskE7Target
$taskE7Record | ConvertTo-Json -Depth 8
