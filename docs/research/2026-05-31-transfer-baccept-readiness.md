# Transfer bAccept Candidate Readiness Guardrail

Date: 2026-05-31

## Scope

This note records the offline readiness audit for
`transfer-baccept-only-policy-slice`. The lane is candidate-only planning evidence. It
does not promote runtime hook wiring, dispatcher wiring, public Transfer SDK, public ABI,
payload decoding, identity, ownership, mutation, return override, or v1 completion.

No servers, runtime probes, protected `/servidor/ark` inputs, ptrace/gcore, Discord,
ArkApi/NextGen copying, commits, pushes, tags, or rebases were used.

## Artifact

Current artifact root:

```text
/home/flowcommunity-ark/obelisk-artifacts/transfer-baccept-only-policy-slice-20260530T073308Z
```

Current direct policy manifest:

```text
transfer-baccept-only-policy-slice.json
sha256=a2b0939189cb847b351c638141fa5e122c08ca69acadae8b5c86d894fc208f12
```

The policy slice contains exactly one copied input bool:

```text
ShooterPlayerController.ServerTransferredPlayerConfirmationResult.bAccept
```

It also keeps ten transfer-adjacent fields as forbidden evidence only: transfer return
bools, spawn/region/bed/player ids, object refs, and class refs.

## Checker

Added `scripts/check_transfer_baccept_readiness.py` as a read-only wrapper around
`scripts/validate_offline_artifact_gate.py`. The checker accepts candidate planning only
when:

- consume mode accepts the artifact;
- promote mode is blocked with `promote_mode_transfer_baccept_policy_slice_evidence_only`
  and `promote_mode_manifest_has_non_claims`;
- the manifest hash matches the reviewed artifact;
- the policy has only expected top-level and nested fields;
- non-claims include the transfer/runtime/public-SDK boundaries;
- copied evidence remains only `bAccept` at the reviewed non-native one-byte bool shape;
- transfer-adjacent fields remain forbidden and covered;
- no field or positive claim implies Transfer SDK, identity, ownership, mutation, return
  override, runtime wiring, public ABI, or v1 completion.

The checker report intentionally returns:

```text
accepted_for_internal_planning=true
consume_only=true
not_artifact_gate=true
public_transfer_sdk_ready=false
public_abi_ready=false
runtime_ready=false
identity_ready=false
ownership_ready=false
mutation_ready=false
return_override_ready=false
v1_completion_ready=false
promotion_ready=false
```

## Validation

Commands run from `/home/flowcommunity-ark/Obelisk`:

```bash
python3 -m unittest scripts/test_check_transfer_baccept_readiness.py
```

Result:

```text
Ran 4 tests in 0.249s
OK
```

```bash
python3 scripts/check_transfer_baccept_readiness.py \
  --root /home/flowcommunity-ark/obelisk-artifacts/transfer-baccept-only-policy-slice-20260530T073308Z \
  --manifest /home/flowcommunity-ark/obelisk-artifacts/transfer-baccept-only-policy-slice-20260530T073308Z/transfer-baccept-only-policy-slice.json \
  --json
```

Result:

```text
ready=true
status=candidate_ready
consume_gate.status=accepted
promote_gate.status=blocked
promote_gate.blocker_reasons=[
  promote_mode_manifest_has_non_claims,
  promote_mode_transfer_baccept_policy_slice_evidence_only
]
blockers=[]
```

## Decision

`transfer-baccept-only-policy-slice` is acceptable as consume/candidate planning evidence
only. It remains blocked for promotion and must not be used as runtime readiness, public
SDK/ABI readiness, identity/ownership evidence, mutation or return override authority, or
v1 completion proof.
