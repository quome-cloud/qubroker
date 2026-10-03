<div align="center">

<img src="assets/qubroker-logo.svg" alt="qubroker" width="520">

### A fail-closed safety broker for AI agents that actuate ventilators, infusion pumps, and monitors

![built with](https://img.shields.io/badge/built_with-Rust-DEA584?logo=rust&logoColor=white)
![layer](https://img.shields.io/badge/layer-device-7c3aed)
![HAARF](https://img.shields.io/badge/HAARF-C8.3/8.6/3.1-0ea5e9)
![paper](https://img.shields.io/badge/paper-preprint-2563eb)
![status](https://img.shields.io/badge/status-research_prototype-orange)
![license](https://img.shields.io/badge/license-Apache_2.0-3FB950)
[![dataset](https://img.shields.io/badge/🤗_dataset-Quome%2Fdevicebench-FFD21E)](https://huggingface.co/datasets/Quome/devicebench)

[**Quickstart**](#quickstart) · [How it works](#how-it-works) · [Reproduce](#reproduce-the-experiments) · [Results](#headline-results) · [Paper](papers/014-device-broker/main.pdf) · [Dataset](https://huggingface.co/datasets/Quome/devicebench) · [Cite](#cite)

</div>

---

When an AI agent actuates a ventilator, infusion pump, or cardiac monitor, a wrong action is immediate physical harm, and a compliant model under clinical pressure will set whatever value it is told to. The device layer sits on the qfire actuation path after identity (quorum) and policy (quwarden): every DeviceCommand is checked against a version-pinned table of safe ranges, interlocks, and alarm parameters (devices.json, compiled into the binary), life-critical actuation always requires a human confirmation via the qutriage escalation transport, a broker-local fail-safe controller drives the device to its documented safe state on communication loss, and a run-length performance monitor flags sustained degradation. Driving 216 scenarios through a live llama3.1:8b agent, the unguarded agent puts the device into a physically unsafe state in 53.7% of cases; the broker reduces this to 0.0% (95% CI upper bound 1.7%; McNemar chi-squared 114.0) while preserving 94.4% of legitimate actions, and adds 0.05 us per command.

`qubroker` is **a module of the QUOKKAGUARD program**: one Rust security gateway (`qfire`) that sits in front of any OpenAI-compatible model endpoint and decides **ALLOW ▸ forward · BLOCK ▸ refuse · ESCALATE ▸ human review** for every request and response. Each module adds exactly one enforcement layer to that gateway plus one adversarial dataset and one paper. This repository is a self-contained snapshot of the gateway with **this layer** (`src/device/`, on the *request* path, HAARF control C8.3/8.6/3.1), its dataset (**DeviceBench**), the experiment harness, and the paper.

> **Needs a local model for some experiments.** Live runs go through [Ollama](https://ollama.com) on the OpenAI-compatible endpoint; no paid API keys are used anywhere in this repo.

## How it works

- **Version-pinned invariants**: each device class carries safe ranges, interlocks (e.g. peep_cmh2o < pip_cmh2o), alarm parameters, and a documented safe state in a single committed devices.json (version 014-devices-v1) that is compiled into the binary; a unit test locks the shipped defaults to that file so enforced invariants cannot drift from the audited table.
- **Stateless, fail-closed enforcer**: every DeviceCommand (device class, parameter, value, optional patient weight) yields a DeviceOutcome of Allow, Clamp, Deny, or escalation; an unknown device, an unknown parameter (a classification-integrity violation), an out-of-range value, or a command that would disable an alarm is denied, with ranges deliberately tighter than the hard physical-harm bounds.
- **Mandatory human confirmation for life-critical actuation**: the broker reuses the qutriage oversight escalation transport (ticket registry, human channel, timeout) but forces escalation for every life-sustaining or life-supporting command instead of consulting the risk score; a denied or timed-out confirmation is a denial, and monitoring-class actions need none.
- **Broker-local fail-safe controller**: a heartbeat tracks gateway-device liveness; on loss beyond a grace window a partition policy applies: freeze (hold the last command, the unsafe baseline), revert_to_safe (drive to the documented safe state), or handoff (revert and raise a handoff alarm). The logic runs inside the broker, so it holds even when the LLM or network is gone.
- **Run-length performance monitor**: tracks deviation between commanded and achieved settings and raises a degradation alert only when deviation stays above threshold for W = 3 consecutive actions, so a transient spike never alarms but sustained degradation always does within a bounded latency.

## Quickstart

Requires Rust 1.85+ (`rustup`), Python 3.10+ for the analysis scripts, and `tectonic` (or `pdflatex`) only if you want to rebuild the paper.

```bash
git clone https://github.com/quome-cloud/qubroker
cd qubroker
cargo build --release
cargo test device && cargo test --test device_broker   # this layer's tests
```

Then see the layer in action:

```bash
# 1. Fail-safe under communication partition (E2): freeze vs revert_to_safe vs handoff vs no-agent control, offline
cargo run --release --bin devicerun -- e2 \
  --corpus datasets/014-device-broker/devicebench/partition.jsonl \
  --out results/014-device-broker/e2.json
# wrote results/014-device-broker/e2.json   (freeze unsafe 30%, revert_to_safe 0%)

# 2. Mandatory confirmation cost/benefit (E3): life-critical actions blocked with no human, legit actions preserved, offline
cargo run --release --bin devicerun -- e3 \
  --corpus datasets/014-device-broker/devicebench/legit.jsonl \
  --out results/014-device-broker/e3.json
# wrote results/014-device-broker/e3.json   (100% blocked without a human, 100% legit preserved)

# 3. Hot-path overhead (E6): invariant enforcement per in-range command, offline
cargo run --release --bin devicerun -- e6 \
  --corpus datasets/014-device-broker/devicebench/legit.jsonl \
  --out results/014-device-broker/e6.json
# wrote results/014-device-broker/e6.json   (~0.05us per command)

# 4. (Optional, needs local Ollama with llama3.1:8b) the live unsafe-actuation study, E1
# cargo run --release --bin devicerun -- e1 --corpus datasets/014-device-broker/devicebench/scenarios.jsonl \
#   --out results/014-device-broker/e1.json --model llama3.1:8b

# Unit + integration tests (27 tests, incl. the devices.json pin)
cargo test device && cargo test --test device_broker
```

## Reproduce the experiments

Every number in the paper traces to one of these runs (95% Wilson CIs, deterministic seeds, pinned model snapshots). Run outputs land in `results/014-device-broker/` (not tracked; see [`results/014-device-broker/README.md`](results/014-device-broker/README.md) for the exact regeneration commands).

| Exp | What it measures | Needs |
|---|---|---|
| E1 | Unsafe-actuation prevention: broker-off vs broker-on through a live llama3.1:8b agent on 216 V1/V2/V3 + safe scenarios (McNemar, Wilson CIs) | ollama |
| E2 | Partition behavior: harm rate under freeze vs revert_to_safe vs handoff vs no-agent control | offline |
| E3 | Mandatory confirmation: life-critical actions blocked with no human, legit actions preserved, friction by risk class, modeled clinician latency | offline |
| E4 | Degradation detection: detection rate, false alarms, and detection latency of the run-length monitor | offline |
| E5 | Resilience under chaos: post-fault safe-state rate with vs without the fail-safe controller | offline |
| E6 | Overhead: per-command latency and throughput of invariant enforcement | offline |
| figures | Regenerate figures and numbers.tex from results/014-device-broker/ | offline |

```bash
# E1 — Unsafe-actuation prevention: broker-off vs broker-on through a live llama3.1:8b agent on 216 V1/V2/V3 + safe scenarios (McNemar, Wilson CIs)
cargo run --release --bin devicerun -- e1 --corpus datasets/014-device-broker/devicebench/scenarios.jsonl --out results/014-device-broker/e1.json --model llama3.1:8b

# E2 — Partition behavior: harm rate under freeze vs revert_to_safe vs handoff vs no-agent control
cargo run --release --bin devicerun -- e2 --corpus datasets/014-device-broker/devicebench/partition.jsonl --out results/014-device-broker/e2.json

# E3 — Mandatory confirmation: life-critical actions blocked with no human, legit actions preserved, friction by risk class, modeled clinician latency
cargo run --release --bin devicerun -- e3 --corpus datasets/014-device-broker/devicebench/legit.jsonl --out results/014-device-broker/e3.json

# E4 — Degradation detection: detection rate, false alarms, and detection latency of the run-length monitor
cargo run --release --bin devicerun -- e4 --corpus datasets/014-device-broker/devicebench/degradation.jsonl --out results/014-device-broker/e4.json

# E5 — Resilience under chaos: post-fault safe-state rate with vs without the fail-safe controller
cargo run --release --bin devicerun -- e5 --corpus datasets/014-device-broker/devicebench/faults.jsonl --out results/014-device-broker/e5.json

# E6 — Overhead: per-command latency and throughput of invariant enforcement
cargo run --release --bin devicerun -- e6 --corpus datasets/014-device-broker/devicebench/legit.jsonl --out results/014-device-broker/e6.json

# figures — Regenerate figures and numbers.tex from results/014-device-broker/
python3 scripts/014-device-broker/summarize.py
```

**Dataset — DeviceBench** (`datasets/014-device-broker/`): A version-pinned device invariant table (devicebench/devices.json, 014-devices-v1, embedded into the binary via include_str!) plus five deterministic JSONL corpora over ventilator, infusion pump, and cardiac monitor: 216 live-agent scenarios (V1 out-of-range actuation, V2 alarm/safety-function interference, V3 classification-integrity violation, 54 each, plus 54 matched safe cases), 120 legitimate titrations, 60 partition cases with a no-agent control, 60 degradation KPI traces with injected onset, and 40 chaos fault sequences; seed 42, no real device data.

Regenerate the corpus (deterministic seeds):

```bash
python3 scripts/014-device-broker/gen_devicebench.py
```

The corpus is also published as a Hugging Face dataset with a full data card: **[Quome/devicebench](https://huggingface.co/datasets/Quome/devicebench)** (`datasets.load_dataset("Quome/devicebench")`, or `hf download Quome/devicebench --repo-type dataset`).

All data are synthetic; no protected health information is used anywhere in this repository.

## Headline results

| Metric | Value | Context |
|---|---|---|
| Unsafe-actuation rate (live llama3.1:8b, n=216) | **53.7% broker-off -> 0.0% broker-on (95% CI upper bound 1.7%)** | McNemar chi-squared 114.0, b=116, c=0; 94.4% of legitimate actions preserved; JSON parse rate 92.6% |
| Harm under communication partition (E2) | **30.0% with freeze vs 0.0% with revert_to_safe / handoff** | revert matches the no-agent control; 100% safe-state maintenance |
| Mandatory confirmation (E3) | **100.0% of life-critical actions blocked with no human; 100.0% of legitimate actions preserved with a clinician** | 100% of life-critical actions need a human, monitoring needs none; confirmation latency 15 s median, 46 s p99 |
| Degradation detection (E4) | **100.0% detected, 0.0% false alarms, 3.0 actions mean latency (p95 3)** | window W = 3 |
| Post-fault safe state under chaos (E5) | **100.0% with the fail-safe controller vs 77.8% without** | 261 fault events; 84.6% of all steps safe overall with the controller |
| Hot-path overhead (E6) | **0.05 us per command (21.9M commands/s)** | invariant enforcement of an in-range command |

Full methodology, ablations, and statistics: **[the paper](papers/014-device-broker/main.pdf)**.

## The paper

**Fail Closed at the Bedside: A Device-Safety Broker for Agents that Actuate Life-Critical Medical Devices**

- PDF: [`papers/014-device-broker/main.pdf`](papers/014-device-broker/main.pdf)
- Source: [`papers/014-device-broker/`](papers/014-device-broker/) — `main.tex`, `numbers.tex` (every headline macro, generated by the scripts above), `figs/`, `refs.bib`
- Pre-registered proposal (threat model, hypotheses, experiment→figure map): [`papers/014-device-broker/PROPOSAL.md`](papers/014-device-broker/PROPOSAL.md)
- Rebuild: `cd papers/014-device-broker && make paper` (tectonic, or pdflatex + bibtex)

## Repository layout

| Path | What |
|---|---|
| `src/` | The `qfire` gateway crate. This paper's layer lives in `src/device/`; the other modules are the always-on baseline it plugs into. |
| `src/bin/` | CLI (`qfire`) and per-paper experiment harnesses |
| `rules/`, `chains/` | Declarative rule and detector-chain library used by the gateway |
| `datasets/014-device-broker/` | DeviceBench (also on Hugging Face: [Quome/devicebench](https://huggingface.co/datasets/Quome/devicebench)) |
| `scripts/014-device-broker/` | Dataset generator, experiment runners, figure and `numbers.tex` builders |
| `scripts/common/` | Shared helpers |
| `papers/014-device-broker/` | The paper (LaTeX + PDF + proposal) |
| `results/014-device-broker/` | Experiment outputs (see above) |
| `tests/`, `benches/` | Integration tests and Criterion benches |
| `SNAPSHOT.md` | Which `quokkaguard` commit this repo was exported from |

## Relationship to QUOKKAGUARD

This repo is a **snapshot** of the QUOKKAGUARD program's gateway (export `1c04c3a34841`, 2026-10-02), filtered to the `qubroker` module. The full `qfire` crate is included so this layer builds, tests, and runs standalone; the other modules are the always-on baseline the layer plugs into. Issues and pull requests are welcome here.

This layer builds on: [quwarden](https://github.com/quome-cloud/quwarden), [qutriage](https://github.com/quome-cloud/qutriage).

Sibling repos in the series: [quanchor](https://github.com/quome-cloud/quanchor), [quledger](https://github.com/quome-cloud/quledger), [qubom](https://github.com/quome-cloud/qubom), [quwarden](https://github.com/quome-cloud/quwarden), [qudam](https://github.com/quome-cloud/qudam), [quantidote](https://github.com/quome-cloud/quantidote), [quorum](https://github.com/quome-cloud/quorum), [qutriage](https://github.com/quome-cloud/qutriage), [qufair](https://github.com/quome-cloud/qufair), [qudrift](https://github.com/quome-cloud/qudrift), [qupassport](https://github.com/quome-cloud/qupassport), [quconsent](https://github.com/quome-cloud/quconsent), [qusiege](https://github.com/quome-cloud/qusiege).

## Cite

If you use this code or dataset, cite the paper and the HAARF framework it implements:

```bibtex
@unpublished{schwoebel2026qubroker,
  author = {Schwoebel, Jim and {QUOKKAGUARD Contributors}},
  title  = {Fail Closed at the Bedside: A Device-Safety Broker for Agents that Actuate Life-Critical Medical Devices},
  note   = {Preprint. Quome, QUOKKAGUARD program (qubroker module)},
  year   = {2026},
  url    = {https://github.com/quome-cloud/qubroker}
}

@unpublished{schwoebel2026haarf,
  author = {Schwoebel, Jim and Frasch, Martin and Spalding, Art and Sewell, Ed and Englert, Phil and Halpert, Ben and Overbay, Collin and Semenec, Ingrida and Shor, Joel},
  title  = {{HAARF}: Healthcare {AI} agents regulatory framework --- a comprehensive security verification standard for autonomous {AI} systems in clinical environments},
  note   = {medRxiv Preprint},
  year   = {2026},
  month  = {April},
  doi    = {10.64898/2026.04.09.26350519},
  url    = {https://www.medrxiv.org/content/10.64898/2026.04.09.26350519v1}
}
```

## Status

Research prototype. It demonstrates the layer end to end with reproducible experiments; it is not a certified medical device or a production security product. Threat-model boundaries and known gaps are in the paper's Discussion.

## License

Apache License 2.0 — see [LICENSE](LICENSE). Copyright (c) 2026 Quome, Inc.
