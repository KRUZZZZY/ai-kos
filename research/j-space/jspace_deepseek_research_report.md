# J-Space & the "Better with DeepSeek" Claim — Independent Research Report

**Agent:** Independent research agent #3 of 3 (isolated context)
**Date of research:** August 18, 2026
**Claim evaluated:** *"J-space operates far far better with deepseek than any other harness."*
**Method:** Primary sources first (Anthropic, arXiv, GitHub repos, DeepSeek official), then independent secondary/community sources. All URLs verified by direct fetch unless noted. Grade scale: VERIFIED / CORROBORATED / UNVERIFIED / DISPROVEN.

---

## 1. What "J-space" is — disambiguation

The term refers to **two distinct, name-overlapping things**. They are NOT the same project, and the overlap is a branding coincidence (flagged by both explainx.ai and the suite's own README).

### (a) J-space — Anthropic interpretability concept (the real, peer-reviewable science)
- **What:** A small, sparse subspace of an LLM's internal activations that holds "verbalizable" concepts the model is *poised to say* — an internal workspace where reasoning is staged before (or instead of) being written down. Named for the **Jacobian lens (J-lens)**, the technique used to find it (per-token average linearized effect of activations on future token probabilities).
- **Where published:** Anthropic, July 6, 2026: blog "A global workspace in language models" (anthropic.com/research/global-workspace) + paper *"Verbalizable Representations Form a Global Workspace in Language Models"* (Gurnee, Sofroniew, et al., 16 authors), arXiv:2607.15495, published on Transformer Circuits Thread (transformer-circuits.pub/2026/workspace).
- **Subject of study:** **Claude models.** The paper's findings are about Claude. It argues the workspace is emergent and likely general across models, but the *evidence* is Claude-specific.
- **Companion code:** github.com/anthropics/jacobian-lens — open-source reference implementation ("Not maintained and not accepting contributions").
- **jspace.com:** a third-party WordPress *explainer* site about this research ("Research explainers on AI interpretability, J-Space, and the Jacobian Lens"). **It is NOT an Anthropic-owned or -affiliated site**, and it covers the interpretability concept, not the Cognition Suite.

### (b) J-Space Cognition Suite — community harness/skill (the hype object)
- **What:** An open-source (Apache-2.0) "inference-time cognitive control layer packaged as a Skill" by GitHub user **Tiger3807861189** (github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6). Changes no weights; it's a system-prompt/protocol suite (workspace loading, broadcast hub, dense track, ledgers, checkpoints, verification) with an optional local Python controller. It deliberately borrows the name and the global-workspace framing from Anthropic's research (its own `j-space-science.md` is a digest of the Anthropic paper). **Not affiliated with Anthropic or DeepSeek.**
- **Claimed results:** Companion report *DeepSeek V4 × J-Space Capability Realization Report* (github.com/Tiger3807861189/DeepSeek-V4-J-Space-Capability-Realization-Report, DOI 10.5281/zenodo.21971185): DeepSeek V4-Flash + J-Space ≈ GLM-5.3 / Kimi-K3, and V4-Pro-0813 + J-Space *beats Claude Fable 5* on several agentic benchmarks "via a harness fix, not weight changes."

### (c) Terminology drift in the wild
- X posts (e.g., @0x0SojalSec) and Chinese forums (linux.do "Deepseek v4 pro 练出焚决 (J-Space) 超越 Fable5??", bilibili videos) amplify the suite as "J-Space Harness" that "unlocked DeepSeek-V4-Pro Power" / can "干翻 fable5" (beat Fable 5). A Turkish AI-news site (aihaber.org) echoes "J-Space Harness … increases DeepSeek V4 Pro 0813 performance up to 20%". These are re-narrations of the same single self-reported table, not new evidence.

---

## 2. The "better with DeepSeek" claim and its evidence

**What the claim means in practice:** "J-Space (the Cognition Suite) gives dramatically bigger gains on DeepSeek than on any other model, and works better in DeepSeek's harness than any other harness."

**Evidence located:**

1. **The only benchmark table in existence is DeepSeek-only.** Every published "+J-Space" number is from the author's own repo/report, run on DeepSeek V4-Flash-0731 and V4-Pro-0813 via the **official DeepSeek Harness in minimal mode** (`reasoning_effort=max`, t=1.0, top_p=0.95). The report itself discloses: **all J-Space values are single-run, no multi-run averaging, no confidence intervals**; GLM-5.3/Kimi-K3/Opus-4.8/Fable-5 columns are vendor-reported public numbers, *not re-run on a shared harness*.

2. **The suite itself claims the opposite of DeepSeek-specificity.** README: "The operating effects have been reproduced across the DeepSeek, Qwen, GLM, GPT, and Claude model families. The suite does not depend on a vendor-specific API, tokenizer, hidden-state probe, or training recipe… Cross-model reproducibility does not imply identical gains." No non-DeepSeek benchmark numbers are published anywhere — the cross-model claim is asserted, not measured publicly.

3. **The only independent A/B test found contradicts the headline.** GitHub issue #10 (opened 2026-08-17, still open, by community user HHHEEEWWW): two rounds of independent A/B on **DeepSeek V4-Flash** (local dsh). Result: **no measurable completion gain** — T1 correct answers 2.33/3 both groups; T2 6/6 both; T3 interruption-recovery 3/3 both — with **higher cost**: +28% input tokens and +17% time (T1+T2); T3 input tokens ≈3.15× (45,410 vs 14,413) and +36% time; third-party blind score 8.30 (control) vs 7.87 (J-Space). Their conclusion: "In current test conditions, J-SPACE brought no measurable improvement in final task completion, but protocol overhead is significant."

4. **Russian AI outlet nnets.ru (2026-08-18) independently reports the same failure pattern:** "the author's table is assembled from other people's measurements on the original DeepSeek… the skill numbers are one specific measurement… Other people tried to verify: got no benchmark gains, spent more tokens and time." Concludes there is no confirmation the skill "raises any model to top level."

5. **No controlled cross-model or cross-harness comparison exists anywhere.** There is no published experiment of J-Space on dsh vs J-Space on Claude Code/Cursor/opencode, nor on GPT/Qwen/GLM vs DeepSeek, that would support "works far better with DeepSeek than any other harness." The claim's evidence base is: (author's single-run DeepSeek table) + (viral amplification) − (independent verification).

6. **No official DeepSeek endorsement.** No DeepSeek channel (GitHub org, HF, API docs, news) was found acknowledging, endorsing, or testing J-Space. explainx.ai's FAQ likewise states no independent lab, DeepSeek, or Anthropic has confirmed the scores.

**Verdict on the claim's evidence:** unverified marketing/community speculation. The *only* reproducible, controlled data point we found (issue #10) shows no gain at higher cost on DeepSeek V4-Flash. The "DeepSeek > everything" framing is an artifact of the fact that DeepSeek is the only model family anyone has published J-Space numbers for — absence of comparison, not evidence of superiority.

---

## 3. Key benchmark numbers with sources

### Official DeepSeek V4-Pro-0813 launch baselines (the "before" numbers)
| Benchmark | Official (DeepSeek launch, Aug 2026) | Source |
|---|---|---|
| Terminal-Bench 2.1 | 87.9 | qz.com/deepseek-v4-pro-official-launch-081326; explainx.ai blog |
| NL2Repo | 61.5 | same |
| DeepSWE | 62.7 | same |

The J-Space report's "before" column matches these exactly (TB 87.9, NL2Repo 61.5, DeepSWE 62.7) — internally consistent.

### Self-reported "after" numbers (author's single-run table, UNVERIFIED)
| Benchmark | V4-Pro-0813 | + J-Space | Δ | V4-Flash-0731 | + J-Space | Δ |
|---|---:|---:|---:|---:|---:|---:|
| HLE (no tools) | 42.7 | 48.0 | +5.3 | 37.8 | 45.5 | +7.7 |
| HLE (w/ tools) | 60.0 | **67.7** | +7.7 | 51.5 | 60.6 | +9.1 |
| Terminal Bench 2.1 | 87.9 | **90.1** | +2.2 | 82.7 | 87.1 | +4.4 |
| NL2Repo | 61.5 | **73.4** | +11.9 | 54.2 | 70.2 | +16.0 |
| CyberGym | 83.3 | **86.8** | +3.5 | 76.7 | 81.7 | +5.0 |
| DeepSWE | 62.7 | **72.0** | +9.3 | 54.4 | 67.4 | +13.0 |
| Toolathlon-Verified | 74.1 | **79.5** | +5.4 | 70.3 | 77.7 | +7.4 |
| Agents' Last Exam | 25.7 | **30.3** | +4.6 | 25.2 | 30.1 | +4.9 |
| AutomationBench (Pub) | 31.8 | 38.2 | +6.4 | 25.1 | 31.7 | +6.6 |

Source: github.com/Tiger3807861189/DeepSeek-V4-J-Space-Capability-Realization-Report (README §4.2). **Bold** = highest in row among reported columns (Pro+J-Space leads 7 of 9 rows; HLE-no-tools still behind Fable 5's 53.3; AutomationBench still behind GLM-5.3's 48.2). All single-run, no CI; comparator columns are vendor-reported, different methodologies.

Efficiency (self-reported, "fixed uniform scaling coefficients… intentionally omitted"): speed 0.43 → 1.09 (**2.53×**); token efficiency 0.38 → 0.84 (**2.21×**). **UNVERIFIED** — the hidden scaling coefficients make these non-reproducible as published.

### Independent counter-evidence (the only controlled data)
- Issue #10 A/B on V4-Flash: completion identical (2.33/3; 6/6; 3/3), cost higher (+28% tokens, +17% time; T3 tokens 3.15×, +36% time), blind score lower (7.87 vs 8.30). Source: github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6/issues/10
- nnets.ru (2026-08-18): third parties report no gains + higher token/time cost. Source: nnets.ru/news/j-space-cognition-suite-ne-podnimaet-modeli-do-top-urovnja-chto-ne-tak-s-gromkim-skillom

### Baseline sanity for the "beats Fable 5" framing
- Claude Fable 5 = Anthropic's flagship (released 2026-06-09, first Mythos-class model above Opus). anthropic.com/news/claude-fable-5-mythos-5; platform.claude.com docs.
- The J-Space report's reference column for Fable 5 is "Fable 5 (w/ fallback)" vendor numbers — the same claim of superiority rests entirely on the self-reported single-run Pro+J-Space column.

---

## 4. Relationship to DeepSeek Harness (dsh)

- **dsh is real and official:** github.com/deepseek-ai/deepseek-harness — "DeepSeek Harness (dsh) is an open-source agent harness developed by DeepSeek AI." Architecture: "**everything is a plugin**", powered by Cordis; developer preview (`npx @deepseek-ai/dsh web`); npm `@deepseek-ai/dsh`; MIT; dsh-plugin topic for community plugins. (Note: default branch is `master`.)
- **J-Space is NOT an official dsh plugin, mode, or wrapper:**
  - The suite is packaged as a **Skill** (`j-space/SKILL.md` + modules/references/scripts), explicitly "for cross-platform use… not merely a Skill, [but] an inference-time cognitive control system packaged as a Skill." It installs into any skill-capable host (Claude Code, Cursor, etc.), not into dsh's plugin registry.
  - The companion report ran it **on top of** the official DeepSeek Harness "Minimal" configuration as a user-loaded inference-time control layer ("J-Space 采用用户主动加载"), i.e., the harness was dsh; the technique was a separate skill layer.
  - The two *actual* dsh-specific community projects are: **dsh-anchored-standard** (github.com/xiaobright/dsh-anchored-standard — "Experimental DeepSeek Harness agent presets", self-declared community, not official DeepSeek; maintenance-only since 2026-08-17 after API price rises) and **dsh-routing-suite** (github.com/yjh051108/dsh-routing-suite — a dsh injector + thinking-mode routing presets). dsh-anchored-standard's own README lists J-Space as a "model-agnostic inference-time cognitive control layer packaged as a Skill" — i.e., the ecosystem treats J-Space as a separate technique that can be *combined with* dsh, not a dsh component.
- **In short:** J-Space (suite) = independent, model-agnostic skill/protocol that people run *inside* dsh (or other harnesses). It is neither part of dsh nor a harness in competition with dsh.

---

## 5. Per-claim source + grade table

| # | Claim | Source | Grade |
|---|---|---|---|
| 1 | Anthropic discovered a "J-space" (sparse internal workspace) in LLMs via a Jacobian lens, rooted in global workspace theory | anthropic.com/research/global-workspace; arxiv.org/abs/2607.15495; transformer-circuits.pub/2026/workspace | **VERIFIED** (primary, peer-visible paper + open code) |
| 2 | The J-space findings were demonstrated **on Claude** models | Same paper (all experiments on Claude) | **VERIFIED** |
| 3 | Open-source reference implementation exists | github.com/anthropics/jacobian-lens | **VERIFIED** |
| 4 | jspace.com explains the J-space concept / Jacobian Lens | jspace.com; jspace.com/what-is-the-jacobian-lens-and-how-does-it-reveal-j-space/ | **VERIFIED** (site exists & covers concept; it is a third-party explainer site, **not** Anthropic official) |
| 5 | "J-Space Cognition Suite" is a community, non-affiliated, inference-time skill-based harness; changes no weights | github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6 (README, LICENSE, structure) | **VERIFIED** (as an existing open-source artifact; ~1.5k stars, 87 forks per repo page) |
| 6 | Suite's scientific grounding claims to derive from Anthropic's research | Repo `j-space/references/j-space-science.md` | **VERIFIED** (self-documentation) |
| 7 | DeepSeek V4-Pro-0813 official baselines: TB2.1 87.9, NL2Repo 61.5, DeepSWE 62.7 | qz.com/deepseek-v4-pro-official-launch-081326 (reports DeepSeek's official release); corroborated by explainx.ai blog; matches report "before" column | **CORROBORATED** (vendor-reported, two independent outlets, internally consistent) |
| 8 | V4-Pro-0813 + J-Space reaches TB2.1 90.1, NL2Repo 73.4, Toolathlon 79.5, HLE-tools 67.7 etc. | github.com/Tiger3807861189/DeepSeek-V4-J-Space-Capability-Realization-Report §4.2 | **UNVERIFIED** (author self-report, single run, no CI, no external confirmation; explicitly disclosed as such) |
| 9 | V4-Pro + J-Space "beats Fable 5" (and Flash ≈ GLM-5.3/Kimi-K3) | Same report + X posts (@0x0SojalSec), linux.do, bilibili, aihaber.org | **UNVERIFIED** (single self-reported table; Fable 5 column is vendor numbers, not same-harness re-run; amplifyers are re-narrations) |
| 10 | Efficiency gains 2.53× speed, 2.21× token efficiency | Same report §4.5 / suite README | **UNVERIFIED** (scaling coefficients "intentionally omitted" — not reproducible as published) |
| 11 | J-Space effects reproduce across DeepSeek, Qwen, GLM, GPT, Claude families | Suite README "Cross-model reproducibility" | **UNVERIFIED** (asserted; no published numbers for any non-DeepSeek model) |
| 12 | J-Space is a dsh plugin / mode / wrapper | — | **DISPROVEN** (suite is a Skill-layer run on top of dsh; dsh has no J-Space component; ecosystem READMEs position it as separate) |
| 13 | "J-Space operates far, far better with DeepSeek than with any other harness/model" | No source found making or supporting this comparative claim | **UNVERIFIED / NOT SUPPORTED** (no controlled cross-model or cross-harness comparison exists; contradicted by suite's own model-agnostic framing and by issue #10) |
| 14 | Independent A/B on DeepSeek V4-Flash: no measurable completion gain; higher token/time cost | github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6/issues/10 (community, 2026-08-17); corroborated by nnets.ru (2026-08-18) | **CORROBORATED** (two independent sources report the same failure pattern; small n, not statistically significant — treated as directional counter-evidence) |
| 15 | dsh-anchored-standard & dsh-routing-suite are community projects, not official DeepSeek | github.com/xiaobright/dsh-anchored-standard; github.com/yjh051108/dsh-routing-suite | **VERIFIED** (self-declared in READMEs) |

---

## 6. Bottom-line verdict

**The user's claim — "J-space operates far far better with deepseek than any other harness" — does NOT hold as stated, and no evidence was found to support its "far better than any other" comparative core.**

- **What is true (VERIFIED):** Anthropic's J-space is real science, but it is about **Claude**; the J-Space Cognition Suite is a real, open-source, model-agnostic skill-layer that anyone can run on DeepSeek, dsh, or other harnesses.
- **What is unverified:** every headline number (DeepSeek "beats Fable 5", TB2.1 90.1, NL2Repo 73.4, Toolathlon 79.5, 2.5× efficiency) is **single-source, single-run, self-reported** by the project author, explicitly without confidence intervals, with hidden scaling in the efficiency metrics, and with competitor columns taken from vendor PRs rather than shared-harness re-runs. No independent lab, DeepSeek, or Anthropic has confirmed anything.
- **What contradicts it:** the only controlled independent test found (issue #10, DeepSeek V4-Flash, Aug 17 2026) measured **zero completion gain and materially higher token/time cost**; nnets.ru independently reports the same from "other people" who tried. The suite itself claims cross-model reproducibility — i.e., it explicitly does NOT claim DeepSeek-specific superiority.
- **Why the illusion exists:** 100% of published J-Space benchmark numbers are DeepSeek numbers, so the hype narrative conflates "the only model anyone measured" with "the model it works best on." "Harness" is also a category error: J-Space is a skill/protocol that runs *inside* harnesses (including dsh), not a harness itself, and no cross-harness comparison was ever run.

**Confidence:** High (90%) that the comparative claim is unsupported marketing/speculation. The residual uncertainty is that (a) the author's single-run Pro numbers have not been independently re-tested (the one independent test used Flash, not Pro), and (b) this is a fast-moving August-2026 story — new verification could land any day. Recommendation for the researcher: treat J-Space as an interesting, cheap-to-test prompt protocol; any real adoption decision should rest on your own A/B on the exact model+harness+tasks you care about, not on the circulating tables.

---

## Source index (all fetched directly unless noted)

1. https://www.anthropic.com/research/global-workspace (Anthropic blog, 2026-07-06)
2. https://arxiv.org/abs/2607.15495 (paper; also https://arxiv.org/pdf/2607.15495)
3. https://transformer-circuits.pub/2026/workspace/ (Transformer Circuits Thread)
4. https://github.com/anthropics/jacobian-lens
5. https://jspace.com/ and https://jspace.com/what-is-the-jacobian-lens-and-how-does-it-reveal-j-space/ (third-party explainer site)
6. https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6 (+ issues/10, + j-space/references/j-space-science.md)
7. https://github.com/Tiger3807861189/DeepSeek-V4-J-Space-Capability-Realization-Report (DOI 10.5281/zenodo.21971185)
8. https://github.com/deepseek-ai/deepseek-harness (official dsh; branch `master`; npm @deepseek-ai/dsh)
9. https://github.com/xiaobright/dsh-anchored-standard
10. https://github.com/yjh051108/dsh-routing-suite
11. https://explainx.ai/blog/j-space-cognition-suite-deepseek-v4-pro-harness-august-2026 (skeptical analysis, 2026-08-18)
12. https://nnets.ru/news/j-space-cognition-suite-ne-podnimaet-modeli-do-top-urovnja-chto-ne-tak-s-gromkim-skillom (skeptical, 2026-08-18)
13. https://qz.com/deepseek-v4-pro-official-launch-081326 (official launch numbers)
14. https://trendshift.io/repositories/164400 (repo activity; quotes X post @0x0SojalSec)
15. https://linux.do/t/topic/2762842 (Chinese forum hype); https://www.bilibili.com/video/BV1Zigg69Epa/ (video hype)
16. https://www.anthropic.com/news/claude-fable-5-mythos-5 ; https://www.anthropic.com/claude/fable (Fable 5 identity)
17. https://aihaber.org/j-space-harness-deepseek-v4-pro-0813un-performansini-+ye-kadar-artiriyor/ (Turkish echo; page returned 404 on direct fetch at research time — indexed snippet only)
18. https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro (model card; card shows earlier V4-Pro benchmarks — the 0813 table is from the official launch reporting)
