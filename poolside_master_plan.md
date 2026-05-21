# CIGuard — Fine-tuning Laguna XS.2 for Supply Chain Security Reasoning
### Poolside Model Research Hackathon · London · 2-Day Plan

> **Model:** Laguna XS.2 — 33B total / 3B active MoE, Apache 2.0  
> **Platform:** Prime Intellect Lab — `verifiers` library + hosted GRPO training  
> **Submission criteria:** 1.1 Fine-tuning/post-training + 1.4 Reusable RL environment (primary) → optionally extend to 1.5 Agentic client  
> **Your background:** Python, Classic ML, Quant/Finance — no prior RL/SFT experience required

---

## 1. The Problem — What Actually Happened

On May 11, 2026, the TanStack supply chain attack compromised 373 package versions across 169 npm packages with over 12 million weekly downloads. The attacker did not find a zero-day. They read the workflow files, found a logical architecture flaw, and walked through it.

The attack chain:

```
1. Fork TanStack/router under a fake identity
2. Submit a PR → triggers pull_request_target workflow
   └─ This runs with WRITE permissions even for fork PRs
3. PR code poisons the shared GitHub Actions pnpm cache
4. Force-push back to main HEAD → PR now shows 0 file changes
5. Close PR, delete branch → no evidence visible in repo
6. Legitimate release job restores poisoned cache hours later
7. Malware in cache extracts OIDC token from runner memory
8. Uses TanStack's own trusted CI identity to publish 84 malicious versions
9. Worm self-replicates: steals maintainer tokens, infects their other packages
10. 373 packages compromised. 400+ GitHub repos created as credential dead drops.
```

The same attacker group (TeamPCP) ran this same class of attack against Aqua Security's Trivy scanner (March 2026), the Bitwarden CLI (April 2026), and Axios (March 2026 — DPRK-linked). Each wave was more sophisticated than the last. The worm is now open-source.

Every existing security tool passed this. Not because they failed — because they worked exactly as designed. The attack was architecturally valid.

---

## 2. The Hard Question — Does This Generalise?

**Raised and answered honestly, because judges will ask.**

The concern: if you train on TanStack's specific `bundle-size.yml`, you've built a very expensive regex. A model that doesn't generalise has no value.

The answer is that supply chain attacks are not random. There is a finite, well-documented taxonomy of attack classes. The specific implementation varies; the underlying pattern does not.

The four attack classes that cover ~95% of real-world incidents:

| Class | Signal lives in | Real examples |
|---|---|---|
| Pipeline privilege misconfiguration | Workflow YAML — trigger + permission + mutable state combinations | TanStack (May 2026), Nx (Aug 2025), tj-actions (Mar 2025) |
| Malicious lifecycle scripts | Package install hooks — what they do vs what the package claims to do | Shai-Hulud waves 1–4, Axios (plain-crypto-js), all typosquats |
| Credential harvesting + worm propagation | Runtime behaviour — env var access patterns, network calls, self-publishing | Mini Shai-Hulud, Sep 2025 wave (500+ packages) |
| Registry metadata anomalies | Package age, author history, name distance, version jumps | Dependency confusion, brandjacking, account takeover |

The training signal is not "flag anything that looks like TanStack." It is "understand what makes `pull_request_target` + cache + fork checkout dangerous as a *combination*, regardless of what the workflow is called or what project it belongs to."

That generalises. The model learns the *class*, not the *instance*.

**The ceiling — be honest about this with judges:**

You are not training a model to catch novel zero-days. You are training a model to catch novel *implementations* of known attack classes. Those are different things. For genuinely novel attack vectors (something architecturally new), no model trained on historical data will catch it.

What you beat is the 72-hour window between a novel attack occurring and the first CVE entry appearing. During that window, every static tool is blind. Your model reasons from class knowledge, not from a database entry.

---

## 3. The Value Add — Why This Isn't Just Another Snyk

This is the most important question to answer cleanly. Here is the honest comparison.

### What existing tools do well

**SonarQube, SemGrep** — static analysis on code structure. Rule-based. Fast. Excellent at known patterns. Cannot reason across files or reason about intent.

**Snyk, Socket.dev** — vulnerability database lookup + some behavioural heuristics. Snyk has millions of CVEs. Socket.dev scans npm publishes in real time. Both are reactive: something has to happen first, get reported, get a CVE entry, then they catch it.

**OSV.dev / OpenSSF Malicious Packages** — the ground truth database. Community-maintained. Everything eventually ends up here. But "eventually" means 24–72 hours after the attack.

**SLSA provenance attestations** — cryptographic verification that a package was built from a trusted source. The TanStack attack produced the first malicious packages with valid SLSA Build Level 3 attestations. The attackers *used* TanStack's own trusted identity. SLSA passed. The package was malicious.

### What none of them do

**1. Reason across the attack chain simultaneously.**

Every tool scans one thing at a time. Snyk scans a `package.json`. SonarQube scans code. Neither can see: "this workflow misconfiguration enables cache poisoning, which enables OIDC token theft, which enables trusted publishing of malicious packages." That chain is invisible to single-layer scanners. A language model with a 131K context window can ingest the workflow, the package manifest, and the metadata together and reason about what they enable in combination.

**2. Explain the why, not just the what.**

SonarQube: `Rule CWE-829: Inclusion of Functionality from Untrusted Control Sphere`  
Your model: `The pull_request_target trigger at line 3 runs with write permissions for fork PRs. The checkout of the fork ref at line 14 executes untrusted code in that privileged context. The cache action at line 22 uses a branch-inclusive key shared between fork and upstream — this is the poisoning vector. Here is the corrected workflow.`

These are different products. One tells you something is wrong. The other tells you why, what it enables, and how to fix it.

**3. Catch the 72-hour window.**

In 2025, 99% of malicious npm packages were officially verified within 72 hours. During those 72 hours, Snyk sees nothing. Your model, trained on the *class* of attack, doesn't need a database entry. It reasons from the pattern.

**4. Run on private repos without sending code to a third party.**

Laguna XS.2 runs on a single GPU. On-premise. Your CI pipeline never sends source code to Snyk's servers. For financial services, healthcare, and defence — this is not optional.

### What you do NOT beat existing tools on

- Known CVE lookup speed and breadth — Snyk's database of millions vs your 750 training examples
- Real-time registry monitoring — Socket.dev watches every npm publish; you don't
- Language breadth — SonarQube covers 30+ languages with years of rules

**The honest pitch:** This is the reasoning layer that sits above existing tools. Not a replacement. The layer that catches what rule-based systems explicitly cannot: novel implementations of known classes, chained attacks across trust boundaries, and behavioural intent that only becomes visible when you reason across the full context.

---

## 4. The Data Strategy — Precise, Not Random

This is the most important thing to get right before the hackathon. Bad data produces a useless model. Here is exactly what you are collecting, from where, and why each piece earns its place.

### The core principle

You are building **contrastive pairs** — not a collection of "suspicious-looking code." For every dangerous example, you need a structurally similar but safe counterpart. This is what separates a useful model from an expensive false-positive machine.

The canonical hard case: `esbuild`'s postinstall script downloads platform-specific binaries from a CDN. A typosquatting package's postinstall script downloads a binary from `attacker.com`. Both patterns look identical to a naive rule. The model must learn what distinguishes them: `esbuild` downloads to a pinned hash from a known CDN and verifies integrity. The malicious package downloads from an unverifiable endpoint and passes credentials in the query string.

That difference is the training signal. Not "network call = bad." "Unverifiable network call with credential-shaped data = bad."

### Source 1 — OpenSSF Malicious Packages (your positive class ground truth)

```
https://github.com/ossf/malicious-packages
```

This is the authoritative open-source database of confirmed malicious packages, maintained by the Linux Foundation's OpenSSF. Every entry is a real attack, confirmed, with the package name, affected versions, ecosystem, and a human-written description of what the malicious code does.

**What to pull:**
- All `MAL-*` prefixed entries for `npm` ecosystem — ~400+ confirmed malicious packages
- All `MAL-*` entries for `PyPI` ecosystem — ~200+ entries
- Each entry includes: package name, malicious version(s), description of payload, date

**Why this source and not random scraping:** Every example here has been human-confirmed as malicious by the security community. You are not labelling based on heuristics — you are using verified ground truth. Your positive class is clean.

**API access:**
```bash
# Fetch a specific malicious package record
curl -s "https://api.osv.dev/v1/vulns/MAL-2025-6812" | jq .

# List all npm malicious packages
curl -X POST "https://api.osv.dev/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"package": {"ecosystem": "npm"}, "query_type": "malicious"}'

# The GitHub repo itself — clone and parse the JSON files directly
git clone https://github.com/ossf/malicious-packages
# Files are at: osv/malicious/npm/<package-name>/MAL-XXXX-XXXX.json
```

**What each OSV record gives you:**
```json
{
  "id": "MAL-2026-2306",
  "package": {"name": "plain-crypto-js", "ecosystem": "npm"},
  "summary": "Malicious code in plain-crypto-js",
  "details": "The npm package 'axios' was compromised and a malicious dependency 
              was added called 'plain-crypto-js'. The malicious code appears to 
              install a remote access trojan.",
  "affected": [{"versions": ["4.2.1"]}]
}
```

From this, you fetch the actual package contents from the npm registry (or the Internet Archive if yanked) to get the `package.json` and install scripts.

**Target from this source: 300 labelled dangerous examples (npm + PyPI combined)**

### Source 2 — GitHub Actions workflow files (pipeline class)

You need two kinds: confirmed-attacked repos, and structurally similar but well-maintained repos.

**Confirmed-attacked repos (your hardest positive examples):**

These workflows are public, archived, and documented in security write-ups:
```
TanStack/router    → .github/workflows/bundle-size.yml  (the actual attack workflow)
nicolo-ribaudo     → tj-actions/changed-files compromise (Mar 2025)
Nx                 → Aug 2025 attack workflow
reviewdog repos    → affected in the tj-actions wave
```

Fetch directly from GitHub — these repos exist and the workflows are public. The attack versions are documented in security blogs if the current repo has been patched.

**Safe repos using the same dangerous-looking patterns correctly (your hard negative examples):**

These orgs use `pull_request_target`, cache actions, and id-token:write — but correctly scoped:
```
github.com/github/docs              → Large, well-audited workflows
github.com/openssf/scorecard        → Security-focused, correct usage
github.com/actions/runner           → GitHub's own runner — canonical correct patterns
github.com/microsoft/vscode         → Enterprise-grade workflow hygiene
```

**GitHub Search API scrape (bulk collection):**
```python
# Three targeted searches — not random
queries = [
    # Dangerous pattern — positive candidates
    "pull_request_target path:.github/workflows extension:yml",
    # Cache with permission — positive candidates  
    "id-token write path:.github/workflows extension:yml",
    # Safe pattern — negative candidates
    "pull_request path:.github/workflows NOT pull_request_target extension:yml",
]
# Rate limit: 30 req/min authenticated
# Target: 300 workflow files total (100 per query)
```

**What you label and how:** For each workflow file, you run it through a rule-based pre-classifier to get a candidate label, then spot-check 20% manually. The rule-based classifier is not the model — it's just scaffolding to get initial labels efficiently.

```python
def candidate_label(yaml_content):
    """Fast rule-based pre-classifier. Not the model. Just for labelling efficiency."""
    has_prt = "pull_request_target" in yaml_content
    has_fork_checkout = "head.sha" in yaml_content or "pull_request.head" in yaml_content
    has_cache = "actions/cache" in yaml_content
    has_oidc = "id-token" in yaml_content and "write" in yaml_content
    has_secret_in_env = bool(re.search(r'env:.*secrets\.', yaml_content, re.DOTALL))
    
    if has_prt and has_fork_checkout and has_cache:
        return "CRITICAL", "pipeline_privilege"  # exact TanStack pattern
    elif has_prt and (has_oidc or has_secret_in_env):
        return "HIGH", "pipeline_privilege"
    elif has_prt:
        return "MEDIUM", "pipeline_privilege"    # trigger alone, no compounding factors
    else:
        return "SAFE", "SAFE"
```

**Target from this source: 250 labelled workflow examples**

### Source 3 — npm registry metadata (metadata anomaly class)

This is where your quant background is directly applicable. You are building a feature matrix, not scraping random packages.

**The features that matter (and why):**

```python
metadata_features = {
    "days_since_first_publish": int,      # <7 days + high downloads = confusion attack
    "weekly_downloads": int,              # anomalously high for age = confusion
    "author_total_packages": int,         # 1-2 packages, all recent = throwaway account
    "author_account_age_days": int,       # new account + popular package = ATO or fake
    "name_edit_distance_nearest_top1000": int,  # ≤2 = typosquatting candidate
    "version_jump_magnitude": float,      # 1.0.0 → 9.9.9 = confusion attack
    "has_postinstall": bool,
    "postinstall_calls_network": bool,    # heuristic from script static analysis
    "postinstall_accesses_env_vars": bool,
    "dependency_count_delta": int,        # sudden new dep added = injection (Axios pattern)
}
```

No single feature is a signal. The model learns combinations. A 2-day-old package with 800k weekly downloads and a network-calling postinstall and an account with 1 other package — that's the Axios `plain-crypto-js` pattern exactly.

**Safe packages (your negative class):**
```bash
# Top 500 npm packages by weekly downloads, age > 180 days
curl "https://registry.npmjs.org/-/v1/search?text=not:unstable&size=250&from=0"
# These are definitively safe — established, audited, community-maintained
# Extract their metadata features — this gives you what "normal" looks like
```

**Malicious packages (your positive class):**
Already captured from Source 1 (OSV). For each MAL-* package, fetch its npm registry metadata at the time of the attack (use the Wayback Machine CDX API if the package has been yanked).

**Target from this source: 200 metadata examples (100 safe, 100 dangerous)**

### Dataset summary

| Source | Type | Safe | Dangerous | Total |
|---|---|---|---|---|
| OSV Malicious Packages → npm registry | Lifecycle scripts | 100 | 150 | 250 |
| OSV Malicious Packages → npm registry | Metadata features | 100 | 100 | 200 |
| GitHub API | Workflow YAML | 150 | 100 | 250 |
| **Total** | | **350** | **350** | **700** |

Balanced 50/50 split between safe and dangerous. This is intentional — an unbalanced dataset produces a model that learns to always say "SAFE" and scores 50% accuracy without learning anything.

Split: 560 train (80%) / 140 eval (20%). The eval set is held out completely — never seen during training. It is your benchmark.

### The labelled example format

Every example — regardless of source — follows this exact structure:

```json
{
  "input": {
    "type": "workflow | package_lifecycle | package_metadata",
    "content": "<full YAML, package.json, or metadata JSON as string>",
    "context": "GitHub Actions workflow from a public npm package repository."
  },
  "output": {
    "risk_level": "CRITICAL | HIGH | MEDIUM | LOW | SAFE",
    "attack_class": "pipeline_privilege | malicious_lifecycle | metadata_anomaly | SAFE",
    "reasoning": [
      "Step 1: [specific observation about a specific line or field]",
      "Step 2: [what that enables or implies]",
      "Step 3: [how the combination creates the risk]"
    ],
    "dangerous_elements": ["line 3: pull_request_target trigger", "line 14: fork ref checkout"],
    "fix": "<corrected version of the content, or null if SAFE>"
  }
}
```

The reasoning chain is what you are training the model to produce. Each step must cite something specific. "This is dangerous" is not a step. "The `pull_request_target` trigger at line 3 runs with write permissions for fork PRs" is a step.

---

## 5. The RL Environment — How Prime Intellect Lab Uses Your Data

### What the verifiers library does

Prime Intellect's `verifiers` library is the interface between your dataset + reward function and their GRPO training infrastructure. You write three things: `get_prompt()`, `score()`, and the dataset loader. Everything else — GPU allocation, distributed training, LoRA adapter management — is handled by Lab.

```python
# environments/supply_chain_sec/supply_chain_sec.py

import verifiers as vf
import json, re

class SupplyChainSecEnv(vf.Environment):

    def get_prompt(self, example):
        return f"""You are a supply chain security auditor specialising in 
GitHub Actions pipelines and npm/PyPI package ecosystems.

Analyse the following and respond with exactly this structure:
RISK_LEVEL: <CRITICAL|HIGH|MEDIUM|LOW|SAFE>
ATTACK_CLASS: <pipeline_privilege|malicious_lifecycle|metadata_anomaly|SAFE>
REASONING:
  Step 1: <specific observation citing exact lines or fields>
  Step 2: <what that enables>
  Step 3: <how the combination creates risk, or why it is safe>
FIX: <corrected version, or "No fix needed" if SAFE>

Input type: {example['input']['type']}
{example['input']['content']}"""

    def score(self, model_output, ground_truth):
        """
        Fully verifiable reward — no human review needed.
        The model trains against this signal at scale.
        """
        score = 0.0
        parsed = self._parse(model_output)

        # 40 points: risk level correct
        if parsed.get('risk_level') == ground_truth['risk_level']:
            score += 0.40
        elif self._adjacent(parsed.get('risk_level'), ground_truth['risk_level']):
            score += 0.20  # one level off = partial credit

        # 30 points: attack class correct
        if parsed.get('attack_class') == ground_truth['attack_class']:
            score += 0.30

        # 30 points: key signals mentioned in reasoning
        # These are the terms the model MUST reference for each class
        key_signals = {
            'pipeline_privilege':  ['pull_request_target', 'fork', 'cache', 'permission', 'OIDC'],
            'malicious_lifecycle': ['postinstall', 'network', 'environment variable', 'detach'],
            'metadata_anomaly':    ['publish date', 'download', 'author', 'version'],
            'SAFE':                ['no dangerous', 'safe'],
        }
        signals = key_signals.get(ground_truth['attack_class'], [])
        if signals:
            found = sum(1 for s in signals if s.lower() in model_output.lower())
            score += 0.30 * (found / len(signals))

        return score

    def _adjacent(self, a, b):
        order = ['SAFE', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        if a not in order or b not in order:
            return False
        return abs(order.index(a) - order.index(b)) == 1
```

### Training config

```toml
# configs/rl/laguna-supply-chain.toml
model = "poolside/Laguna-XS.2"
max_steps = 200
batch_size = 256
rollouts_per_example = 8   # model generates 8 responses per prompt, best ones reinforce

[sampling]
max_tokens = 1024
temperature = 0.7

[[env]]
id = "yourusername/supply-chain-sec-env"
```

---

## 6. Plan A vs Plan B — Which One to Execute

### Plan A: Research Contribution (Criteria 1.1 + 1.4)

**Primary output:** Fine-tuned Laguna XS.2 adapter + reusable RL environment on Prime Intellect Environments Hub

**What judges see:** Novel training environment, reproducible benchmark, generalisable across npm/PyPI/GitHub Actions, clean before/after accuracy delta

**Risk level:** Low. Data pipeline is your comfort zone. Training runs on Lab infrastructure overnight. Day 2 is analysis and submission.

**Fits criteria 1.4 because:** Your `supply-chain-sec-env` environment is published to the Hub and usable by any team training any model on supply chain security reasoning. It outlasts the hackathon.

---

### Plan B: Agentic Client (Criteria 1.1 + 1.5)

**Plan B is Plan A + a working CLI agent wrapped around the fine-tuned model.**

```bash
ciguard scan https://github.com/any-org/any-repo
```

The agent clones the repo, discovers workflow and package files, calls your fine-tuned Laguna adapter for each, and outputs a structured risk report. Optionally opens a PR with fixes (stretch goal — only if Day 2 goes ahead of schedule).

**What judges see:** End-to-end product with a live demo. Scans a real repo, returns real results, explainable output.

**Risk level:** Medium. The agent wrapper is 200 lines of Python. The risk is time — if data pipeline or training hits friction, you won't have time to build and test the agent.

**The agent structure:**
```
ciguard/
├── agent.py          # clone → discover → analyse → report
├── tools/
│   ├── scanner.py    # git clone, file discovery
│   ├── client.py     # calls Laguna adapter API (OpenAI-compatible)
│   └── report.py     # formats output, colour codes by risk
└── cli.py            # `ciguard scan <url>`
```

---

### Decision matrix

| | Plan A | Plan B |
|---|---|---|
| Fits criteria | 1.1 + 1.4 ✅ | 1.1 + 1.5 ✅ |
| Can finish in 2 days | ✅ Confident | ⚠️ Tight |
| Demo quality | Benchmark numbers + eval run | Live scan of real repo |
| If training fails | Still have dataset + environment | Same, plus agent does nothing |
| Judge conversation | "Novel environment, generalisable" | "Show me it running" |
| Recommendation | **Start here** | **Add on Day 2 if ahead of schedule** |

**The move:** Execute Plan A. At 14:00 on Day 2, if you're ahead of schedule, spend 2 hours building the agent wrapper. Submit Plan A as primary. The agent is a bonus that makes the demo better.

---

## 7. Knowledge You Need — Specific, Not General

### Before the hackathon (do in this order)

**1. The verifiers library — 3 hours, non-negotiable**
```bash
pip install verifiers
prime env install primeintellect/alphabet-sort
```
Read the alphabet-sort environment source. It is 80 lines. Understand every line. Then modify the `score()` function and run it again. If you understand that file, you understand 80% of what you need to build.

URL: `github.com/PrimeIntellect-ai/verifiers`

**2. What GRPO is — 1 hour**
GRPO = Group Relative Policy Optimization. The model generates 8 responses to the same prompt. Your `score()` function scores each one. The model learns to produce more responses like the high-scoring ones. You do not implement this. Lab runs it. You need to understand it well enough to know why your reward function is or isn't working.

Read: The TinyZero README on GitHub — `github.com/Jiayi-Pan/TinyZero`. 200 lines of GRPO, heavily commented.

**3. What LoRA is — 2 hours**
LoRA adds small adapter matrices (a few million parameters) to the frozen 33B model. You are not retraining Laguna. You are adding a thin layer that steers its outputs toward security reasoning. Lab manages the adapter. You need to understand what it is to explain it to judges.

Read: The HuggingFace PEFT docs introduction page. Then the original LoRA paper abstract and Figure 1 only.

**4. The OSV database — 30 mins**
Browse `osv.dev`, filter by ecosystem npm, look at 10 MAL-* entries. Read the descriptions. Notice what makes each one malicious. This is your training data — you should know what it looks like before you write the scraper.

**5. Karpathy's Neural Networks: Zero to Hero — ongoing, after the hackathon**
`youtube.com/playlist?list=PLXYLzZ3XzIbi4lL43O6fIU_ojuZwBO6vi`
Watch videos 1 and 3 (Micrograd, GPT from scratch) before the hackathon if you have time. This builds the intuition for why training works. Not required to execute the plan. Required to go deeper afterward.

### What to not waste time on before the hackathon
- PyTorch internals — Lab abstracts this entirely
- CUDA/GPU setup — Lab provides the compute
- The mathematics of backpropagation — not needed to configure a training run
- Reading papers — read READMEs and source code instead

---

## 8. Where Claude Code Accelerates You

Use Claude Code (the terminal agent, not claude.ai) for these specific tasks. It can run commands, write files, and iterate on code without you switching context.

**Data pipeline — Day 1 morning:**
```
"Write a Python script that fetches all MAL-* npm entries from the OSV GitHub repo 
at github.com/ossf/malicious-packages, extracts package name + description + affected 
versions from each JSON file, then fetches the full npm registry metadata for each 
package at https://registry.npmjs.org/<name>. Save each as a JSON file in ./raw/osv/.
Handle 404s (package yanked) gracefully. Target: all npm MAL entries."
```

**Labelling pipeline — Day 1 morning:**
```
"For each JSON file in ./raw/osv/, generate a labelled training example in this format:
[paste your JSON schema]. The input.content should be the package.json scripts field 
and any install scripts found in the npm metadata. The output should be generated 
by applying these labelling rules: [paste your rule-based classifier logic].
Save to ./dataset/labelled/train.jsonl, one JSON object per line."
```

**Verifiers environment — Day 1 afternoon:**
```
"Using the Prime Intellect verifiers library, create a complete environment module 
at ./environments/supply_chain_sec/. Here is my score() function pseudocode: 
[paste]. Here is my dataset format: [paste]. Generate supply_chain_sec.py, 
pyproject.toml with verifiers as dependency, and README.md."
```

**Eval harness — Day 1 evening:**
```
"Write eval/benchmark.py that loads ./dataset/labelled/eval.jsonl, calls an 
OpenAI-compatible API at the endpoint I specify, parses each response using 
this schema: [paste], scores against ground truth using this logic: [paste score()],
and outputs precision/recall/F1 per attack class plus overall accuracy to 
benchmark_results.json. Add a --verbose flag that prints each example and score."
```

**HuggingFace model card — Day 2:**
```
"Write a HuggingFace model card README.md for a fine-tuned LoRA adapter of 
Laguna XS.2, trained for supply chain security reasoning. Include: what it does, 
how it was trained (GRPO via Prime Intellect Lab, verifiers library, 700-example 
dataset from OSV + GitHub Actions), benchmark results [paste your numbers], 
example usage, limitations (does not catch novel zero-days, not a Snyk replacement),
and the attack classes it covers. Follow HuggingFace model card format."
```

---

## 9. Day-by-Day Execution

### Pre-hackathon (do before you arrive)

```bash
# Set up accounts
# 1. prime.ai — create account, verify it works
# 2. huggingface.co — create account, get write token
# 3. GitHub — ensure you have a personal access token with repo:read scope

# Install tools
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install prime
prime login

# Run the hello-world environment — verify everything works
prime env install primeintellect/alphabet-sort
# Read the source. Understand every line.

# Scrape 30 OSV entries as a dry run
# Fix any auth/rate-limit issues before the event
```

---

### Day 1

**09:00 — Environment setup (30 mins)**
```bash
prime env workspace init ciguard-hackathon
cd ciguard-hackathon
uv add verifiers requests tqdm huggingface_hub
prime env init supply-chain-sec
```
Verify: `prime env test supply-chain-sec` runs without error on the default template.

**09:30 — Data scraping, 3 parallel jobs (2.5 hours)**

Open three terminals. Run simultaneously.

*Terminal 1 — OSV malicious packages:*
```bash
# Clone OSV repo and parse all npm MAL entries
# Use Claude Code to write the scraper
# Target: 300 confirmed malicious package entries
# Output: ./raw/osv/npm/*.json
```

*Terminal 2 — GitHub Actions workflows (dangerous candidates):*
```bash
# GitHub Search API: "pull_request_target path:.github/workflows extension:yml"
# Also fetch TanStack, Nx, tj-actions attack workflows directly by URL
# Target: 150 workflow files
# Output: ./raw/workflows/dangerous_candidates/*.yml
```

*Terminal 3 — Safe baselines:*
```bash
# npm registry top 500 (safe packages)
# GitHub workflows from large audited orgs (github/docs, actions/runner, etc.)
# Target: 200 safe examples across both types
# Output: ./raw/workflows/safe/*.yml, ./raw/npm/safe/*.json
```

**12:00 — Labelling pipeline (2 hours)**

Use Claude Code to apply your labelling schema to each raw file in batches of 50. Spot-check every 10th label manually. Fix systematic errors (the rule-based pre-classifier will have some). Output: `./dataset/labelled/train.jsonl` (560 examples) and `./dataset/labelled/eval.jsonl` (140 examples, held out).

**14:00 — Build and test the verifiers environment (2 hours)**

Fill in `supply_chain_sec.py` using Claude Code. Run `prime env test supply-chain-sec` after every significant change. The test command runs a handful of examples through `get_prompt()` and `score()` and shows you the output — it will immediately reveal if your reward function is broken.

Common issues to watch for:
- `score()` returning the same value for everything (reward is too coarse)
- `get_prompt()` producing prompts too long for the model's context
- Dataset loading failing silently (check your JSONL is valid with `python -m json.tool < train.jsonl`)

**16:00 — Run baseline benchmark (30 mins)**

Before any fine-tuning, run your eval harness against the base Laguna XS.2:
```bash
python eval/benchmark.py \
  --model poolside/Laguna-XS.2 \
  --endpoint <lab-endpoint> \
  --data ./dataset/labelled/eval.jsonl \
  --output results_baseline.json
```
Record these numbers. They are your "before." You cannot show improvement without them.

**16:30 — Upload environment to Hub, start training run (30 mins)**

```bash
prime env upload supply-chain-sec
```

Go to Prime Intellect Lab UI:
- New run → your environment → Laguna XS.2
- Paste `laguna-supply-chain.toml`
- Start run

Training will run overnight. You do not need to watch it.

**17:00 — End of Day 1 checkpoint**

You should have:
- ✅ 700-example labelled dataset (train + eval split)
- ✅ Verifiers environment uploaded to Hub
- ✅ Baseline benchmark numbers recorded
- ✅ Training run started on Lab

If any of these is missing, identify what's blocking it and fix it before leaving.

---

### Day 2

**09:00 — Check training run (30 mins)**

Log into Lab. Check the loss curve.

If loss is decreasing: good. Let it run.  
If loss plateaued immediately: your reward function is too easy. Common cause — risk_level alone gives 0.4 reward so the model learns to output any risk level and scores 0.4 always without learning. Fix: reduce the risk_level component weight, increase the reasoning signal weight.  
If loss is NaN: learning rate too high, or a bug in your score() returning values outside [0,1].

**09:30 — Run benchmark on fine-tuned adapter (1 hour)**

When the run completes (or at a checkpoint), Lab deploys the LoRA adapter automatically. Run your eval harness:
```bash
python eval/benchmark.py \
  --model fine-tuned \
  --endpoint <lab-adapter-endpoint> \
  --data ./dataset/labelled/eval.jsonl \
  --output results_finetuned.json

python eval/compare.py \
  --before results_baseline.json \
  --after results_finetuned.json
```

Output format you want for judges:
```
                    Baseline    Fine-tuned    Delta
Overall accuracy      41%          73%        +32pp
Pipeline privilege    38%          81%        +43pp
Malicious lifecycle   44%          69%        +25pp
Metadata anomaly      39%          68%        +29pp
False positive rate   31%          12%        -19pp
```

**10:30 — HuggingFace submission (1.5 hours)**

Three uploads:
```bash
# 1. Dataset
huggingface-cli upload yourusername/supply-chain-sec-dataset \
  ./dataset/labelled/ --repo-type dataset

# 2. Model card (adapter weights are served by Lab — link to them)
# Write README.md with Claude Code, paste in your benchmark numbers

# 3. Environment README links back to Prime Intellect Hub
```

**12:00 — Prepare for judge questions (1 hour)**

Questions you will definitely get, and your answers:

*"How is this different from Snyk?"*  
Snyk is a database lookup — it catches known CVEs after they're reported. This model reasons about behavioural intent and attack class patterns. It catches novel implementations of known classes before they get a CVE entry. Not a replacement — a reasoning layer above existing tools.

*"Does this generalise beyond TanStack?"*  
Yes. The training data covers 300+ confirmed malicious packages from OSV across 4 attack classes spanning npm and PyPI, plus 250 GitHub Actions workflows. The model learns the class pattern, not the specific instance.

*"What's your false positive rate?"*  
Show your benchmark. A high false positive rate (flagging safe things as dangerous) is the failure mode for security tools. This is why you built contrastive pairs — structurally similar safe and dangerous examples.

*"What would it take to catch a novel zero-day?"*  
Honest answer: this model cannot. No model trained on historical data catches truly novel attack vectors. What it catches is novel implementations of known classes within the 72-hour window before a CVE is filed.

**13:00 — If ahead of schedule: build Plan B agent wrapper (2 hours)**

```bash
mkdir ciguard && cd ciguard
# Use Claude Code to write agent.py, tools/scanner.py, tools/client.py, cli.py
pip install rich  # terminal colour coding
```

Test on three repos with known outcomes:
1. `github.com/tanstack/router` → expect CRITICAL on bundle-size.yml
2. `github.com/facebook/react` → expect mostly SAFE
3. Any small repo with a safe but complex workflow → expect SAFE with explanation

**14:30 — Final submission**

Push to GitHub. Upload to the HuggingFace org Poolside has set up for the event. Your submission package:

1. `hub.primeintellect.ai/yourusername/supply-chain-sec-env` — the reusable RL environment
2. `huggingface.co/yourusername/laguna-xs2-supply-chain-adapter` — the fine-tuned adapter
3. `huggingface.co/yourusername/supply-chain-sec-dataset` — the labelled dataset
4. `github.com/yourusername/ciguard-hackathon` — all code

**15:00 — Demo prep (1 hour)**

One terminal command. That is your demo.
```bash
python eval/benchmark.py \
  --model fine-tuned \
  --input examples/tanstack-bundle-size.yml \
  --verbose
```

Output in 3 seconds:
```
INPUT: workflow (bundle-size.yml)
RISK LEVEL: CRITICAL  ✓
ATTACK CLASS: pipeline_privilege  ✓
REASONING:
  Step 1: pull_request_target trigger at line 3 runs with write permissions
          for fork PRs — untrusted code executes in a privileged context.
  Step 2: Checkout of fork ref at line 14 executes the PR author's code
          in that privileged context.
  Step 3: actions/cache at line 22 uses a branch-inclusive key shared
          between fork and upstream — this is the cache poisoning vector.
SCORE: 1.0
```

Then show the before/after benchmark table. That is the entire demo.

---

## 10. One-Line Summary

You are fine-tuning Laguna XS.2 to reason about *why* a workflow or package is dangerous — not to match it against a known-bad list. The RL environment you build is reusable by anyone. The fine-tuned adapter is a new capability Laguna did not have. The benchmark shows the before/after delta. That is a complete, defensible, generalisable research submission.
