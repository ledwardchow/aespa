$ErrorActionPreference = "Stop"

# No parameters: reads saml.b64 from the same directory as this script.
$SamlAssertionFile = Join-Path $PSScriptRoot "saml.b64"

# Edit these defaults if needed.
$DurationSeconds = 3600
$Region = if ($env:AWS_REGION) { $env:AWS_REGION } elseif ($env:AWS_DEFAULT_REGION) { $env:AWS_DEFAULT_REGION } else { "ap-southeast-2" }

if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw "AWS CLI was not found. Install AWS CLI v2, then reopen PowerShell."
}

if (-not (Test-Path $SamlAssertionFile)) {
    throw "SAML assertion file not found: $SamlAssertionFile"
}

$assertionPath = (Resolve-Path $SamlAssertionFile).Path
$samlB64 = (Get-Content $assertionPath -Raw).Trim()

Write-Host "Attempting to detect AWS role/principal ARNs from SAML assertion..."

$xmlText = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($samlB64))
[xml]$xml = $xmlText

$nodes = $xml.SelectNodes(
    "//*[local-name()='Attribute' and @Name='https://aws.amazon.com/SAML/Attributes/Role']/*[local-name()='AttributeValue']"
)

$pairs = @()

foreach ($node in $nodes) {
    $parts = "$($node.InnerText)".Split(",") | ForEach-Object { $_.Trim() }

    $role = $parts | Where-Object { $_ -match ":role/" } | Select-Object -First 1
    $principal = $parts | Where-Object { $_ -match ":saml-provider/" } | Select-Object -First 1

    if ($role -and $principal) {
        $pairs += [pscustomobject]@{
            RoleArn      = $role
            PrincipalArn = $principal
        }
    }
}

if ($pairs.Count -eq 0) {
    throw "Could not detect AWS role/principal ARNs from the SAML assertion."
}

if ($pairs.Count -gt 1) {
    Write-Host ""
    Write-Host "Multiple AWS roles found in the assertion. Using the first one:"
    for ($i = 0; $i -lt $pairs.Count; $i++) {
        Write-Host "[$i] $($pairs[$i].RoleArn)"
        Write-Host "    $($pairs[$i].PrincipalArn)"
    }
    Write-Host ""
}

$RoleArn = $pairs[0].RoleArn
$PrincipalArn = $pairs[0].PrincipalArn

Write-Host "Assuming AWS role:"
Write-Host "  RoleArn:      $RoleArn"
Write-Host "  PrincipalArn: $PrincipalArn"
Write-Host "  Duration:     $DurationSeconds seconds"
Write-Host "  Region:       $Region"
Write-Host ""

$samlArg = "file://$assertionPath"

$json = aws sts assume-role-with-saml `
    --role-arn $RoleArn `
    --principal-arn $PrincipalArn `
    --saml-assertion $samlArg `
    --duration-seconds $DurationSeconds `
    --output json

$resp = $json | ConvertFrom-Json

if (-not $resp.Credentials.AccessKeyId) {
    throw "AWS STS did not return credentials."
}

$userTarget = [EnvironmentVariableTarget]::User

[Environment]::SetEnvironmentVariable("AWS_ACCESS_KEY_ID", $resp.Credentials.AccessKeyId, $userTarget)
[Environment]::SetEnvironmentVariable("AWS_SECRET_ACCESS_KEY", $resp.Credentials.SecretAccessKey, $userTarget)
[Environment]::SetEnvironmentVariable("AWS_SESSION_TOKEN", $resp.Credentials.SessionToken, $userTarget)
[Environment]::SetEnvironmentVariable("AWS_REGION", $Region, $userTarget)
[Environment]::SetEnvironmentVariable("AWS_DEFAULT_REGION", $Region, $userTarget)
[Environment]::SetEnvironmentVariable("AWS_PROFILE", $null, $userTarget)

# Also load them into this PowerShell session so immediate tests work.
$env:AWS_ACCESS_KEY_ID     = $resp.Credentials.AccessKeyId
$env:AWS_SECRET_ACCESS_KEY = $resp.Credentials.SecretAccessKey
$env:AWS_SESSION_TOKEN     = $resp.Credentials.SessionToken
$env:AWS_REGION            = $Region
$env:AWS_DEFAULT_REGION    = $Region
Remove-Item Env:\AWS_PROFILE -ErrorAction SilentlyContinue

Write-Host "AWS credentials written to the User environment and loaded into this PowerShell session."
Write-Host "Expires: $($resp.Credentials.Expiration)"
Write-Host ""
Write-Host "New terminals and apps launched after this point will inherit the User environment values."
Write-Host "Restart Aespa if it is already running."
Write-Host ""
Write-Host "Test with:"
Write-Host "  aws sts get-caller-identity"