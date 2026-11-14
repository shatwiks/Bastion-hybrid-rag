# Acme Storage Hardware Inventory & SKU Specifications

This internal hardware catalog documents approved storage chassis, drive shelves, thermal envelopes, and rack power layouts managed by Acme Tier-1 infrastructure support.

## Approved Storage Hardware SKUs

| SKU Identifier | Product Name | Form Factor | Raw Capacity | Max Sequential Throughput | Support Tier |
| --- | --- | --- | --- | --- | --- |
| `SKU-9921-A` | High-Throughput NVMe JBOF Array | `2U` Rackmount | 368.6 TB (`24 x 15.36 TB` PCIe Gen5 NVMe) | 110 GB/s | `support_tier_1` |
| `SKU-7740-B` | High-Density Archive Shelf | `4U` Top-Loading | 1.44 PB (`60 x 24 TB` SAS-4 Helium HDD) | 14.5 GB/s | `support_tier_1` |
| `SKU-4410-C` | Dual-Port RoCEv2 TOR Switch | `1U` Switch | N/A (`32 x 400GbE` QSFP-DD) | 25.6 Tbps fabric | `support_tier_1` |

## `SKU-9921-A` Thermal & Power Specifications

The `SKU-9921-A` High-Throughput NVMe JBOF Array requires front-to-back cold-aisle airflow and dual redundant PDUs to maintain Gen5 NVMe controller temperatures below throttling thresholds.

| Metric | Nominal Operating Spec | Warning Threshold | Critical Shutdown |
| --- | --- | --- | --- |
| Inlet Air Temperature | 18 C - 24 C | 29 C | 35 C |
| Power Draw (Dual PSU) | 1,180 W (`208V AC`) | 1,420 W | 1,600 W |
| NVMe Controller Junction | 54 C | 72 C | 80 C |
| Fan Tray Redundancy | `N+1` Hot-Swap (`6 x 80mm`) | 1 Fan Fault | 2+ Fan Faults |

## Standard Rack Layout (`42U` Storage Pod)

| Rack Unit Range | Hardware SKU | Role | Network Uplink |
| --- | --- | --- | --- |
| `U41 - U42` | `SKU-4410-C` | Primary & Secondary 400GbE TOR Switches | `8 x 400G` Spine |
| `U33 - U40` | `SKU-9921-A` (`x4`) | Tier-0 Hot NVMe JBOF Pool | `2 x 200GbE` per chassis |
| `U05 - U28` | `SKU-7740-B` (`x6`) | Tier-2 Erasure-Coded Archive Shelves | `2 x 100GbE` per shelf |
| `U01 - U04` | `PDU-30A-3P` | Redundant A/B Rack Power Distribution | Out-of-Band IPMI |

### Hardware Telemetry Verification Command

Query BMC sensor health and confirm SKU firmware baselines on newly racked `SKU-9921-A` or `SKU-7740-B` units:

```bash
acme-hw-ctl inventory verify \
  --sku SKU-9921-A \
  --check-thermals \
  --firmware-baseline v4.12.0
```
