# Security Policy

## Supported Versions

Security fixes are provided for the latest released `0.x` version until a stable
`1.0` policy is published.

## Reporting a Vulnerability

Do not open public issues for vulnerabilities or leaked credentials. Email
`security@hzprotocol.com` with:

- affected version or commit
- reproduction steps
- expected impact
- whether any secrets were exposed

## Secret Handling

`predxt` examples use environment variables for credentials. Do not hard-code
Kalshi private keys, Opinion API keys, signatures, or account identifiers in
tests, examples, issues, or pull requests.
