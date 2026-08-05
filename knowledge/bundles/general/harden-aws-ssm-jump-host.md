---
id: 2415163a-4468-40a8-8101-2aa2c5c8b819
title: How to Harden an AWS SSM Jump Host
slug: harden-aws-ssm-jump-host
type: process
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.8
keywords:
- aws
- ssm
- jump-host
- hardening
- tailscale
- memory
- ai-kos
- knowledge
- articles
summary: 'Step-by-step procedure for hardening an AWS Systems Manager jump host: upgrade
  instance type, prevent OOM kills, reap stale SSH tunnels, add memory monitoring.'
related:
- ai-kos
- ai-kos-mission
- ai-kos-plan
- article-types-guide
- creation-protocol
- docling-graph-research
- durable-execution-research
- hybrid-search-research
- ingest-file
- langgraph-orchestration-research
- memsearch-claude-memory-research
- networkx-implementation-notes
- obsidian-graph-idea
- oss-consolidation-strategy
- process-articles-backup-skills
- random-graph-simulation-suite
- run-random-graph-suite
- session-end-protocol
- session-writeback
- tailscale-vs-headscale
provenance:
- inbox/Tailscale vs Headscale Evaluation.md
retrieval_count: 0
gap: false
tags:
- type/process
---

## Outcome
Jump host survives memory pressure without OOM-killing the SSM agent. Stale tunnels auto-reaped. Memory usage monitored with alerts. Instance ID preserved for external team compatibility.

## Prerequisites
- AWS CLI access
- Ability to stop/start the instance (public IP will change unless using Elastic IP)

## Steps
1. Stop the instance and upgrade from t2.micro (1GB) to t3a.small (2GB) — preserves Instance ID
2. Create systemd override: /etc/systemd/system/snap.amazon-ssm-agent.amazon-ssm-agent.service.d/override.conf with Restart=always, RestartSec=5s, OOMScoreAdjust=-900
3. Add to /etc/ssh/sshd_config: ClientAliveInterval 60, ClientAliveCountMax 3 — auto-terminates idle tunnels after 3 minutes
4. Deploy AWS CloudWatch agent to monitor OS-level RAM and swap (EC2 metrics only show hypervisor stats)
5. Configure CloudWatch alarm: mem_used_percent > 80 for 5 minutes → notify
6. Optional: remove public IP, deploy VPC Endpoints for SSM (ssm, ssmmessages, ec2messages) — ~$21/month
7. Optional: scale further to t3.medium (4GB) if 2GB is insufficient for 13+ concurrent users

## Related
[[ai-kos]] [[ai-kos-mission]] [[ai-kos-plan]] [[article-types-guide]] [[creation-protocol]] [[docling-graph-research]] [[durable-execution-research]] [[hybrid-search-research]] [[ingest-file]] [[langgraph-orchestration-research]] [[memsearch-claude-memory-research]] [[networkx-implementation-notes]] [[obsidian-graph-idea]] [[oss-consolidation-strategy]] [[process-articles-backup-skills]] [[random-graph-simulation-suite]] [[run-random-graph-suite]] [[session-end-protocol]] [[session-writeback]] [[tailscale-vs-headscale]]
