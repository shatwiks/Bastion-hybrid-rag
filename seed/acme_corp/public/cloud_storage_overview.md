# Acme Cloud Storage Architecture & Public Overview

Acme Cloud Storage is a globally distributed, strongly consistent object and block storage platform designed for enterprise workloads requiring high durability, multi-region replication, and deterministic API semantics.

## Core Architecture

Acme Cloud Storage separates metadata consensus from bulk block persistence across three independent control and data planes:

1. **Edge Ingress Gateway:** Terminates TLS 1.3 connections, validates OAuth 2.0 / JWT bearer tokens, and routes requests to the nearest regional cell.
2. **Metadata Raft Cluster:** Maintains linearizable namespace locks, object version vectors, and bucket ACL policies across three availability zones.
3. **Erasure-Coded Block Store:** Persists 64 MiB immutable stripes using Reed-Solomon (10+4) parity encoding for 99.999999999% (11 nines) annual durability.

## SLA Tiers and Regional Availability

Acme Cloud Storage provides three commercially backed service tiers across North America, Europe, and Asia-Pacific regions.

| SLA Tier | Monthly Uptime SLA | Target P99 Read Latency | Durability | Supported Regions |
| --- | --- | --- | --- | --- |
| `Standard-HA` | 99.99% | 45 ms | 11 nines | `us-east-1`, `us-west-2`, `eu-central-1`, `ap-northeast-1` |
| `Mission-Critical` | 99.995% | 18 ms | 11 nines (cross-region) | `us-east-1`, `eu-central-1` |
| `Cold-Archive` | 99.9% | 450 ms (first-byte) | 11 nines | All global regions |

## Public API Endpoints

All public customer integrations communicate through versioned HTTPS endpoints under `https://api.acme-storage.example.com/v2`.

| Operation | HTTP Method | Endpoint Path | Rate Limit |
| --- | --- | --- | --- |
| Upload Object | `PUT` | `/v2/buckets/{bucket}/objects/{key}` | 5,000 req/s |
| Download Object | `GET` | `/v2/buckets/{bucket}/objects/{key}` | 15,000 req/s |
| List Bucket Contents | `GET` | `/v2/buckets/{bucket}/objects` | 2,000 req/s |
| Cluster Health Probe | `GET` | `/v2/health/ready` | Unlimited |

### Quickstart Object Upload Example

Use the following `curl` request to upload a configuration manifest to a `Standard-HA` bucket:

```bash
curl -X PUT "https://api.acme-storage.example.com/v2/buckets/public-assets/objects/manifest.json" \
  -H "Authorization: Bearer ${ACME_PUBLIC_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"version": "2.4", "region": "us-east-1"}'
```

### Health Check Response Schema

```json
{
  "status": "healthy",
  "region": "us-east-1",
  "replication_lag_ms": 12
}
```
