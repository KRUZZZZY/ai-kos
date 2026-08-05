---
id: bbb3b0aa-2a14-4797-bb3d-5b8bc0bf247f
title: 'Tailscale vs Headscale: Zero-Trust Mesh VPN Comparison'
slug: tailscale-vs-headscale
type: base
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.8
keywords:
- tailscale
- headscale
- wireguard
- vpn
- zero-trust
- mesh
- aws
- infrastructure
summary: Comparative evaluation of Tailscale SaaS vs self-hosted Headscale for zero-trust
  mesh VPN. Covers SSM-IN hardening, WireGuard peer-to-peer, policy engines, OIDC,
  SSH recording, and high availability.
related:
- harden-aws-ssm-jump-host
provenance:
- inbox/Tailscale vs Headscale Evaluation.md
retrieval_count: 0
gap: false
tags:
- type/base
---

Tailscale and Headscale both implement zero-trust peer-to-peer mesh VPNs on top of WireGuard. The coordination server acts exclusively as a control plane — handling node registration, key distribution, DNS policies, ACL compilation, and NAT traversal. Actual traffic flows directly peer-to-peer, encrypted by WireGuard. Tailscale is a managed SaaS platform with built-in high availability, device posture validation, SSH session recording (tsrecorder → S3), MagicDNS, Funnel ingress, and native OIDC group mappings. Headscale is the self-hosted alternative — identical data plane performance but requires manual engineering for HA (Keepalived VIP, LiteFS+Consul SQLite replication, or PostgreSQL clustering). Headscale lacks posture validation, IP sets support, and has experimental-only Tailscale SSH with incomplete policy integration. Session recording is unsupported. Recommendation: Tailscale SaaS for most organizations; Headscale only when compliance prohibits third-party SaaS. The existing SSM-IN jump host (t2.micro, 1GB RAM) was diagnosed with OOM-killer terminating the SSM agent due to memory exhaustion from stale SSH tunnels. Fix: upgrade to t3a.small, add swap, configure ClientAliveInterval, deploy CloudWatch agent for memory monitoring.

## Related
[[harden-aws-ssm-jump-host]]
