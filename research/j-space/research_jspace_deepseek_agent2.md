# J-Space and the "better with DeepSeek" claim — Independent Research Report

**Agent:** Research agent #2 of 3 (isolated) · **Date of research:** 2026-08-18 · **Commissioned by:** Zachariah Markusson (via parent agent)
**Claim tested:** *"J-space operates far far better with deepseek than any other harness."*

**Method note:** `web_extract` was unavailable (search-only backend), so all page content was fetched via `curl` with a browser UA and HTML-stripped. Every URL below was fetched and read in full (or head/tail sections) during this session. No URL or number is fabricated.

---

## 1. What "J-space" is — disambiguation (three distinct things)

There are **three** distinct referents that share the "J-space" name. Conflating them is the root of the hype.

### (a) Anthropic's J-space — a measured internal activation subspace in Claude (interpretability research)
- **Primary source:** "Verbalizable Representations Form a Global Workspace in Language Models," Transformer Circuits Thread, published **2026-07-06** — https://transformer-circuits.pub/2026/workspace/index.html
- **Companion blog:** https://www.anthropic.com/research/global-workspace ("A global workspace in language models", Jul 6, 2026)
- **Companion code:** https://github.com/anthropics/jacobian-lens (reference implementation, Apache-2.0, "Examples use Qwen; other HuggingFace decoders adapt cleanly")
- **What it is:** Anthropic found that a small, sparse set of internal neural patterns in Claude ("J-space," named after the Jacobian-based "J-lens" technique) holds concepts the model is *poised to say* — reportable, modulatable, usable in internal multi-step reasoning — even when never written to output. They argue it behaves like the "global workspace" of Baars / Dehaene et al. theory. It is a **measurement/interpretability construct about Claude**, not a harness, not a prompt, not software you "run."
- **Scope check:** I grepped the Transformer Circuits page for "deepseek" — **0 mentions**. The research is about Claude only. Anthropic's J-lens reference implementation fits on open-weight decoders (Qwen example), but **no primary source I found measures J-space specifically in DeepSeek models**.
- **Corroboration (secondary):** MIT Tech Review (2026-07-09, says it was found in "Claude Opus 4.6"), VentureBeat (2026-07-06), Forbes (2026-07-12), LessWrong review (2026-07-06), Hugging Face community blog by David Louapre (2026-07-13) which independently reproduces a small example on an open model.

### (b) J-Space Cognition Suite — a community prompt/skill package that borrows the name
- **Repo:** https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6 (created 2026-07-22; ~1,542 stars, 87 forks; topics incl. `dsh`, `dsh-plugin`, `hermes-agent`, `claude-code`, `opencode`, `codex`, `j-space`, `global-workspace`; description: *"AI cognitive-enhancement Skills based on Anthropic's J-space global workspace research"*)
- **What it is (its own words):** *"a model-agnostic inference-time cognitive control layer"* — an operating protocol (workspace loading, broadcast hub, "dense track," checkpoints, ledger, verification loops, first-person control grammar) **packaged as a Skill** (SKILL.md + modules/ + references/). No weights changed, no fine-tuning, no hidden service.
- **Relationship to Anthropic's J-space:** **Name + vocabulary borrowed, not the same thing.** The suite's own science reference (`j-space/references/j-space-science.md`) digests the Anthropic paper and uses "J-space" as an *operational name* for the model's accessible workspace; the suite's mechanisms are prompt-level control heuristics, not the measured activation subspace. explainx.ai explicitly flags the overlap as "a coincidence worth flagging, not a connection."

### (c) The DeepSeek V4 × J-Space "Capability Realization Report" — the benchmark claims
- **Repo:** https://github.com/Tiger3807861189/DeepSeek-V4-J-Space-Capability-Realization-Report (created **2026-08-16**, i.e. 2 days before this research; ~778 stars, 45 forks; Zenodo DOI claimed: 10.5281/zenodo.21971185)
- **Thesis:** DeepSeek V4-Flash-0731 / V4-Pro-0813 suffer "capability-realization loss" (interface/trajectory/state/verification mismatches) that J-Space reduces at inference time. Introduces the author's own terms "chain-of-thought diode" and "capability-realization loss," explicitly labeled as *engineering diagnoses of black-box behavior, not official DeepSeek disclosures*.

### (d) Also encountered
- **jspace.com** — a third-party WordPress explainer site ("Research explainers on AI interpretability, J-Space, and the Jacobian Lens," published ~Aug 2026). It is **not** an Anthropic property and not a primary source; it is SEO-style explainer content riding the research.
- **"Operation Cheepseek"** — a nickname for this whole story used in explainx.ai's coverage; no independent primary source found.

---

## 2. The "better with DeepSeek" claim and its evidence

**The claim as tested:** *"J-space operates far far better with deepseek than any other harness."*

**What evidence actually exists:**

1. **Anthropic's J-space research says nothing about DeepSeek** (0 mentions on the TC page). It is about Claude. There is no published J-lens/J-space measurement of DeepSeek models that I could find. The interpretability concept therefore cannot substantiate a "better with DeepSeek" claim in any direction.

2. **The J-Space Cognition Suite's own README claims model-agnosticism**: *"The operating effects have been reproduced across the DeepSeek, Qwen, GLM, GPT, and Claude model families."* This directly contradicts the idea that J-Space (the suite) is DeepSeek-special. It also publishes **zero cross-model benchmark tables** — no numbers for Qwen/GPT/Claude/GLM with the suite — so there is no basis for any "better with X than Y" comparison.

3. **The only benchmark table** (report §4.2) compares **DeepSeek + J-Space (suite-run)** against **vendor-published baselines** for GLM-5.3, Kimi-K3, Opus-4.8, Fable 5 — explicitly *not* a unified harness experiment (*"GLM-5.3、Kimi-K3、Opus-4.8 与 Fable 5 保留各厂商公开时的评测方法，仅作为能力位置参照，不表示所有模型由同一 harness 重测"*). All J-Space numbers are **single-run** with no confidence intervals (*"所有结果按单次运行记录，不表示多次均值，也不附带置信区间"*).

4. **No independent reproduction exists.** explainx.ai (Aug 18, 2026): *"No independent lab, DeepSeek, or Anthropic has confirmed these scores as of this post."* nnets.ru (Russian AI outlet, Aug 18, 2026) likewise: hype without confirmation. Community tests so far are anecdotal and **mixed** — a V2EX user testing the skill on DeepSeek V4 Pro (dsh 0.1.0-rc.6) reported the effect *"感觉变差了"* ("feels worse") on one task and better on another.

5. **Timeline red flag:** the report repo was created Aug 16, 2026; the hype posts on X are Aug 17–18; explainx and nnets.ru skeptical coverage landed Aug 18 — the entire cluster is **2–4 days old**. Zero time for external validation.

**Verdict on the claim:** as a factual statement it is **unsupported — effectively unverified marketing/speculation**. It is a three-way category error (research construct ≠ suite ≠ benchmark claim), it lacks any controlled comparison across harnesses or models, its only numbers are self-reported single-run, and the suite's own framing contradicts DeepSeek-specificity.

---

## 3. Key benchmark numbers with sources

All from the report README (https://github.com/Tiger3807861189/DeepSeek-V4-J-Space-Capability-Realization-Report) — **single-run, self-reported, J-Space columns run by the suite author only**. Comparator columns are vendor-published, different methodologies.

| Benchmark | V4-Pro-0813 (base) | +J-Space (claimed) | Best comparator (vendor-published) |
|---|---|---|---|
| HLE (no tools) | 42.7 | 48.0 | Fable 5: **53.3** (Fable still wins) |
| HLE (with tools) | 60.0 | **67.7** | Fable 5: 63.0 |
| Terminal Bench 2.1 | 87.9 | **90.1** | GLM-5.3: 88.2; Fable 5: 88.0 |
| NL2Repo | 61.5 | **73.4** | Opus-4.8: 69.7 |
| CyberGym | 83.3 | **86.8** | GLM-5.3: 84.5 |
| DeepSWE | 62.7 | **72.0** | Fable 5: 70.0 |
| Toolathlon-Verified | 74.1 | **79.5** | Fable 5: 77.9 |
| Agents' Last Exam | 25.7 | **30.3** | GLM-5.3: 28.5 |
| AutomationBench (Public) | 31.8 | 38.2 | GLM-5.3: **48.2** (GLM still wins) |
| Efficiency: score/time | 0.43 | **1.09 (2.53×)** | — |
| Efficiency: score/token | 0.38 | **0.84 (2.21×)** | — |

- **The "before" numbers match DeepSeek's official launch baseline** (explainx: "DeepSeek's own official launch reported 87.9 on Terminal-Bench 2.1 and 61.5 on NL2Repo... which matches the 'before' numbers") — a small point in favor of the runs being against the real model, but it says nothing about the "after" numbers.
- **Red flags:** single-run; no CIs; efficiency scaling coefficients "intentionally omitted" (display-scale only); the report itself lists falsification conditions and admits *"单次结果不代表稳定分布"* ("single-run results do not represent a stable distribution") and *"厂商公开成绩不是统一对照实验"* ("vendor-published scores are not a unified control experiment").
- DeepSeek V4-Pro official model card: https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro (verified to exist; V4 series preview Apr 2026, arXiv:2606.19348, https://arxiv.org/abs/2606.19348). Claude Fable 5 (Anthropic, Jun 9, 2026): https://www.anthropic.com/news/claude-fable-5-mythos-5.

---

## 4. Relationship to DeepSeek Harness (dsh)

- **dsh** = DeepSeek AI's open-source agent harness (github.com/deepseek-ai/deepseek-harness), MIT, released **Aug 13, 2026**, developer preview, Cordis-based, "everything is a plugin" architecture. Verified: README contains **no mention of J-Space**; GitHub issue search for "J-Space" in deepseek-ai/deepseek-harness returns **0 results**.
- **J-Space Cognition Suite is a third-party community project, not part of dsh.** It is distributed as a **Skill package** (its own README; also listed on skills.sh). It carries the `dsh-plugin` topic tag for discoverability (dsh's README invites community repos to add that tag) and its benchmarks are run *inside* dsh's minimal mode ("DeepSeek Harness Minimal 组合, reasoning_effort=max, temperature=1.0, top_p=0.95") — but it is not shipped by DeepSeek, not in the official docs, and not required to use dsh.
- **Ecosystem position** (from the report and from xiaobright/dsh-anchored-standard's README): three sibling community approaches on top of dsh — **Anchored Standard** (xiaobright/dsh-anchored-standard: first-round Minimal-interface anchoring, then promotion to Standard tools), **Routing Suite** (yjh051108/dsh-routing-suite: task-aware behavior-band/persona routing), and **J-Space Cognition Suite** ("a model-agnostic inference-time cognitive control layer packaged as a Skill"). The report's own framing: *"J-Space 是一个插件"* — i.e., it is a skill/plugin layered on dsh, not a dsh mode or official component. Best description: an **inference-time prompt/protocol wrapper (Skill)** that can run in dsh or any skill-aware environment (Claude Code, Codex, OpenCode, Hermes, etc.).
- Note: the suite repo predates dsh's public release (suite created Jul 22 vs dsh released Aug 13), so the suite was built as a general skill first and only later positioned within the dsh ecosystem.

---

## 5. Per-claim source + grade table

| # | Claim | Source(s) | Grade |
|---|---|---|---|
| 1 | Anthropic published J-space / Jacobian-lens research on Jul 6, 2026 | https://transformer-circuits.pub/2026/workspace/index.html ; https://www.anthropic.com/research/global-workspace | **VERIFIED** (primary, reproducible code at github.com/anthropics/jacobian-lens) |
| 2 | J-space is a small sparse internal workspace of reportable concepts in Claude, discovered via J-lens | Anthropic post (same URLs); MIT Tech Review https://www.technologyreview.com/2026/07/09/1140293/ ; VentureBeat https://venturebeat.com/technology/anthropics-new-j-lens-reveals-a-silent-workspace-inside-claude-that-mirrors-a-leading-theory-of-consciousness | **VERIFIED** (as Anthropic's finding about Claude) |
| 3 | The J-lens / J-space research is about DeepSeek or says anything about DeepSeek | grep of TC page: 0 mentions of "deepseek"; no DeepSeek J-lens study found | **DISPROVEN** (as a characterization of the research; the research is Claude-only) |
| 4 | jspace.com is a primary source for J-space | https://jspace.com/ (WordPress explainer site, "Research explainers on AI interpretability…", published ~Aug 2026) | **UNVERIFIED** (third-party explainer/SEO content; primary source is anthropic.com) |
| 5 | J-Space Cognition Suite exists as an open-source inference-time control layer packaged as a Skill; based on Anthropic's J-space research (self-described) | https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6 (repo + README + description) | **VERIFIED** (repo exists and says this about itself) |
| 6 | J-Space Cognition Suite is Anthropic's J-space, or mechanistically implements it | explainx.ai FAQ: "No… the name overlap is a coincidence worth flagging, not a connection" https://explainx.ai/blog/j-space-cognition-suite-deepseek-v4-pro-harness-august-2026 ; suite science ref (analogical use of the term) | **DISPROVEN** as equivalence; the suite borrows the name/vocabulary only |
| 7 | DeepSeek V4-Pro-0813 + J-Space beats Fable 5 "via a harness fix, not weight changes" | Report README (self-reported) https://github.com/Tiger3807861189/DeepSeek-V4-J-Space-Capability-Realization-Report ; X amplification posts (e.g., https://x.com/0x0SojalSec/status/2089418544312381462) | **UNVERIFIED** (self-reported single-run; explicitly labeled unverified by explainx.ai and nnets.ru) |
| 8 | Specific gains: Terminal-Bench 2.1 87.9→90.1; NL2Repo 61.5→73.4; Toolathlon 74.1→79.5; HLE-tools 67.7 vs Fable 63.0 | Report README §4.2; explainx.ai FAQ (same numbers, labeled self-reported) | **UNVERIFIED** (single-run, no CIs, no external reproduction) |
| 9 | The "before" numbers equal DeepSeek's official V4-Pro-0813 launch baselines (87.9 / 61.5) | explainx.ai FAQ (attributes to DeepSeek official launch); report table matches | **CORROBORATED** (two independent statements agree; primary launch page not directly scrapeable here — https://www.deepseek.com/en/news/ , https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro) |
| 10 | Efficiency gains 2.53× score/time, 2.21× score/token | Report README §4.5 | **UNVERIFIED** (single-run; scaling coefficients "intentionally omitted") |
| 11 | J-Space is a plugin/mode of DeepSeek Harness (dsh) | dsh README (no J-Space mention); GitHub issue search in deepseek-ai/deepseek-harness = 0 hits; suite README (Skill packaging); xiaobright/dsh-anchored-standard README ("…control layer packaged as a Skill") | **DISPROVEN** as official component; **VERIFIED** as third-party community skill/plugin layered on dsh (tagged `dsh-plugin` for discoverability) |
| 12 | "Capability-realization loss" and "chain-of-thought diode" are established/DeepSeek-official concepts | Report README (author's own terms; explicitly "不是 DeepSeek 官方给出的架构名称") | **UNVERIFIED** (author's engineering framing, not an official or peer-reviewed construct) |
| 13 | J-Space works "far far better" with DeepSeek than with any other model/harness | No controlled cross-model or cross-harness experiment exists; suite itself claims cross-model reproducibility (DeepSeek, Qwen, GLM, GPT, Claude) with no cross-model tables | **UNVERIFIED / NOT SUPPORTED** — no evidence for the superlative; contradicted by the suite's own model-agnostic framing |
| 14 | Independent reproduction of the benchmark claims exists | explainx.ai (none as of Aug 18, 2026); nnets.ru (no confirmation); V2EX anecdote (mixed: worse on one task, better on another) https://hk.v2ex.com/t/1234765 | **DISPROVEN** (no independent reproduction found; community anecdotes mixed) |
| 15 | DeepSeek V4-Pro-0813 and Claude Fable 5 exist and are current flagship models | https://arxiv.org/abs/2606.19348 ; https://www.anthropic.com/news/claude-fable-5-mythos-5 ; https://www.deepseek.com/en/news/v4-preview/ | **VERIFIED** (primary) |

---

## 6. Bottom-line verdict

**The claim "J-space operates far far better with DeepSeek than any other harness" does NOT hold as stated.** Confidence: **high (~95%)** that it is unverified/unsupported; I cannot certify the underlying effect is false (that would require running the controlled experiments myself), and I explicitly note the claim's core is *untested*, not *refuted by a counter-benchmark*.

Reasons:
1. **Category confusion.** "J-space" = Anthropic's measured internal workspace in **Claude** (not a harness, and silent about DeepSeek) ≠ "J-Space Cognition Suite" = a **community prompt/skill package** that borrows the name ≈ "DeepSeek V4 × J-Space report" = a **2-day-old self-reported benchmark document**. The claim only works by treating all three as one thing.
2. **No controlled comparison exists.** The only numbers compare DeepSeek+J-Space (suite-run, single-shot) against *vendor-published* scores from different methodologies. There is no J-Space run on any other model/harness, and the suite itself claims model-agnosticism — which cuts *against* DeepSeek-specificity.
3. **No independent verification.** explainx.ai and nnets.ru (both Aug 18, 2026) explicitly state the scores are unconfirmed; the report admits single-run status and lists its own falsification conditions; community field tests are anecdotal and mixed.
4. **Skeptic's summary:** the "before" numbers plausibly match DeepSeek's official baselines (cheap to verify), but every "after" number is the claimer's own, un-reproduced, with no error bars, published days ago. That is marketing-grade evidence, not measurement.

**What would change the grade:** (i) an independent third-party reproduction of the suite's on/off A/B on DeepSeek and at least one other model family under identical harness/task/tool conditions, ideally with multi-seed runs and CIs; (ii) DeepSeek or Anthropic commenting; (iii) the report's falsification conditions being tested (e.g., score/token and score/time gains without token/elapsed inflation). Until then, treat "J-Space > other harnesses with DeepSeek" as an unverified community claim with a plausible-sounding mechanism (harness engineering / "loop engineering" improving agent outcomes is a real, documented trend — that part is credible) but **zero verified DeepSeek-specific superiority**.

---

## Source index (all fetched this session)

Primary:
- https://transformer-circuits.pub/2026/workspace/index.html (Anthropic paper, Jul 6 2026; 0 "deepseek" mentions)
- https://www.anthropic.com/research/global-workspace
- https://github.com/anthropics/jacobian-lens
- https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6 (+ README, repo metadata, j-space/references/j-space-science.md)
- https://github.com/Tiger3807861189/DeepSeek-V4-J-Space-Capability-Realization-Report (+ README full text)
- https://github.com/deepseek-ai/deepseek-harness (README; issues search: 0 J-Space hits)
- https://github.com/xiaobright/dsh-anchored-standard (README)
- https://arxiv.org/abs/2606.19348 (DeepSeek-V4 preview paper)
- https://www.anthropic.com/news/claude-fable-5-mythos-5 ; https://www.anthropic.com/claude/fable

Secondary / commentary:
- https://explainx.ai/blog/j-space-cognition-suite-deepseek-v4-pro-harness-august-2026 (skeptical, labels claims unverified)
- https://explainx.ai/blog/anthropic-j-space-global-workspace-claude-interpretability-2026 ; https://explainx.ai/blog/what-is-j-lens-jacobian-lens-claude-interpretability-2026
- https://nnets.ru/news/j-space-cognition-suite-ne-podnimaet-modeli-do-top-urovnja-chto-ne-tak-s-gromkim-skillom (skeptical, RU)
- https://huggingface.co/blog/dlouapre/j-space (independent technical review + open-model reproduction of J-lens)
- https://www.technologyreview.com/2026/07/09/1140293/anthropic-found-a-hidden-space-where-claude-puzzles-over-concepts/
- https://venturebeat.com/technology/anthropics-new-j-lens-reveals-a-silent-workspace-inside-claude-that-mirrors-a-leading-theory-of-consciousness
- https://www.forbes.com/sites/johnwerner/2026/07/12/anthropic-illuminates-llm-j-space-with-j-lens/
- https://www.lesswrong.com/posts/zFJ3ZdQwrTWE9jT5S/a-review-of-anthropic-s-global-workspace-paper
- https://jspace.com/ (third-party explainer site — NOT primary)
- https://hk.v2ex.com/t/1234765 (community test: mixed results)
- https://x.com/0x0SojalSec/status/2089418544312381462 ; https://x.com/geesehowardt7/status/2089159449793712584 (hype amplification)
- https://dshdocs.com/ (community dsh handbook)
- https://www.remio.ai/post/anthropic-deepseek-rivalry-tightens-as-v4-pro-0813-nears-claude-fable-5 (headline only; body JS-blocked)
