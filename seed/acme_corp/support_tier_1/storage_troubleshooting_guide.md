# Acme Storage Tier-1 Troubleshooting Guide

This operational runbook covers internal diagnostics, lock contention resolution, and backpressure mitigation for Acme Cloud Storage support engineers (`support_tier_1` and `executive`).

## Internal Error Code Reference

Use the table below to triage storage control-plane and replication errors reported by customer clusters or internal telemetry dashboards.

| Error Code | HTTP Status | Subsystem | Root Cause | Immediate Remediation |
| --- | --- | --- | --- | --- |
| `ERR_409_CONFLICT` | `409` | Metadata Raft Lock Manager | Resource lock contention during concurrent sync or overlapping multipart commits | Inspect lease owner with `acme-storage-cli locks inspect` and retry with jittered backoff |
| `ERR_503_SERVICE_UNAVAILABLE` | `503` | Ingress Backpressure Queue | Backpressure saturation when NVMe write-ahead queues exceed 85% capacity | Enable read-only failover or throttle batch sync workers via `--max-inflight-writes=16` |
| `ERR_429_QUOTA_BURST` | `429` | Tenant Token Bucket | Tenant exceeded burst IOPS allocation | Verify tier entitlement and raise burst ceiling temporarily if approved |
| `ERR_504_RAFT_QUORUM` | `504` | Consensus Ring | Leader election timeout during cross-AZ packet loss | Check inter-AZ RTT latency and force quorum health probe |

## Resolving `ERR_409_CONFLICT` Lock Contention

`ERR_409_CONFLICT` occurs when two concurrent sync workers attempt to acquire an exclusive lease on the same namespace key prefix within the 1,500 ms Raft lease window.

### Step 1: Inspect Active Lock Leases

Run the diagnostic CLI against the affected tenant partition to identify the conflicting lease holder:

```bash
acme-storage-cli locks inspect \
  --tenant-id acme_corp \
  --bucket prod-ledger-sync \
  --error-code ERR_409_CONFLICT \
  --format json
```

### Step 2: Release Stale Leases & Retry Sync

If the lease holder heartbeat is older than 30 seconds, force-expire the stale lock token and resume the sync job with deterministic exponential backoff:

```bash
acme-storage-cli locks release \
  --lease-id lease-9921-f8a \
  --reason "ERR_409_CONFLICT stale worker recovery"

acme-storage-cli sync resume \
  --bucket prod-ledger-sync \
  --backoff-ms 250 \
  --max-retries 5
```

## Mitigating `ERR_503_SERVICE_UNAVAILABLE` Backpressure Saturation

When write-ahead logs saturate on primary storage nodes, the ingress gateway sheds load by returning `ERR_503_SERVICE_UNAVAILABLE` with a `Retry-After` header.

### Diagnostic Verification Steps

Check queue depth and node saturation metrics before shifting traffic:

```bash
acme-storage-cli cluster queue-depth \
  --region us-east-1 \
  --filter-code ERR_503_SERVICE_UNAVAILABLE \
  --threshold 0.85
```

If saturation persists for more than 120 seconds, drain the overloaded primary shard and route read traffic to healthy replicas while throttling ingest concurrency.
