param(
    [string]$RepoName = "homeostasisbench",
    [string]$Description = "A benchmark for stress-testing multi-agent systems under overload, failures, false signals, and resource collapse.",
    [ValidateSet("public", "private")]
    [string]$Visibility = "public",
    [string]$RemoteName = "origin",
    [switch]$SkipCommit
)

$ErrorActionPreference = "Stop"

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing required command: $Name"
    }
}

function Resolve-GitHubCli {
    $command = Get-Command gh -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $fallbacks = @(
        "C:\Program Files\GitHub CLI\gh.exe",
        "C:\Users\ASUS\AppData\Local\Microsoft\WinGet\Packages\GitHub.cli_Microsoft.Winget.Source_8wekyb3d8bbwe\gh.exe"
    )
    foreach ($candidate in $fallbacks) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    throw "Missing required command: gh"
}

Require-Command git
$gh = Resolve-GitHubCli

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$null = & $gh auth status

$gitName = git config --global --get user.name
$gitEmail = git config --global --get user.email
if (-not $gitName -or -not $gitEmail) {
    throw "Global git user.name/user.email are not configured."
}

$remoteUrl = $null
try {
    $remoteUrl = git remote get-url $RemoteName 2>$null
} catch {
    $remoteUrl = $null
}
if (-not $remoteUrl) {
    $args = @(
        "repo", "create", $RepoName,
        "--$Visibility",
        "--source", ".",
        "--remote", $RemoteName,
        "--description", $Description
    )
    & $gh @args
}

if (-not $SkipCommit) {
    git add .
    $hasChanges = git status --porcelain
    if ($hasChanges) {
        git commit -m "Initial public release for HomeostasisBench"
    }
}

git push -u $RemoteName HEAD

$topics = @(
    "multi-agent-systems",
    "ai-agents",
    "benchmark",
    "resilience",
    "fault-tolerance",
    "swarm-intelligence",
    "simulation",
    "python"
)

& $gh repo edit --add-topic ($topics -join ",")

Write-Host ""
Write-Host "Publish complete."
Write-Host "Repo:" (git remote get-url $RemoteName)
