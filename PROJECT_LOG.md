# OCI A1 Flex Hunter — Project Log

## 2026-07-13T13:40:00-07:00 — Phase 01

- **Objective:** [VERIFIED] Read both controlling Markdown documents completely before acting.
- **Action:** [VERIFIED] Read the 2,434-line blueprint and 313-line Phase 01 start task in bounded chunks.
- **Result:** [VERIFIED] Phase 01 scope, safety constraints, output files, and validation gate were established.
- **Validation evidence:** [VERIFIED] Line counts and complete bounded reads reached the final line of both documents.
- **Unresolved issue:** [UNRESOLVED] Live-system availability had not yet been tested.
- **Rollback state:** [VERIFIED] No filesystem or service change had occurred.
- **Next bounded step:** [VERIFIED] Run workspace preflight only.

## 2026-07-13T13:45:00-07:00 — Phase 01

- **Objective:** [VERIFIED] Validate the Sagneo workspace boundary.
- **Action:** [VERIFIED] Inspected current identity, current directory, umbrella-directory metadata, immediate child names, Git-work-tree status, target existence, and disk capacity.
- **Result:** [VERIFIED] The umbrella path existed, was not in a Git work tree, had safe ownership, and the target was absent. No sibling content was inspected.
- **Validation evidence:** [VERIFIED] Workspace mode was `0700`; approximately 32 GiB was available.
- **Unresolved issue:** [UNRESOLVED] None for workspace creation.
- **Rollback state:** [VERIFIED] No change had yet occurred.
- **Next bounded step:** [VERIFIED] Create the independent non-Git project directory and install the exact blueprint.

## 2026-07-13T13:46:00-07:00 — Phase 01

- **Objective:** [VERIFIED] Create the authorized project workspace.
- **Action:** [VERIFIED] Created `/home/ubuntu/projects/sagneo/oci-a1-flex-hunter`, copied the authoritative blueprint byte-for-byte, and applied restrictive modes.
- **Result:** [VERIFIED] Directory mode is `0750`; blueprint mode is `0640`.
- **Validation evidence:** [VERIFIED] Source and destination SHA-256 both equal `512d5eb31b76cd916c2765e352db69745d8a4688d50200d61b357458ba76520b`.
- **Unresolved issue:** [UNRESOLVED] Live-system state still required inspection.
- **Rollback state:** [VERIFIED] Removing the new project directory would revert this workspace-only change.
- **Next bounded step:** [VERIFIED] Record the service baseline before source inspection.

## 2026-07-13T13:46:49-07:00 — Phase 01

- **Objective:** [VERIFIED] Record pre-inspection live-service state.
- **Action:** [VERIFIED] Queried systemd active, enabled, PID, identity, command, working-directory, restart, fragment, drop-in, type, and start-limit properties; recorded a hash of the host boot identity.
- **Result:** [VERIFIED] The service was `inactive` and `not-found`, with PID `0`, no unit path, and no executable command.
- **Validation evidence:** [VERIFIED] Direct `systemctl` property queries returned no loaded unit metadata.
- **Unresolved issue:** [UNRESOLVED] The intended live service may be on a different or unavailable host/filesystem.
- **Rollback state:** [VERIFIED] All service queries were read-only; no state-changing systemctl verb was used.
- **Next bounded step:** [VERIFIED] Test read access and search only for relevant legacy paths, units, and processes.

## 2026-07-13T13:48:00-07:00 — Phase 01

- **Objective:** [VERIFIED] Determine whether the service or source existed outside the expected loaded-unit state.
- **Action:** [VERIFIED] Confirmed passwordless read access, checked `/root/oci-hunter`, searched standard systemd unit paths, searched the root filesystem by relevant names without crossing filesystems, and checked the process table without retaining arguments.
- **Result:** [VERIFIED] The legacy path, unit, drop-ins, and matching process were absent. Only supplied task documents and the new project workspace matched the project names.
- **Validation evidence:** [VERIFIED] Exact-path tests and filesystem metadata search returned no live artifact.
- **Unresolved issue:** [UNRESOLVED] Complete source, unit, process, and Git inventory is impossible without the actual legacy installation.
- **Rollback state:** [VERIFIED] Searches were read-only and did not follow symlinks outside the intended filesystem.
- **Next bounded step:** [VERIFIED] Collect safe host/runtime facts and bounded journal metadata.

## 2026-07-13T13:49:00-07:00 — Phase 01

- **Objective:** [VERIFIED] Capture remaining safe host and runtime evidence.
- **Action:** [VERIFIED] Queried OS, kernel, architecture, system Python, OCI SDK presence, time synchronization, and a 30-day bounded journal count without retaining message fields.
- **Result:** [VERIFIED] Host is Ubuntu 24.04.4 LTS on `x86_64`; system Python is 3.12.3; OCI SDK is absent from system Python; NTP is synchronized; the requested unit has zero bounded journal entries.
- **Validation evidence:** [VERIFIED] Read-only OS, Python metadata, time-service, and journal metadata queries completed.
- **Unresolved issue:** [UNRESOLVED] The live virtual environment, dependencies, behavior, logs, and sensitive-location metadata remain unavailable.
- **Rollback state:** [VERIFIED] No runtime, package, or service state was changed.
- **Next bounded step:** [VERIFIED] Write sanitized Phase 01 documents and run the consolidated validation.

## 2026-07-13T13:52:00-07:00 — Phase 01

- **Objective:** [VERIFIED] Run the consolidated Phase 01 validation and close the phase without entering Phase 02.
- **Action:** [VERIFIED] Rechecked service state and PID, project file set and modes, Git boundaries, blueprint hash, legacy-path absence, sibling metadata, factual-classification labels, and prohibited sensitive patterns.
- **Result:** [VERIFIED] Workspace-output validation passed; service remained `inactive` and `not-found` with PID `0`; exactly three authorized files exist; Git is absent at both required boundaries; all configured sensitive-pattern checks were clear. The live-inventory completion criterion failed because the required live installation is absent.
- **Validation evidence:** [VERIFIED] Blueprint hashes match; document modes are `0600`; blueprint mode is `0640`; project directory mode is `0750`; `/root/oci-hunter` remained absent.
- **Unresolved issue:** [UNRESOLVED] The actual legacy host or filesystem is required to complete the evidence freeze.
- **Rollback state:** [VERIFIED] No service, package, cloud, Git, live path, or sibling state was changed.
- **Next bounded step:** [UNRESOLVED] Provide Codex access to the actual legacy host or its read-only mounted filesystem, then rerun Phase 01. Do not begin Phase 02.

## 2026-07-13T14:10:00-07:00 — Greenfield rebaseline

- **Objective:** Replace the disproven brownfield premise with the authoritative greenfield product contract.
- **Action:** Read the build-and-publish contract completely, verified project and Git boundaries, confirmed planning-file readability, and reclassified the blueprint and current state as greenfield.
- **Result:** Legacy migration is no longer a project dependency. The earlier Phase 01 entries remain preserved as historical context.
- **Validation evidence:** The project path exists, the umbrella path is non-Git, the project had no Git repository or unrelated remote, and GitHub CLI authentication is available for the Sagneo account.
- **Unresolved issue:** Implementation and publication validation remain pending.
- **Rollback state:** Changes are confined to this project directory.
- **Next bounded step:** Implement the package, tests, documentation, and CI.

## 2026-07-13T14:20:00-07:00 — Greenfield implementation

- **Objective:** Build the version 0.1.0 safe OCI A1 Flex hunter product.
- **Action:** Added the Python package, official OCI SDK adapter boundary, CLI, validated configuration, bounded controller, duplicate matching, process lock, atomic state, redacted logging, deterministic fakes, offline tests, CI, systemd example, and user/operations documentation.
- **Result:** The CLI provides `validate-config`, `check`, `run`, and `status`; dry-run is the default and OCI creation is gated by `run --live`.
- **Validation evidence:** No live mode or OCI tenancy operation was invoked during implementation.
- **Unresolved issue:** Final security audit, Git history, and publication remained pending.
- **Rollback state:** All changes remained inside the project directory.
- **Next bounded step:** Run the complete local validation and publication audit.

## 2026-07-13T14:30:00-07:00 — Resource-limit review

- **Objective:** Reconcile historical 4-OCPU/24-GB expectations with current public Oracle guidance.
- **Action:** Reviewed official Oracle Free Tier and Always Free resource pages and documented their conflicting 4/24 and 2/12 statements.
- **Result:** The repository uses conservative 1-OCPU/6-GB examples, records 2/12 as the current specific Always Free page's published total, keeps 4/24 configurable for paid or account-specific use, and labels neither profile automatically free.
- **Validation evidence:** Configuration tests cover both 2/12 and 4/24 as syntactically valid, account-dependent profiles.
- **Unresolved issue:** The user's OCI Console, account agreement, current quotas, and pricing remain authoritative and were not accessed.
- **Rollback state:** Documentation and tests only; no OCI action occurred.
- **Next bounded step:** Complete offline validation.

## 2026-07-13T14:40:00-07:00 — Local validation

- **Objective:** Prove the package installs and all required offline checks pass.
- **Action:** Created a project-local virtual environment, installed runtime and development dependencies, compiled source/tests, formatted and linted with Ruff, type-checked with mypy, ran pytest with coverage, installed editable packaging, and ran all CLI help smoke tests.
- **Result:** 46 tests passed with 84% total coverage; Ruff formatting/linting and mypy passed; editable installation and every required CLI help command passed.
- **Validation evidence:** OCI SDK 2.181.1 was installed only as a project dependency; tests used deterministic fakes and no credentials.
- **Unresolved issue:** Pre-commit sensitive-data and artifact audit remained pending.
- **Rollback state:** Generated virtual-environment and cache files are project-local and ignored.
- **Next bounded step:** Run the complete secret and publication audit before Git initialization.

## 2026-07-13T14:45:00-07:00 — Pre-commit publication audit

- **Objective:** Ensure only sanitized, reproducible project files can enter Git.
- **Action:** Enumerated every intended file, checked symlinks and sensitive filenames, reviewed `.env.example` and `.gitignore`, scanned content for private-key headers, complete OCI identifiers, addresses, fingerprints, common credential formats, and token formats, and rechecked workspace boundaries.
- **Result:** Forty-one source, test, documentation, example, and workflow files are intended for tracking. No unexpected symlink, sensitive filename, credential pattern, complete cloud identifier, address, key header, fingerprint, token, state, log, cache, environment, virtual-environment, or build artifact was found in the intended set.
- **Validation evidence:** No dedicated local secret scanner was installed; bounded filename and PCRE2 content scans completed with zero matches. The project-local virtual environment and caches are ignored.
- **Unresolved issue:** Regex scanning cannot prove absence of every possible secret format; manual review of examples and configuration names remains part of the release audit.
- **Rollback state:** Git was still uninitialized and all work remained project-local.
- **Next bounded step:** Rerun final local validation, initialize Git on `main`, and create focused commits.

## 2026-07-13T14:50:00-07:00 — Repository initialization

- **Objective:** Create an independent, reviewable Git history only inside the project.
- **Action:** Initialized Git on `main`, confirmed the complete 41-file intended set, configured the authenticated Sagneo no-reply commit identity locally, staged explicit scopes, and created focused planning, implementation, test, documentation, and CI commits.
- **Result:** The local repository has five focused commits and a clean working tree; the umbrella workspace remains non-Git.
- **Validation evidence:** Commit subjects are recorded by Git history and ignored project-local artifacts were not staged.
- **Unresolved issue:** Remote name availability, organization permission, Actions, tag, and release remained pending.
- **Rollback state:** No remote existed and all Git metadata was confined to this project.
- **Next bounded step:** Commit this log entry, verify remote availability, and publish only to `Sagneo/oci-a1-flex-hunter`.

## 2026-07-13T15:00:00-07:00 — Initial publication and CI review

- **Objective:** Publish `main` to the exact approved public owner/name and inspect initial CI.
- **Action:** Verified the authenticated owner, confirmed the repository name was unused, created the public repository, set `origin`, pushed `main`, confirmed the default branch, and watched both CI matrix jobs.
- **Result:** Initial CI passed on Python 3.11 and 3.12. GitHub emitted Node runtime deprecation annotations for the older workflow action majors.
- **Validation evidence:** Every install, compile, format, lint, type, test, and CLI smoke step passed in both jobs.
- **Unresolved issue:** The workflow annotations should be removed before the release tag.
- **Rollback state:** The remote exists only at the approved public Sagneo URL; no alternative owner or cloud resource was used.
- **Next bounded step:** Update to the current official checkout and setup-python majors, rerun CI, then record publication and tag the passing commit.

## 2026-07-13T15:10:00-07:00 — Release-candidate validation

- **Objective:** Remove platform warnings and establish the release candidate on supported workflow runtimes.
- **Action:** Verified current official action releases, updated checkout and setup-python majors, reran local Ruff, mypy, and 46 tests, pushed the correction, and watched the complete remote matrix.
- **Result:** GitHub Actions passed on Python 3.11 and 3.12 with all required steps and without the prior Node runtime annotations.
- **Validation evidence:** Remote Actions run `29285901406` completed successfully for both matrix jobs.
- **Unresolved issue:** Annotated tag and GitHub release remained pending.
- **Rollback state:** `main` remained the only branch and the remote owner/name remained exact.
- **Next bounded step:** Commit this release-candidate record, require final `main` CI, then create and verify `v0.1.0`.

## 2026-07-13T15:20:00-07:00 — v0.1.0 publication

- **Objective:** Publish and verify the first greenfield release.
- **Action:** Required final `main` CI success, created annotated tag `v0.1.0`, pushed the tag, created the GitHub release, and watched the tag-triggered matrix.
- **Result:** The public release exists at the approved Sagneo repository and tag CI passed on Python 3.11 and 3.12.
- **Validation evidence:** Final pre-tag `main` run `29285998606` and tag run `29286063723` completed successfully for every required job.
- **Unresolved issue:** Dedicated secret-scanner tooling was unavailable; bounded regex, filename, working-tree, and history audits are the documented fallback.
- **Rollback state:** The immutable release identifies the locally validated release-candidate commit; no OCI or host deployment action occurred.
- **Next bounded step:** Push this chronological publication record, require final `main` CI, and complete remote/source/history verification.
