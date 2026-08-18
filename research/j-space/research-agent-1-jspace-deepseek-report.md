# Research Agent #1 Report: "J-space" and the claim that it works far better with DeepSeek than any other harness

**Date of research:** 2026-08-18 (all sources verified via live fetch on this date)
**Researcher:** Independent research agent #1 of 3 (isolated context)
**Claim under test:** *"J-space operates far far better with deepseek then any other harness"*

---

## 1. What "J-space" is — disambiguation (three distinct things share the name)

### 1a. J-space, the Anthropic interpretability concept (the REAL, primary meaning)
- **VERIFIED** via primary sources. Anthropic's paper *"Verbalizable Representations Form a Global Workspace in Language Models"* (Wes Gurnee, Nicholas Sofroniew, Adam Pearce, Jack Lindsey et al., Anthropic; published July 6, 2026) defines the **J-space** as a privileged, small collection of internal neural representations in Claude that are *poised to be verbalized*: reportable, deliberately modulatable, used for intermediate reasoning, and broadcast to many downstream computations. It is measured with the **Jacobian lens (J-lens)**, which finds, for each vocabulary word, the internal activation pattern that makes the model more likely to say that word in the future.
  - Sources: https://transformer-circuits.pub/2026/workspace/index.html ; https://www.anthropic.com/research/global-workspace
- The paper explicitly ties this to global workspace theory (Baars). Anthropic says J-space is **not** the same as chain-of-thought/scratchpad; it is silent, in activations.
- Anthropic open-sourced the technique: **anthropics/jacobian-lens** (Apache-2.0), which "fits the lens on open-weights decoder transformers" — i.e., the technique is **model-agnostic by design**, not DeepSeek-specific (https://github.com/anthropics/jacobian-lens). Independent reproductions exist on open models (e.g., https://huggingface.co/blog/dlouapre/j-space; fitting J-lens on Qwen takes ~100 prompts per https://www.linkedin.com/pulse/how-anthropics-jacobian-lens-reads-what-model-say-alphasignal-p3bif).
- **jspace.com** (https://jspace.com/) is a third-party WordPress explainer site ("Research explainers on AI interpretability, J-Space, and the Jacobian Lens"), first post dated 2026-08-05, with posts like "J-Space Anthropic explained" (2026-07-16 per its own datePublished). It explains the **Anthropic concept**. It is NOT an Anthropic domain, NOT the harness project, and its authorship is not disclosed (UNVERIFIED). Its content has nothing to do with DeepSeek harnesses.

### 1b. "J-Space Cognition Suite" — a community prompt/skill harness (the thing the viral claim is about)
- **VERIFIED to exist, UNVERIFIED in its claims.** A community project by GitHub user **Tiger3807861189** (identified in the repo description as Bilibili creator "Tiger380", UID 3494375382321675; repo created 2026-07-22, V3.6 released ~2026-08-17, 1,542 stars at time of research):
  - Suite repo: https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6
  - Capability report repo: https://github.com/Tiger3807861189/DeepSeek-V4-J-Space-Capability-Realization-Report
- What it actually is: **an inference-time text-protocol / "Skill" package** (SKILL.md + 9 modules + optional local controller script). It explicitly says: "The suite changes no model weights... It is an inference-time cognitive control layer." It addresses: working-set overload, representation drift, uncontrolled retry, premature completion. It is **not** the Jacobian lens, does not measure activations, and is not affiliated with Anthropic or DeepSeek.
- Name relationship: the suite **borrows** the name and conceptual framing from Anthropic's research. Its own README: "The suite uses J-space as the operational name for that accessible workspace." Its scientific-scope section says it is "grounded in Anthropic's related research" but "does not claim that text instructions directly expose every hidden activation." explainx.ai independently confirms the name overlap "is a coincidence worth flagging, not a connection" (https://www.explainx.ai/blog/j-space-cognition-suite-deepseek-v4-pro-harness-august-2026).
- The suite claims **model-agnostic** operation: "The operating effects have been reproduced across the **DeepSeek, Qwen, GLM, GPT, and Claude** model families" (suite README, Cross-model reproducibility section). GitHub topics tag it for claude-code, codex, opencode, hermes-agent, dsh — i.e., it presents itself as a cross-harness Skill.

### 1c. Competing sibling projects in the same viral wave (context)
- The capability report compares J-Space against two other community "suites" for the DeepSeek Harness: **dsh-anchored-standard** (xiaobright, 3,493 stars) and **dsh-routing-suite** (yjh051108, 5,741 stars) — both created 2026-08-14, both now more popular than J-Space on GitHub.
  - https://github.com/xiaobright/dsh-anchored-standard ; https://github.com/yjh051108/dsh-routing-suite
- This is a wave of prompt/skill packs riding both the DeepSeek V4 GA launch (Aug 14, 2026) and Anthropic's July J-space paper.

---

## 2. The "better with DeepSeek" claim and its evidence

**The claim as it circulates (X, Aug 17–18, 2026):** "J-Space Cognition Suite just unlocked DeepSeek-V4-Pro Power... without weight changes, just fixed the thinking... completely outperforms Fable across every task" — amplified by accounts including @jun_song, @0x0SojalSec, and an AI-generated reply from xAI's Grok account:
- https://x.com/jun_song/status/2089412146748948782
- https://x.com/grok/status/2089412502006219224 (Grok itself concedes official scores are only "competitive with Fable 5")
- https://x.com/0x0SojalSec/status/2089418544312381462
(Content quoted as indexed by search engines; X itself was not directly fetchable in this session.)

**What the evidence actually consists of:**

1. **The author's own single-run benchmark table** (capability report §4.2). Baseline ("before") numbers match DeepSeek's official model card exactly (verified against https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813). The "+J-Space" numbers are the author's own runs. Competitor columns (GLM-5.3/Kimi-K3/Opus-4.8/Fable-5) are **taken from each vendor's own published results — not re-run under the same harness**. The report itself states (§4.4): "不同厂商保留各自发布时的评测方法，因此这里描述的是公开能力位置，而不是统一 harness 的严格横向实验" = "different vendors retain their own evaluation methods at release; this describes public capability position, NOT a strict horizontal experiment on a unified harness." And (§6): "单次结果不代表稳定分布" = single results do not represent stable distributions; formal research needs multiple seeds, confidence intervals, and per-task trajectory logs. **The report's own authors admit it is not a controlled comparison.**

2. **The only independent-ish evaluation found — a community A/B test posted in the author's own repo (issue #10)** — reached the OPPOSITE conclusion:
   - Round 1 (5 tasks, A/B ×1): both groups completed everything; no difference in final correctness.
   - Round 2 (3 tasks, A/B ×3, 12 runs, third-party blind scoring): task completion identical (T1 2.33/3 vs 2.33/3; T2 6/6 vs 6/6; T3 recovery 3/3 vs 3/3); **J-Space added +28% input tokens (T1+T2), ~3.15× input tokens (T3), +17–36% time**; blind score control 8.30 vs J-Space 7.87 (control slightly higher, not significant).
   - Verbatim conclusion: "在当前测试条件下，J-SPACE 没有带来可测的最终任务完成度提升，但协议开销明显" = "Under current test conditions, J-SPACE brought no measurable improvement in final task completion, but protocol overhead is significant."
   - Source: https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6/issues/10 (community, unpeer-reviewed, small sample — flagged as such by the authors themselves).

3. **Direct community testimony contradicting DeepSeek-specificity** (issue #4, open): a user who built a near-identical skill ("思维堆栈" / thinking-stack) says applying the same technique to **Opus 5, ChatGPT 5.6 Sol, and Kimi K3 also improved their performance**, and therefore scores must be compared with the same skill applied to other models: "不能确认仅DeepSeek v4 pro受益于该skill，说不定其他模型因此受益幅度更大呢" = "you cannot conclude only DeepSeek V4 Pro benefits; maybe other models benefit even more." (https://github.com/Tiger3807861189/DeepSeek-V4-J-Space-Capability-Realization-Report/issues/4)

4. **Unanswered requests for raw data + deleted criticism**: issue #7 requests actual DeepSWE/NL2Repo trajectories ("不太认可这样夸张的涨幅，请提供...轨迹" — "I don't accept such exaggerated gains; please provide trajectories"); no public trajectories exist. Issues #5 and #6 are missing from the repo, and issue #8 asks: "为啥把质疑的issue删掉了？" = "Why was the questioning issue deleted?" (https://github.com/Tiger3807861189/DeepSeek-V4-J-Space-Capability-Realization-Report/issues/8)

5. **The suite's own cross-model claim** contradicts the "DeepSeek-specific advantage" framing (§1b above).

**Bottom line for this section:** There is **zero controlled, comparative, or independently reproduced measurement** showing J-Space works better with DeepSeek than with any other model or harness. Every "beats Fable 5" headline traces back to one author's self-reported single runs compared against other vendors' differently-harnessed official scores. The only attempted independent A/B found no improvement (and real overhead) on DeepSeek itself.

---

## 3. Key benchmark numbers with sources

**Official DeepSeek card (V4-Pro-0813, DeepSeek's own numbers — VERIFIED):** https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813
| Benchmark | V4-Pro-0813 | Fable 5 (w/ fallback) | V4-Flash-0731 |
|---|---|---|---|
| HLE (wo/w tools) | 42.7 / 60.0 | 53.3 / 63.0 | 37.8 / 51.5 |
| Terminal Bench 2.1 | 87.9 | 88.0 | 82.7 |
| NL2Repo | 61.5 | — | 54.2 |
| CyberGym | 83.3 | 83.1 | 76.7 |
| DeepSWE | 62.7 | 70.0 | 54.4 |
| Toolathlon-Verified | 74.1 | 77.9 | 70.3 |
| Agents' Last Exam | 25.7 | — | 25.2 |
| AutomationBench | 31.8 | 29.1 | 25.1 |
| DSBench-FullStack/Hard | 71.1 / 67.2 | 77.2 / 68.3 | 68.7 / 59.6 |

Official framing: "broadly competitive with the strongest proprietary models" — **official numbers do NOT show V4-Pro-0813 beating Fable 5 overall**; Fable 5 leads HLE, TB 2.1, DeepSWE, Toolathlon, DSBench. Official card also confirms the code-agent numbers were measured "with the minimal mode of DeepSeek Harness as the agent framework" (the very harness whose "minimal mode" the J-Space suite wraps). Secondary confirmation: VentureBeat, https://venturebeat.com/technology/deepseek-harness-launches-as-open-source-rival-to-claude-code-alongside-v4-pro-on-api-with-higher-prices

**J-Space capability report table (author's single runs + vendor numbers — UNVERIFIED):** https://github.com/Tiger3807861189/DeepSeek-V4-J-Space-Capability-Realization-Report (§4.2)
| Benchmark | V4-Pro | Pro+J-Space | GLM-5.3 | Kimi-K3 | Opus-4.8 | Fable 5 |
|---|---|---|---|---|---|---|
| HLE (no tools) | 42.7 | 48.0 | — | 43.5 | 49.8 | **53.3** |
| HLE (w/ tools) | 60.0 | **67.7** | 62.5 | 56.0 | 57.9 | 63.0 |
| Terminal Bench 2.1 | 87.9 | **90.1** | 88.2 | 88.3 | 85.0 | 88.0 |
| NL2Repo | 61.5 | **73.4** | 58.0 | 58.0 | 69.7 | — |
| CyberGym | 83.3 | **86.8** | 84.5 | 80.0 | 78.3 | 83.1 |
| DeepSWE | 62.7 | **72.0** | 66.9 | 67.5 | 58.0 | 70.0 |
| Toolathlon-Verified | 74.1 | **79.5** | 73.0 | 76.5 | 76.2 | 77.9 |
| Agents' Last Exam | 25.7 | **30.3** | 28.5 | 27.6 | 25.7 | 23.8 |
| AutomationBench | 31.8 | 38.2 | **48.2** | 30.8 | 27.2 | 29.1 |

Per the report itself: Pro+J-Space leads 7/9 rows, but **HLE-no-tools still trails Fable 5 (48.0 < 53.3) and AutomationBench still trails GLM-5.3 (38.2 < 48.2)**. Baseline rows match the official card exactly; J-Space rows are single runs; competitor rows are vendor-reported. Also claimed (Flash, single-run): score/time 0.43→1.09 (**2.53×**), score/token 0.38→0.84 (**2.21×**) — contradicted in direction by issue #10's measured token/time overhead.

**Circulating headline numbers** (explainx FAQ, quoting the project): TB 2.1 87.9→90.1, NL2Repo 61.5→73.4, Toolathlon-Verified up to 79.5 — consistent with the report table. (https://www.explainx.ai/blog/j-space-cognition-suite-deepseek-v4-pro-harness-august-2026)

**Independent A/B (issue #10):** no completion gain; +28% tokens / +17–36% time; blind score 7.87 vs 8.30 control. (https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6/issues/10)

---

## 4. Relationship to DeepSeek Harness (dsh)

- **dsh is real and official**: https://github.com/deepseek-ai/deepseek-harness ("DeepSeek Harness: Everything is a Plugin."), MIT, Cordis-based, developer preview, launched ~Aug 14, 2026 alongside V4-Pro GA; official page https://www.deepseek.com/harness/en/. Its architecture: models, tools, skills, sessions, sandboxes, storage, loops, UI are all plugins.
- **J-Space is NOT part of dsh.** I cloned the official repo and grepped for jspace/j-space/jacobian: **zero matches**. No official DeepSeek channel (model card, harness docs, deepseek.com) mentions J-Space.
- **J-Space is a third-party artifact that runs ON TOP of dsh** (and on other harnesses). It is packaged as a "Skill" (SKILL.md), and dsh treats skills as plugins; the suite self-tags with the `dsh-plugin` topic and lists `deepseek-harness`, `dsh`, `claude-code`, `codex`, `opencode`, `hermes-agent` among its topics. So in dsh terms it is a **community plugin/skill**, not an official mode or a fork.
- Two sibling community suites (anchored-standard, routing-suite) are similarly third-party dsh presets (§1c).
- **The name is the only link to the Anthropic J-lens**: the suite is a text-protocol control layer that *invokes the concept* of a workspace; it performs no activation measurement. The actual Jacobian lens (anthropics/jacobian-lens) is a separate, open, model-agnostic interpretability tool that has nothing to do with benchmark gains.

---

## 5. Per-claim source + grade table

| # | Claim | Sources | Grade |
|---|---|---|---|
| 1 | J-space = internal verbalizable "global workspace" in LLMs, found via Jacobian lens | https://transformer-circuits.pub/2026/workspace/index.html ; https://www.anthropic.com/research/global-workspace | **VERIFIED** (primary, peer-style research writeup) |
| 2 | Anthropic released open J-lens code; technique runs on open-weights models (model-agnostic) | https://github.com/anthropics/jacobian-lens ; https://huggingface.co/blog/dlouapre/j-space | **VERIFIED** (primary code repo + independent reproduction) |
| 3 | jspace.com explains Anthropic's J-space concept | https://jspace.com/ (+ /j-space-anthropic-explained/) | **CORROBORATED** (site content matches Anthropic research; authorship of site UNVERIFIED) |
| 4 | "J-Space Cognition Suite" exists as an open-source inference-time Skill/suite, no weight changes | https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6 | **VERIFIED** (primary repo, readable code/docs) |
| 5 | Suite is based on / borrows from Anthropic's J-space research, but is unrelated to Anthropic/DeepSeek official | Suite README (Scientific scope); https://www.explainx.ai/blog/j-space-cognition-suite-deepseek-v4-pro-harness-august-2026 | **VERIFIED** (primary docs + independent secondary) |
| 6 | Suite claims effects reproduced across DeepSeek, Qwen, GLM, GPT, Claude families (model-agnostic) | Suite README, "Cross-model reproducibility" | **UNVERIFIED** (self-reported; no published numbers) |
| 7 | V4-Pro-0813 + J-Space beats Fable 5 on 7 of 9 benchmarks; TB 2.1 87.9→90.1, NL2Repo 61.5→73.4, Toolathlon 74.1→79.5 | https://github.com/Tiger3807861189/DeepSeek-V4-J-Space-Capability-Realization-Report §4.2; explainx FAQ | **UNVERIFIED** (single author runs; competitors not re-run; report admits non-comparable methodology) |
| 8 | Report's "before" numbers = official DeepSeek card numbers | Report §4.2 vs https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813 | **VERIFIED** (exact match, 9/9 rows) |
| 9 | "V4-Pro-0813 beats Fable 5 on key benchmarks" (official framing) | Official model card | **DISPROVEN** — official card says "broadly competitive"; Fable 5 leads most rows |
| 10 | J-Space improves task completion | https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6/issues/10 (community A/B) | **DISPROVEN as general claim** — A/B found no measurable completion gain on DeepSeek V4-Flash; overhead +28% tokens to 3.15× tokens, +17–36% time; blind score favored control |
| 11 | "J-space works far far better with DeepSeek than any other harness" (the user's claim) | No comparative source exists; contradicted by suite's own cross-model claims, issue #4 testimony, issue #10 | **UNVERIFIED / effectively DISPROVEN as stated** — zero controlled comparative measurement anywhere |
| 12 | J-Space is part of official DeepSeek Harness | Clone+grep of https://github.com/deepseek-ai/deepseek-harness; https://www.deepseek.com/harness/en/ | **DISPROVEN** — zero mentions; it is a community plugin/skill |
| 13 | Viral X narrative "simple harness fix, insane scores, outperforms Fable across every task" | https://x.com/jun_song/status/2089412146748948782 ; https://x.com/grok/status/2089412502006219224 ; https://x.com/0x0SojalSec/status/2089418544312381462 | **UNVERIFIED** (marketing/viral amplification; Grok's own reply downgrades to "competitive") |
| 14 | explainx.ai skepticism: numbers self-reported, not independently verified, no lab confirmation | https://www.explainx.ai/blog/j-space-cognition-suite-deepseek-v4-pro-harness-august-2026 | **CORROBORATED** (independent secondary analysis; consistent with primary evidence above) |

---

## 6. Bottom-line verdict

**The claim "J-space operates far far better with DeepSeek than any other harness" does NOT hold up. As stated, it is unsupported marketing, and the available evidence points the other way.**

- There is **no reproducible benchmark** behind it: no controlled run of J-Space against other models or other harnesses exists anywhere. The "beats Fable 5" numbers compare the author's single-run DeepSeek scores against competitors' *own vendor-reported* scores measured under *different* harnesses — an apples-to-oranges table whose non-comparability the author himself concedes in the report (§4.4, §6).
- The only independent attempt at verification (community A/B, issue #10) found **no measurable improvement and significant overhead** on DeepSeek itself.
- The suite's own documentation says it is **model-agnostic** and reproduced across DeepSeek, Qwen, GLM, GPT, and Claude — which directly contradicts a DeepSeek-specific "far far better" framing; a community practitioner with a similar skill reports comparable gains on other models (issue #4).
- The "J-space" name is doing heavy lifting: the viral claim borrows prestige from Anthropic's genuine interpretability research while the actual artifact is an unrelated prompt/skill pack by an individual creator. The real Jacobian lens is a model-agnostic measurement tool, not a performance harness.
- Official DeepSeek itself never claims to beat Fable 5 — its card says "broadly competitive," and its official dsh repo has zero J-Space content.

**Confidence: HIGH (~85%)** that the claim as stated is unverified marketing rather than a reproducible result. Residual uncertainty: (i) prompt/skill engineering genuinely can shift agent benchmark results, so some task-specific benefit on DeepSeek is plausible and untested by me; (ii) all primary artifacts are only days old (Aug 14–18, 2026) and may evolve; (iii) I could not directly fetch X posts or jspace.com's full body text in this session (quotes via search-engine indexing). None of this rescues the specific "far better with DeepSeek than any other harness" claim, which lacks even a single comparative measurement.

**Recommendation for Zachariah Markusson:** treat any "J-Space unlocks DeepSeek V4" headline as a hypothesis, not a result. A 30-minute controlled A/B (same model, same tasks, J-Space skill loaded vs not, both under dsh minimal mode) on his own workloads is the only way to test it, and it should compare a plain strong system-prompt baseline too — the community A/B suggests the marginal value over a good baseline may be small or negative.
