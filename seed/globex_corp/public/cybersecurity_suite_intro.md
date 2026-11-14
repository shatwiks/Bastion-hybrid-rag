# Globex Enterprise Threat Defense Suite Overview

Globex Enterprise Threat Defense delivers zero-trust network visibility, agentless workload scanning, and automated compliance reporting for regulated hybrid-cloud organizations.

## Core Security Capabilities

Globex protects perimeter and east-west service traffic through three integrated security modules:

1. **Inline Intrusion Prevention (IPS):** Performs wire-speed TLS 1.3 inspection and signature-free anomaly scoring across branch and cloud gateways.
2. **Agentless Workload Posture Scanning:** Captures ephemeral VM and container filesystem snapshots out-of-band to detect CVEs, exposed secrets, and drift without runtime CPU overhead.
3. **Continuous Compliance Engine:** Maps live firewall telemetry directly to SOC 2 Type II, ISO 27001, and PCI-DSS 4.0 control matrices.

## Deployment Modes & Compliance Matrix

| Deployment Profile | Inspection Mode | Supported Environments | Compliance Attestations |
| --- | --- | --- | --- |
| `Globex-Cloud-Guard` | Agentless API + VPC Mirroring | AWS, GCP, Azure | SOC 2 Type II, ISO 27001 |
| `Globex-Perimeter-IPS` | Inline Wire-Speed Gateways | On-Premise & Colocation | PCI-DSS 4.0, HIPAA |
| `Globex-Hybrid-Mesh` | Unified Control Plane | Multi-Cloud + Edge | FedRAMP Moderate Ready |

### Agentless Posture Scan Trigger Example

Trigger an on-demand compliance posture assessment using the public Globex REST API:

```bash
curl -X POST "https://api.globex-security.example.com/v1/posture/scans" \
  -H "Authorization: Bearer ${GLOBEX_PUBLIC_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"scope": "production-vpc", "framework": "SOC2_TYPE_II"}'
```

```json
{
  "scan_id": "scan-glx-8812",
  "status": "queued",
  "estimated_duration_sec": 45
}
```
