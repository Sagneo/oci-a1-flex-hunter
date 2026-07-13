# Configuration

The CLI combines process environment variables with explicit CLI overrides. It does not parse `.env` files automatically. Keep the live environment file, standard OCI config, signing key, and SSH public key outside the repository with restrictive permissions.

| Environment variable | CLI option | Purpose | Default |
| --- | --- | --- | --- |
| `OCI_A1_HUNTER_OCI_CONFIG` | `--oci-config` | Standard OCI config path | standard user path |
| `OCI_A1_HUNTER_OCI_PROFILE` | `--oci-profile` | OCI profile | `DEFAULT` |
| `OCI_A1_HUNTER_COMPARTMENT_ID` | `--compartment-id` | Target compartment | required |
| `OCI_A1_HUNTER_AVAILABILITY_DOMAIN` | `--availability-domain` | Placement domain | required |
| `OCI_A1_HUNTER_SUBNET_ID` | `--subnet-id` | Existing subnet | required |
| `OCI_A1_HUNTER_IMAGE_ID` | `--image-id` | Compatible image | required |
| `OCI_A1_HUNTER_SHAPE` | `--shape` | Compute shape | `VM.Standard.A1.Flex` |
| `OCI_A1_HUNTER_OCPUS` | `--ocpus` | Positive OCPU count | `1` |
| `OCI_A1_HUNTER_MEMORY_GB` | `--memory-gb` | Positive memory amount | `6` |
| `OCI_A1_HUNTER_DISPLAY_NAME` | `--display-name` | Stable duplicate identity | required |
| `OCI_A1_HUNTER_SSH_PUBLIC_KEY` | `--ssh-public-key` | Public-key file path | required |
| `OCI_A1_HUNTER_PROJECT_TAG` | `--project-tag` | Stable duplicate tag | required |
| `OCI_A1_HUNTER_BOOT_VOLUME_SIZE_GB` | `--boot-volume-size-gb` | Optional positive size | unset |
| `OCI_A1_HUNTER_MAX_ATTEMPTS` | `--max-attempts` | Process attempt ceiling | `5` |
| `OCI_A1_HUNTER_MIN_DELAY` | `--min-delay` | Minimum jitter delay | `30` |
| `OCI_A1_HUNTER_MAX_DELAY` | `--max-delay` | Maximum jitter delay | `120` |
| `OCI_A1_HUNTER_STATE_DIR` | `--state-dir` | State and lock directory | user state directory |
| `OCI_A1_HUNTER_LOG_LEVEL` | `--log-level` | Console log level | `INFO` |

Display names and project tags accept letters, numbers, periods, underscores, and hyphens, must begin with an alphanumeric character, and have a maximum length of 63 characters.

OCPU and memory defaults are examples, not a statement of price or eligibility. Before live mode, verify the current Oracle price, quota, service limits, policy, compatible image, and approved resource profile for the account.

## A1 allocation guidance

The shape profile remains configurable because paid accounts and account-specific entitlements can differ. A historical 4-OCPU/24-GB allocation could be one 4/24 instance or several smaller instances, but the Oracle Always Free resource page reviewed on 2026-07-13 instead publishes a 2-OCPU/12-GB total and describes one 2-OCPU instance or two 1-OCPU instances. Oracle pages are not fully consistent, and block-volume usage also constrains instance count. Treat the account Console and current Oracle terms as authoritative; the application never labels a configured profile as free.

Use `oci-a1-flex-hunter validate-config` before `check`, and use `check` before any manually approved live run.
