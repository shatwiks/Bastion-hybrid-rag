# Globex Firewall Operations Manual & Error Codes

This Tier-1 support operations guide documents firewall policy priority evaluation, egress certificate revocation handling, and CLI flags for Globex Threat Defense appliances.

## Firewall Error Code Catalog

| Error Code | Severity | Subsystem | Description | Resolution Action |
| --- | --- | --- | --- | --- |
| `ERR_401_SEC_REVOKED` | Critical | mTLS Egress Validator | Invalid or revoked egress client certificate detected during policy handshake | Rotate gateway certificate bundle and verify OCSP responder reachability |
| `ERR_403_EGRESS_DENIED` | High | Strict Egress Filter | Outbound packet matched default-deny egress rule when `--strict-egress-filtering` is active | Audit destination ASN/CIDR allowlist in policy tier 200 |
| `ERR_502_REPLICA_DESYNC` | Medium | Policy State Sync | Read replica policy table lagged behind primary controller by >5 seconds | Restart policy sync daemon with `--enable-read-replica` flag |

## Rule Evaluation Priority Order

Globex firewalls evaluate packets strictly in ascending numerical priority order; the first matching terminal rule halts evaluation.

| Priority Band | Rule Scope | Default Action | Override Flag |
| --- | --- | --- | --- |
| `100 - 199` | Emergency Threat Feed Blocklist | `DROP` (logged) | Immutable |
| `200 - 399` | Strict Egress TLS Certificate Validation | `REJECT` (`ERR_401_SEC_REVOKED`) | `--strict-egress-filtering` |
| `400 - 699` | Tenant Micro-Segmentation ACLs | `ALLOW` / `DENY` | Policy Controller Managed |
| `900 - 999` | Fallback Catch-All Audit Rule | `DROP` | None |

## Handling `ERR_401_SEC_REVOKED` & Read-Replica Failover

When a branch gateway reports `ERR_401_SEC_REVOKED`, its egress mTLS certificate has failed OCSP/CRL validation against the Globex root authority.

### Step 1: Verify Revocation Status & Rotate Certificate

Run the diagnostic CLI to inspect the serial number triggering `ERR_401_SEC_REVOKED` and issue a replacement certificate:

```bash
glx-fw-ctl cert verify \
  --tenant-id globex_corp \
  --error-code ERR_401_SEC_REVOKED \
  --strict-egress-filtering
```

### Step 2: Enable Read-Replica Policy Fallback

During primary policy-controller maintenance, enable local read-replica policy lookups alongside strict egress enforcement so edge gateways continue authenticating valid workloads without outage:

```bash
glx-fw-ctl daemon start \
  --enable-read-replica \
  --strict-egress-filtering \
  --replica-sync-interval 2s
```
