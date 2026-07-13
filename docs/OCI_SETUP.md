# OCI onboarding

This guide prepares one target without asking the project to create IAM, networking, keys, or any other supporting resource. Oracle's current Console, account terms, pricing, limits, quotas, and usage view remain authoritative.

## Keep the two key pairs separate

OCI API signing keys authenticate the SDK as an OCI user. The private half stays on the machine running the hunter and the public half is registered under the OCI user's API Keys. SSH keys authenticate an operator to the instance after it exists; only the SSH **public** key is supplied in launch metadata. These pairs serve different protocols and are not interchangeable.

Oracle's [Required Keys and OCIDs](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/apisigningkey.htm) and [SDK configuration](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm) pages are the authoritative signing-key references.

## Create an OCI SDK profile

In the OCI Console:

1. Open the profile menu, choose **User settings**, then **API Keys**.
2. Choose **Add API Key**. Generate/download a key pair or upload an existing PEM public key according to your organization's key-management policy.
3. Keep the signing private key outside this repository. Never paste it into an environment file, issue, log, or shell history.
4. Copy the Console's generated configuration-file preview into `~/.oci/config` (or another protected path).
5. Update `key_file` to the local signing private-key path. The selected profile must contain nonempty `user`, `fingerprint`, `key_file`, `tenancy`, and `region` entries.
6. Restrict access, for example `chmod 600 ~/.oci/config /protected/path/oci_api_key.pem`. The application safely rejects a signing key readable or writable by group/other.

`validate-config` parses the selected profile through the OCI SDK and validates the signing-key file locally. It makes no network request and does not print profile values or paths. Authentication remains an explicit `check` operation.

## Collect the target identifiers

Collect values in the same region as the profile:

- **Compartment OCID:** open **Identity & Security → Compartments**, select the approved compartment, and copy its OCID. Compartments organize resources and policy boundaries; see [Understanding Compartments](https://docs.oracle.com/en-us/iaas/Content/GSG/Concepts/compartments.htm).
- **Availability domain:** open **Compute → Instances → Create instance** and note an availability domain offered for the selected compartment/region.
- **Subnet OCID:** select an existing VCN/subnet approved for the target, then copy the subnet OCID. This project does not create or alter networking.
- **Image OCID:** select a current platform or custom image that explicitly supports Arm/Ampere A1. Image OCIDs are region-specific; use Oracle's [Compute images documentation](https://docs.oracle.com/en-us/iaas/Content/Compute/References/images.htm) and verify the architecture in the Console.
- **SSH public-key path:** point to the public half of a separate SSH key pair. The file should begin with a recognized SSH public-key type; never point to the private key.
- **Display name and project tag:** choose stable, unique values for this one logical target. Both participate in duplicate detection.
- **Boot-volume size:** leave unset to use the platform default or choose a reviewed positive size. Storage allowance and cost can limit how many instances fit.

Never publish complete OCIDs, fingerprints, config contents, addresses, or keys when requesting support.

## Plan the IAM boundary

The project never creates or changes IAM policies. An OCI administrator must design a least-privilege policy for the actual identity-domain/group, compartment hierarchy, subnet ownership, image source, and boot-volume configuration.

The principal needs only the operations required to list matching Compute instances and launch the approved instance while using the selected subnet, image, VNIC, and volume resources. Oracle documents policy syntax in [Getting Started with Policies](https://docs.oracle.com/en-us/iaas/Content/Identity/Concepts/policygetstarted.htm) and the exact Compute resource types and permissions in [Details for the Core Services](https://docs.oracle.com/en-us/iaas/Content/Identity/Reference/corepolicyreference.htm). Do not copy a broad universal policy from this repository: have an administrator derive and review the narrow statements for the tenancy.

## Store protected target configuration

The program reads its process environment; it does **not** parse `.env` files automatically. Create a file outside Git, owned by the runtime identity and mode `0600`, using placeholders rather than the examples below verbatim:

```dotenv
OCI_A1_HUNTER_OCI_CONFIG=/protected/path/oci/config
OCI_A1_HUNTER_OCI_PROFILE=DEFAULT
OCI_A1_HUNTER_COMPARTMENT_ID=<compartment-ocid>
OCI_A1_HUNTER_AVAILABILITY_DOMAIN=<availability-domain>
OCI_A1_HUNTER_SUBNET_ID=<subnet-ocid>
OCI_A1_HUNTER_IMAGE_ID=<arm-image-ocid-for-profile-region>
OCI_A1_HUNTER_SHAPE=VM.Standard.A1.Flex
OCI_A1_HUNTER_OCPUS=2
OCI_A1_HUNTER_MEMORY_GB=12
OCI_A1_HUNTER_DISPLAY_NAME=a1-target-primary
OCI_A1_HUNTER_SSH_PUBLIC_KEY=/protected/path/ssh/id_target.pub
OCI_A1_HUNTER_PROJECT_TAG=a1-target-primary
OCI_A1_HUNTER_MAX_ATTEMPTS=5
OCI_A1_HUNTER_MIN_DELAY=30
OCI_A1_HUNTER_MAX_DELAY=120
OCI_A1_HUNTER_STATE_DIR=/protected/state/a1-target-primary
OCI_A1_HUNTER_LOG_LEVEL=INFO
```

Shell sourcing executes shell syntax. Use it only for an environment file that the operator created, owns, restricted to mode `0600`, and reviewed in full; sourcing an untrusted or unreviewed file can execute arbitrary commands.

```bash
set -a
. /protected/path/hunter.env
set +a
```

## Choose a resource profile

Oracle's current [Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) page describes 1,500 OCPU-hours and 9,000 GB-hours per month as **2 OCPUs and 12 GB total** for an Always Free tenancy. A conservative layout is either one 2-OCPU/12-GB target or two separate 1-OCPU/6-GB targets. Boot/block-volume use also constrains instance count.

Other and historical Oracle material has described 4 OCPUs/24 GB. Treat 4/24 only as a historical or account-specific profile; it is not this project's current safe Always Free default and may be unavailable or chargeable. Confirm the Console's **Limits, Quotas and Usage**, the account agreement, and current pricing before proceeding. The program deliberately does not infer free eligibility.

## Configure two targets without pretending they are one

One process configuration manages one target. For two 1/6 targets, create `target-a.env` and `target-b.env`. Each must have a unique display name, project tag, environment file, and state directory, for example:

```dotenv
# target-a.env
OCI_A1_HUNTER_OCPUS=1
OCI_A1_HUNTER_MEMORY_GB=6
OCI_A1_HUNTER_DISPLAY_NAME=a1-target-a
OCI_A1_HUNTER_PROJECT_TAG=a1-target-a
OCI_A1_HUNTER_STATE_DIR=/var/lib/oci-a1-flex-hunter/target-a
```

```dotenv
# target-b.env
OCI_A1_HUNTER_OCPUS=1
OCI_A1_HUNTER_MEMORY_GB=6
OCI_A1_HUNTER_DISPLAY_NAME=a1-target-b
OCI_A1_HUNTER_PROJECT_TAG=a1-target-b
OCI_A1_HUNTER_STATE_DIR=/var/lib/oci-a1-flex-hunter/target-b
```

The systemd template examples map `%i` to these separate protected files and state paths. This is separate one-target coordination, not native multi-target orchestration.

## Validate in this order

```bash
oci-a1-flex-hunter validate-config
oci-a1-flex-hunter check
oci-a1-flex-hunter run --once
```

The first command is local-only, the second makes a read-only OCI list request, and the third is a non-network dry-run. Review all three results, current pricing, quotas, policy, placement, image, storage, and duplicate identity. Only then may an operator deliberately authorize the resource-creating command:

```bash
oci-a1-flex-hunter run --live --once
```

That final command can create a chargeable cloud resource. There is no automatic rollback or termination.
