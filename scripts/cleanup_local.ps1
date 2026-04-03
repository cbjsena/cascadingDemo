param(
    [string]$ProjectName = "cascadingdemo_local",
    [switch]$RemoveOrphans
)

$ErrorActionPreference = "Stop"

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-PodmanObject {
    param(
        [ValidateSet("container", "pod", "network")]
        [string]$Type,
        [string]$Name
    )

    switch ($Type) {
        "container" { & podman container exists $Name *> $null }
        "pod" { & podman pod exists $Name *> $null }
        "network" { & podman network exists $Name *> $null }
    }

    return ($LASTEXITCODE -eq 0)
}

function Remove-PodmanObject {
    param(
        [ValidateSet("container", "pod", "network")]
        [string]$Type,
        [string]$Name
    )

    if (-not (Test-PodmanObject -Type $Type -Name $Name)) {
        Write-Host "[SKIP] $Type '$Name' not found"
        return
    }

    switch ($Type) {
        "container" {
            Write-Host "[DEL ] container '$Name'"
            & podman rm -f $Name | Out-Host
        }
        "pod" {
            Write-Host "[DEL ] pod '$Name'"
            & podman pod rm -f $Name | Out-Host
        }
        "network" {
            Write-Host "[DEL ] network '$Name'"
            & podman network rm -f $Name | Out-Host
        }
    }
}

if (-not (Test-Command podman)) {
    Write-Error "podman command not found. Check Podman installation and PATH."
    exit 1
}

$containers = @(
    "${ProjectName}_worker_1",
    "${ProjectName}_web_1",
    "${ProjectName}_redis_1",
    "${ProjectName}_db_1"
)
$podName = "pod_${ProjectName}"
$networkName = "${ProjectName}_default"

Write-Host "[INFO] Cleanup target project: $ProjectName"
Write-Host ""

foreach ($name in $containers) {
    Remove-PodmanObject -Type container -Name $name
}

Remove-PodmanObject -Type pod -Name $podName
Remove-PodmanObject -Type network -Name $networkName

if ($RemoveOrphans) {
    Write-Host ""
    Write-Host "[INFO] Remove orphan containers with prefix '$ProjectName'"

    $orphans = (& podman ps -a --format "{{.Names}}") |
        Where-Object { $_ -like "${ProjectName}*" }

    foreach ($orphan in $orphans) {
        Remove-PodmanObject -Type container -Name $orphan
    }
}

Write-Host ""
Write-Host "[DONE] Local cleanup finished"

