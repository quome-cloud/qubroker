> **Paper 014 proposal — Safe medical-device integration.** Imported 2026-06-07 from the local
> outline `P10` (`ongoing-papers/papers/10-medical-device-integration/`). Read with the
> [`ROADMAP.md`](../ROADMAP.md) deltas in mind: **monorepo** — features are `qfire`
> modules, not `haarf-*` crates or spin-out repos — and **confidential-enclave**
> production deployment, validated locally on Ollama via the OpenAI-compatible
> bridge. The threat model, hypotheses, experiments, datasets, and figures below
> are the pre-registered working plan; they are reconciled against the gateway as
> built at the feature-spec (stage 2) and paper-spec (stage 4) gates.

---

# Paper 10 — Safe Agent Integration with Life-Critical Medical Devices

**Crate:** `haarf-device` · **New dataset:** HAARF-Device · **Covers:** C8.3, C8.6, C3.1 · **Status:** outline

## Abstract

When agents actuate FDA-regulated medical devices — ventilators, infusion pumps, cardiac
monitors — the failure mode is immediate physical harm, and HAARF C8.3 (Medical Device
Integration), C8.6 (Tool Performance Monitoring), and C3.1 (Resilience to Socio-Technical
Disruption) become safety-critical. We build `haarf-device`, a device-integration safety
broker that preserves device classification integrity and alarms, enforces fail-safe
defaults, mandates human oversight for life-critical actuation, and degrades gracefully
when agent or device communication fails. We contribute **HAARF-Device**, a simulator +
scenario suite for ventilator/infusion/monitor interactions with safety-critical edge
cases, and show the broker prevents unsafe actuation while preserving legitimate use.

## Stakeholders & expert-in-the-loop

Life-critical device safety can only be validated by experts who own these devices at
the bedside and under regulation; this paper keeps them in the loop end-to-end.

- **Intensivist / critical-care physician** — owns the clinical risk of every
  ventilator/infusion/monitor decision and defines what "unsafe actuation" means at the
  bedside (V1, V5).
- **Respiratory therapist** — sets and titrates ventilators daily; validates tidal
  volume / pressure safe ranges, alarm semantics, and which actions need a human in the
  loop.
- **Critical-care / charge nurse** — frontline operator of infusion pumps and alarm
  response; grounds confirmation-latency tolerance (RQ3) and alarm-integrity needs (V2).
- **Biomedical / clinical engineer** — owns device integration, interlocks, and
  safe-state behavior in the hospital, validating the fail-safe controller and heartbeat
  design under comms failure (V4, C3.1).
- **Medical-device safety engineer (IEC 60601)** — ensures the broker preserves device
  classification integrity and safety functions per device-design standards (V3, C8.3).
- **Regulatory-affairs (FDA device) specialist** — maps the broker to FDA device
  classification, MAUDE failure modes, and cybersecurity guidance so claims survive
  regulatory scrutiny.
- **Patient-safety / human-factors expert** — evaluates mandatory-confirmation
  workflows for alarm fatigue and friction so safety gates do not induce new error modes
  (RQ3, V5).

## Problem / safety model

- **V1 Out-of-range actuation** — agent commands a device setting outside safe/clinical
  bounds (e.g. infusion rate, tidal volume).
- **V2 Alarm/safety-function interference** — agent action suppresses or disrupts a
  device alarm or safety interlock (C8.3.2).
- **V3 Classification-integrity violation** — agent use alters the device's intended use
  / risk class (C8.3.1).
- **V4 Comms failure / partition** — agent or network fails mid-actuation; device must
  fail safe, not freeze in a dangerous state (C8.3.5, C3.1).
- **V5 Unbounded autonomous actuation** — life-critical action taken without the
  mandatory human confirmation (C8.3.4).

## Research questions

- **RQ1** Can a broker enforce device-specific safe-range + interlock invariants with
  zero unsafe actuations across the scenario suite?
- **RQ2** What fail-safe policy minimizes harm under comms failure/partition (V4)?
- **RQ3** What is the latency cost of mandatory human confirmation for life-critical
  actions, and is it within clinical tolerance?
- **RQ4** Can device performance monitoring (C8.6) detect device/integration degradation
  before harm?

## Hypotheses

- **H1** Invariant enforcement yields 0 out-of-range/interlock-violating actuations
  (V1/V2) across HAARF-Device.
- **H2** Fail-safe defaults reduce harm under V4 partition to ≤ baseline-no-agent risk
  (the agent must never make a partition *worse*).
- **H3** Mandatory-confirmation adds bounded latency (report p99) and eliminates V5 with
  ≤ X% legitimate-action friction.
- **H4** Device performance monitoring detects injected degradation within W actions.

## Experiments → figures

- **E1 Unsafe-actuation prevention (→ Fig 1):** unsafe rate per device per attack V1–V3,
  {no broker, broker}.
- **E2 Partition behavior (→ Fig 2):** harm outcome under V4 across fail-safe policies
  (freeze / revert-to-safe / handoff-to-human).
- **E3 Confirmation latency (→ Fig 3):** actuation latency + friction vs. confirmation
  policy by device risk class.
- **E4 Performance monitoring (→ Fig 4):** device-degradation detection latency.
- **E5 Resilience/chaos (→ Fig 5):** safe-state maintenance under injected faults
  (latency spikes, dropped messages, device errors) — C3.1.
- **E6 Gateway overhead (→ shared Fig).**

## Datasets

**Public:**
- **PhysioNet** waveform/vitals (MIT-BIH, VitalDB, MIMIC-IV-Waveform) — realistic
  monitor/vitals streams driving simulated devices.
- **FDA medical-device cybersecurity** guidance + **MAUDE** adverse-event reports —
  real device failure modes to seed scenarios.
- Open device simulators / IEC 60601 safe-range references for bounds.

**New — HAARF-Device (the contribution):**
- A **device simulator** (ventilator, infusion pump, cardiac monitor) with documented
  safe ranges, alarms, and interlocks, exposed as tools to the gateway.
- A scenario suite covering V1–V5 with ground-truth safe/unsafe labels and fail-safe
  expected behavior, plus a fault-injection harness for C3.1 resilience.
- A legitimate-use corpus (titrations clinicians *should* be able to do).
  Apache-2.0, synthetic.

## Validation & statistics

- Unsafe-actuation rate (target 0) with exact CIs; any nonzero case root-caused.
- Partition/fault outcomes compared to a no-agent control (the agent must not increase
  risk).
- Latency via `criterion` + the load harness; report p99.
- **Threats to validity:** simulator fidelity vs. real devices (explicit sim-to-real
  gap; recommend HIL bench follow-up); safe-range tables are device/version specific.

## Rust components (`haarf-device`)

- **Invariant enforcer:** per-device safe-range + interlock + alarm-preservation rules
  (expressible via `haarf-policy`); rejects/clamps unsafe commands.
- **Mandatory-confirmation gate:** life-critical actions route to `Escalate` (Paper 6)
  with a hard human-confirm requirement (C8.3.4).
- **Fail-safe controller:** heartbeat between gateway and device; on loss, drives the
  device to its documented safe state rather than leaving last command latched.
- **Device performance monitor:** tracks device response/health KPIs (C8.6); links
  Paper 9.

## Server / proxy design

- The broker is an **enforcing** layer for device-class tools (fail-closed, no
  fail-open option for life-critical devices).
- Runs after identity/policy; invariants are device-version-pinned and signed
  (Paper 2/8).
- Heartbeat + safe-state logic is local to the broker so it holds even if the LLM/agent
  is unreachable (C3.1 resilience).

## Metrics

| Metric | Definition | Target |
|---|---|---|
| UAR | Unsafe-actuation rate | 0% |
| PSM | Partition safe-state maintenance | 100% |
| CFL | Confirmation latency (life-critical) p99 | within SLA |
| DDM | Device-degradation detection latency | ≤ W |
| RES | Safe-state held under fault injection | 100% |

## Repo scaffold

```
haarf-device/
├── crates/haarf-device/            # invariants + confirm gate + fail-safe + perf monitor
├── dataset/haarf-device/           # simulator + scenarios + fault harness + legit corpus
├── figures/
└── paper/
```
