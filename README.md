# Safe GitHub Achievement Unlocker

A bounded Python CLI for inspecting GitHub profile achievements and performing small,
controlled experiments in exactly one repository:
`pyanexya/github-achievement-lab`.

It does **not** promise to unlock every GitHub achievement. Several achievements require
real stars, an accepted Discussions answer, another person, payment, or historical
participation. The conditions are not formally documented as a stable GitHub API;
the catalog therefore records confidence and treats the public profile as the source of
truth for visible badges.

## Safety guarantees

- Hard repository allow-list: only `pyanexya/github-achievement-lab`.
- No infinite loops and no unlimited retries.
- Exact action plans and a side-effect-free `--dry-run`.
- Default maximum of 20 achievement actions per invocation.
- Deterministic branch names and recovery of open PRs after interruption.
- Temporary achievement branches are deleted after merge.
- No token is written to source, state, README, `.env`, or logs.
- No fake accounts, stars, reactions, accepted answers, or unsolicited external PRs.

## Supported achievements

| Achievement | Classification | Base condition used by the tool | Confidence |
|---|---|---:|---|
| Quickdraw | Automatable | Close one issue/PR within 5 minutes | High |
| YOLO | Automatable | Merge one PR without approving review | Medium |
| Pull Shark | Automatable | 2 merged PRs | High |
| Pair Extraordinaire | External co-author required | 1 co-authored merged PR | Medium |
| Starstruck | External requirement | 16 genuine stars on an owned repo | High |
| Galaxy Brain | External requirement | 2 accepted Discussions answers | Medium |
| Public Sponsor | Manual/payment | Publicly sponsor open-source work | High |
| Heart On Your Sleeve | Legacy/unobtainable | Test/unreleased; not currently earnable | Medium |
| Open Sourcerer | Legacy/unobtainable | Test/unreleased; not currently earnable | Medium |
| Arctic Code Vault Contributor | Legacy/unobtainable | 2020 Archive Program snapshot | High |
| Mars 2020 Contributor | Legacy/unobtainable | Historical Mars 2020 contribution | High |

Commonly reported tier thresholds:

| Achievement | Base | Bronze | Silver | Gold |
|---|---:|---:|---:|---:|
| Pull Shark | 2 | 16 | 128 | 1024 |
| Pair Extraordinaire | 1 | 10 | 24 | 48 |
| Starstruck | 16 | 128 | 512 | 4096 |
| Galaxy Brain | 2 | 8 | 16 | 32 |

GitHub does not publish these achievement rules as a versioned contract. Before a real
run, compare the visible profile with current community references such as
[gomzyakov/github-achievements](https://github.com/gomzyakov/github-achievements) and
[GitHub Community discussions](https://github.com/orgs/community/discussions/categories/profile).

## Requirements

- Python 3.11+
- `requests`
- A public repository named `pyanexya/github-achievement-lab`
- Existing GitHub CLI authentication, `GH_TOKEN`, or `GITHUB_TOKEN`

Install:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On Linux/macOS, activate with `source .venv/bin/activate`.

## Authentication and least privilege

Credential resolution order:

1. `gh auth token` from an existing GitHub CLI login;
2. `GH_TOKEN`;
3. `GITHUB_TOKEN`.

For a fine-grained PAT scoped only to `github-achievement-lab`, use:

- Metadata: Read (automatic baseline permission)
- Contents: Read and write
- Pull requests: Read and write
- Issues: Read and write

Repository creation may require a credential with broader account/repository
administration capability. To keep the normal token minimal, create the empty public
repository in GitHub first and initialize it with `README.md`, then use the four
permissions above. The CLI `init` command is provided only when the credential is
allowed to create repositories.

Never paste a token into a Python file. In PowerShell for the current process only:

```powershell
$env:GITHUB_TOKEN = "your-token"
```

## Commands

```powershell
python cli.py status
python cli.py init
python cli.py unlock all --dry-run
python cli.py unlock quickdraw
python cli.py unlock yolo
python cli.py unlock pull-shark --target base
python cli.py unlock pull-shark --count 2
python cli.py unlock pair-extraordinaire --target base
python cli.py cleanup
```

`unlock all` means only the minimal/base tier of safely automatable achievements. It
never requests Bronze/Silver/Gold and skips Pair Extraordinaire when a co-author is not
configured.

For Pair Extraordinaire, provide a real second GitHub user's commit identity:

```powershell
$env:GITHUB_COAUTHOR_NAME = "real-login"
$env:GITHUB_COAUTHOR_EMAIL = "verified-email-or-login@users.noreply.github.com"
python cli.py unlock pair-extraordinaire --target base --dry-run
```

If the user's email is private and cannot be verified through GitHub's public user API,
the CLI reports that limitation instead of pretending it verified the mapping.

## Dry-run and high-volume protection

`--dry-run` reports the exact target and expected counts for branches, commits, PRs, and
issues, without creating or changing GitHub objects.

Any plan exceeding 20 actions is rejected by default. `--allow-high-volume` exists for
an explicitly reviewed plan, but tiers requiring hundreds or thousands of PRs are not
recommended and are never selected by `unlock all`.

## Idempotency and cleanup

Branches follow `achievement/<name>/<sequence>`. Before creating anything, the client
checks for an existing branch, progress file, or PR and resumes the operation. State is
stored locally in `.achievement-unlocker-state.json` without secrets.

`python cli.py cleanup` closes only unfinished PRs/issues carrying the tool's markers,
deletes only `achievement/` branches, and removes local state. It does not rewrite
history or touch another repository.

## Rate-limit policy

Every API response is checked. Transient 429/5xx responses, primary rate exhaustion,
and secondary rate-limit responses use bounded exponential backoff, `Retry-After`, and
`X-RateLimit-Reset`. The default is four retries; failures then stop with the HTTP status
and a redacted response excerpt.

## Validation

```powershell
python -m compileall -q .
python -m unittest discover -s tests -v
python cli.py unlock all --dry-run
```

## License

MIT. See [LICENSE](LICENSE).

