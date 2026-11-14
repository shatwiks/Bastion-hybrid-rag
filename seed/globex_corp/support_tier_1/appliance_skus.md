# Globex Security Appliance Hardware Catalog & SKUs

This Tier-1 support hardware specification covers Globex physical security appliances, throughput ratings, power budgets, and network interface allocations.

## Hardware Appliance SKU Matrix

| SKU Identifier | Appliance Model | Deployment Role | Inspected TLS Throughput | Concurrent Sessions | Support Tier |
| --- | --- | --- | --- | --- | --- |
| `SKU-GLX-500` | Carrier-Grade Threat Gate | Core Data Center & Perimeter IPS | 200 Gbps | 40,000,000 | `support_tier_1` |
| `SKU-GLX-100` | Edge Sensor | Branch Office & Remote POP Sensor | 10 Gbps | 1,500,000 | `support_tier_1` |
| `SKU-GLX-900` | Sovereign Crypto Accelerator | Dedicated HSM Offload Module | 400 Gbps (AES-GCM) | N/A | `support_tier_1` |

## `SKU-GLX-500` Carrier-Grade Threat Gate Specifications

The `SKU-GLX-500` is a `2U` dual-socket appliance engineered for carrier-grade inline packet inspection with hardware bypass relays.

| Component | Specification | Notes |
| --- | --- | --- |
| Network Interfaces | `8 x 100GbE` QSFP28 + `4 x 25GbE` SFP28 | Optical hardware fail-open bypass on ports 1-4 |
| Management Interface | `1 x 1GbE` RJ45 Out-of-Band + Serial Console | Dedicated isolated management VRF |
| Power Supply | Dual `1,200W` Platinum AC/DC Hot-Swap (`100-240V`) | Typical load: 780W under 150 Gbps inspection |
| Dimensions & Weight | `2U` (`88 x 438 x 720 mm`), `21.4 kg` | Requires 4-post sliding rail kit |

## `SKU-GLX-100` Edge Sensor Specifications

The `SKU-GLX-100` provides compact `1U` branch inspection and zero-touch SD-WAN telemetry forwarding.

| Component | Specification | Notes |
| --- | --- | --- |
| Network Interfaces | `4 x 10GbE` SFP+ + `4 x 1GbE` RJ45 | Supports passive TAP or inline bridge mode |
| Power Supply | Single `250W` Internal AC + External DC Failover | Typical load: 95W |
| Cooling | Front-to-Back Variable PWM (`38 dBA` nominal) | Office-closet acoustic compliant |

### Appliance Provisioning CLI Example

```bash
glx-appliance-init provision \
  --sku SKU-GLX-500 \
  --bypass-mode fail-open \
  --enable-read-replica
```
