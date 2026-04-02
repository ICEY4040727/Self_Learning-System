[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('list-issues', 'list-prs', 'get-issue', 'get-pr', 'list-issue-comments', 'comment-issue', 'comment-pr')]
    [string]$Action,

    [string]$Repo,

    [int]$Number,

    [string]$Body,

    [ValidateSet('open', 'closed', 'all')]
    [string]$State = 'all',

    [int]$PerPage = 30,

    [int]$Page = 1
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-RepoFromGitRemote {
    try {
        $remote = (git remote get-url origin).Trim()
    } catch {
        throw 'Cannot read git remote origin. Provide -Repo explicitly, e.g. owner/name.'
    }

    if ($remote -match 'github\.com[:/](?<repo>[^/]+/[^/.]+)') {
        return $Matches.repo
    }

    throw "Cannot parse owner/repo from origin: $remote"
}

function Get-Headers {
    $headers = @{
        'Accept' = 'application/vnd.github+json'
        'User-Agent' = 'self-learning-system-github-api-script'
        'X-GitHub-Api-Version' = '2022-11-28'
    }

    $token = $env:GITHUB_TOKEN
    if (-not $token) {
        $token = $env:GH_TOKEN
    }

    if ($token) {
        $headers['Authorization'] = "Bearer $token"
    }

    return $headers
}

function Invoke-GithubApi {
    param(
        [Parameter(Mandatory = $true)][ValidateSet('GET', 'POST')][string]$Method,
        [Parameter(Mandatory = $true)][string]$Endpoint,
        [object]$Payload
    )

    $headers = Get-Headers
    $uri = "https://api.github.com$Endpoint"

    if ($Method -eq 'POST') {
        $json = $Payload | ConvertTo-Json -Depth 10
        return Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -ContentType 'application/json' -Body $json
    }

    return Invoke-RestMethod -Method Get -Uri $uri -Headers $headers
}

function Assert-GithubResponse {
    param(
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        [object]$Response,
        [Parameter(Mandatory = $true)]
        [string]$ActionName
    )

    if ($null -eq $Response) {
        throw "GitHub API returned empty response for action: $ActionName"
    }

    if ($Response -is [System.Array]) {
        return
    }

    $props = @($Response.PSObject.Properties.Name)
    if (($props -contains 'message') -and -not ($props -contains 'number' -or $props -contains 'id')) {
        throw "GitHub API error for ${ActionName}: $($Response.message)"
    }
}

if (-not $Repo) {
    $Repo = Get-RepoFromGitRemote
}

switch ($Action) {
    'list-issues' {
        $result = Invoke-GithubApi -Method GET -Endpoint "/repos/$Repo/issues?state=$State&per_page=$PerPage&page=$Page"
        Assert-GithubResponse -Response $result -ActionName $Action
        @($result) | Where-Object { $_.PSObject.Properties.Name -notcontains 'pull_request' } |
            Select-Object number, title, state, created_at, updated_at, html_url
    }

    'list-prs' {
        $result = Invoke-GithubApi -Method GET -Endpoint "/repos/$Repo/pulls?state=$State&per_page=$PerPage&page=$Page"
        Assert-GithubResponse -Response $result -ActionName $Action
        @($result) | Select-Object number, title, state, created_at, updated_at, html_url
    }

    'get-issue' {
        if (-not $Number) {
            throw 'Action get-issue requires -Number.'
        }

        $result = Invoke-GithubApi -Method GET -Endpoint "/repos/$Repo/issues/$Number"
        Assert-GithubResponse -Response $result -ActionName $Action
        $result
    }

    'get-pr' {
        if (-not $Number) {
            throw 'Action get-pr requires -Number.'
        }

        $result = Invoke-GithubApi -Method GET -Endpoint "/repos/$Repo/pulls/$Number"
        Assert-GithubResponse -Response $result -ActionName $Action
        $result
    }

    'list-issue-comments' {
        if (-not $Number) {
            throw 'Action list-issue-comments requires -Number.'
        }

        $result = Invoke-GithubApi -Method GET -Endpoint "/repos/$Repo/issues/$Number/comments?per_page=$PerPage&page=$Page"
        Assert-GithubResponse -Response $result -ActionName $Action
        @($result) | Select-Object id, @{Name = 'user'; Expression = { $_.user.login } }, created_at, updated_at, body, html_url
    }

    'comment-issue' {
        if (-not $Number) {
            throw 'Action comment-issue requires -Number.'
        }

        if (-not $Body) {
            throw 'Action comment-issue requires -Body.'
        }

        if (-not $env:GITHUB_TOKEN -and -not $env:GH_TOKEN) {
            throw 'Comment action requires GITHUB_TOKEN or GH_TOKEN in environment.'
        }
        $result = Invoke-GithubApi -Method POST -Endpoint "/repos/$Repo/issues/$Number/comments" -Payload @{ body = $Body }
        Assert-GithubResponse -Response $result -ActionName $Action
        $result | Select-Object id, html_url, created_at
    }

    'comment-pr' {
        if (-not $Number) {
            throw 'Action comment-pr requires -Number.'
        }

        if (-not $Body) {
            throw 'Action comment-pr requires -Body.'
        }

        if (-not $env:GITHUB_TOKEN -and -not $env:GH_TOKEN) {
            throw 'Comment action requires GITHUB_TOKEN or GH_TOKEN in environment.'
        }
        # PR conversation comments use the same issue-comments endpoint.
        $result = Invoke-GithubApi -Method POST -Endpoint "/repos/$Repo/issues/$Number/comments" -Payload @{ body = $Body }
        Assert-GithubResponse -Response $result -ActionName $Action
        $result | Select-Object id, html_url, created_at
    }
}
