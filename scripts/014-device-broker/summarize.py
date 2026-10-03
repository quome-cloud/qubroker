#!/usr/bin/env python3
# Copyright 2026 Quome. Licensed under the Apache License, Version 2.0.
"""Summarize DeviceBench results (paper 014) into figures + numbers.tex + tables.

Reads results/014-device-broker/e{1..6}.json (produced by the `devicerun` bench
binary) and writes figures to papers/014-device-broker/figs/, headline macros to
papers/014-device-broker/numbers.tex, and a markdown table to
papers/014-device-broker/tables/. Skips any experiment whose results file is
absent (e.g. E1 still running on Ollama).
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = "results/014-device-broker"
FIGS = "papers/014-device-broker/figs"
TABLES = "papers/014-device-broker/tables"
NUMBERS = "papers/014-device-broker/numbers.tex"

NAVY, TEAL, AMBER, RED, GREY = "#1b2a4a", "#2a9d8f", "#e9c46a", "#c1432f", "#9aa0a6"
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})

os.makedirs(FIGS, exist_ok=True)
os.makedirs(TABLES, exist_ok=True)
macros = {}


def load(name):
    p = os.path.join(R, name)
    return json.load(open(p)) if os.path.exists(p) else None


def pctstr(x):
    return f"{100 * x:.1f}\\%"


# ---- E1: unsafe-actuation prevention (headline) --------------------------
def fig_e1(d):
    cells = d["per_cell"]
    # aggregate per vuln across devices for the headline bar
    vulns = ["V1", "V2", "V3", "safe"]
    labels = {"V1": "V1 out-of-range", "V2": "V2 alarm", "V3": "V3 class-integ.", "safe": "safe (legit)"}
    off, on = [], []
    for v in vulns:
        sub = [c for c in cells if c["vuln"] == v]
        n = sum(c["n"] for c in sub)
        off.append(sum(c["uar_off"] * c["n"] for c in sub) / n if n else 0.0)
        on.append(sum(c["uar_on"] * c["n"] for c in sub) / n if n else 0.0)
    x = range(len(vulns))
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    w = 0.38
    ax.bar([i - w / 2 for i in x], [100 * o for o in off], w, label="broker OFF", color=RED)
    ax.bar([i + w / 2 for i in x], [100 * o for o in on], w, label="broker ON", color=TEAL)
    ax.set_xticks(list(x))
    ax.set_xticklabels([labels[v] for v in vulns])
    ax.set_ylabel("unsafe-actuation rate (%)")
    ax.set_title(f"E1: live agent ({d['model']}) unsafe actuation, broker off vs on")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig1_unsafe_actuation.png"), dpi=160)
    plt.close(fig)

    macros["EoneModel"] = d["model"].replace("_", "\\_")
    macros["EoneN"] = str(d["n"])
    macros["EoneUarOff"] = pctstr(d["uar_off"])
    macros["EoneUarOn"] = pctstr(d["uar_on"])
    macros["EoneUarOnCiHi"] = pctstr(d["uar_on_ci"][1])
    macros["EoneMcNemarB"] = str(d["mcnemar_b_off_only"])
    macros["EoneMcNemarChi"] = f"{d['mcnemar_chi2']:.1f}"
    macros["EoneSafePreserve"] = pctstr(d["safe_preservation_rate"])
    macros["EoneParseRate"] = pctstr(d["parse_rate"])


# ---- E2: partition behaviour --------------------------------------------
def fig_e2(d):
    pols = d["policies"]
    names = {"freeze": "Freeze", "revert_to_safe": "Revert-to-safe", "handoff": "Handoff"}
    order = ["freeze", "revert_to_safe", "handoff"]
    pmap = {p["policy"]: p for p in pols}
    harm = [100 * pmap[k]["harm_rate"] for k in order]
    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    cols = [RED, TEAL, NAVY]
    ax.bar([names[k] for k in order], harm, color=cols, width=0.6)
    ax.axhline(0.0, color=GREY, ls="--", lw=1, label="no-agent control")
    ax.set_ylabel("post-partition harm rate (%)")
    ax.set_title("E2: harm under comms partition by fail-safe policy")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig2_partition.png"), dpi=160)
    plt.close(fig)

    with open(os.path.join(TABLES, "e2_partition.md"), "w") as f:
        f.write("| Fail-safe policy | Post-partition harm | Safe-state maintenance |\n")
        f.write("|---|---|---|\n")
        for k in order:
            p = pmap[k]
            f.write(f"| {names[k]} | {100*p['harm_rate']:.1f}% | {100*p['safe_state_maintenance']:.1f}% |\n")

    macros["EtwoFreezeHarm"] = pctstr(pmap["freeze"]["harm_rate"])
    macros["EtwoRevertHarm"] = pctstr(pmap["revert_to_safe"]["harm_rate"])
    macros["EtwoRevertPsm"] = pctstr(pmap["revert_to_safe"]["safe_state_maintenance"])


# ---- E3: confirmation latency + friction --------------------------------
def fig_e3(d):
    fr = {x["risk_class"]: x["friction"] for x in d["friction_by_class"]}
    order = [k for k in ["life_sustaining", "life_supporting", "monitoring"] if k in fr]
    names = {"life_sustaining": "life-sustaining", "life_supporting": "life-supporting", "monitoring": "monitoring"}
    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    ax.bar([names[k] for k in order], [100 * fr[k] for k in order], color=[NAVY, TEAL, GREY][: len(order)], width=0.6)
    ax.set_ylabel("commands requiring human confirm (%)")
    ax.set_title(f"E3: confirmation friction by device risk class (p99={d['confirm_latency_p99_s']:.0f}s)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig3_confirmation.png"), dpi=160)
    plt.close(fig)

    macros["EthreePmedian"] = f"{d['confirm_latency_p50_s']:.0f}"
    macros["EthreePninetynine"] = f"{d['confirm_latency_p99_s']:.0f}"
    macros["EthreeVfiveBlocked"] = pctstr(d["v5_blocked_no_human_rate"])
    macros["EthreePreserve"] = pctstr(d["legit_preservation_rate"])
    lc = [x for x in d["friction_by_class"] if x["risk_class"] != "monitoring"]
    macros["EthreeFrictionLC"] = pctstr(1.0 if lc else 0.0)


# ---- E4: degradation detection ------------------------------------------
def fig_e4(d):
    macros["EfourDetectRate"] = pctstr(d["detection_rate"])
    macros["EfourLatMean"] = f"{d['detect_latency_mean_actions']:.1f}"
    macros["EfourLatPninetyfive"] = f"{d['detect_latency_p95_actions']:.0f}"
    macros["EfourWindow"] = str(d["window_w"])
    macros["EfourFalseAlarm"] = pctstr(d["false_alarm_rate"])
    # simple illustrative fig: detection latency distribution is ~constant at W;
    # draw a small annotated bar.
    fig, ax = plt.subplots(figsize=(5.6, 3.0))
    ax.bar(["mean", "p95"], [d["detect_latency_mean_actions"], d["detect_latency_p95_actions"]],
           color=[TEAL, NAVY], width=0.5)
    ax.axhline(d["window_w"], color=RED, ls="--", lw=1, label=f"window W={d['window_w']}")
    ax.set_ylabel("detection latency (actions after onset)")
    ax.set_title(f"E4: degradation detected in {d['detect_latency_mean_actions']:.0f} actions "
                 f"({100*d['detection_rate']:.0f}% detected, {100*d['false_alarm_rate']:.0f}% FA)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig4_degradation.png"), dpi=160)
    plt.close(fig)


# ---- E5: resilience / chaos ---------------------------------------------
def fig_e5(d):
    wf, nf = d["with_failsafe"], d["without_failsafe"]
    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    groups = ["overall safe\nsteps", "post-fault\nsafe state"]
    with_v = [100 * wf["res"], 100 * wf["post_fault_safe_rate"]]
    without_v = [100 * nf["res"], 100 * nf["post_fault_safe_rate"]]
    x = range(len(groups))
    w = 0.38
    ax.bar([i - w / 2 for i in x], without_v, w, label="no fail-safe (freeze)", color=RED)
    ax.bar([i + w / 2 for i in x], with_v, w, label="with fail-safe (revert)", color=TEAL)
    ax.set_xticks(list(x))
    ax.set_xticklabels(groups)
    ax.set_ylabel("safe (%)")
    ax.set_title("E5: safe-state maintenance under fault injection")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig5_resilience.png"), dpi=160)
    plt.close(fig)

    macros["EfivePostFaultWith"] = pctstr(wf["post_fault_safe_rate"])
    macros["EfivePostFaultWithout"] = pctstr(nf["post_fault_safe_rate"])
    macros["EfiveResWith"] = pctstr(wf["res"])
    macros["EfiveFaults"] = str(wf["faults"])


# ---- E6: overhead --------------------------------------------------------
def num_e6(d):
    macros["EsixPerCmdUs"] = f"{d['per_command_us']:.2f}"
    tp = d["throughput_cmds_per_s"]
    macros["EsixThroughput"] = f"{tp/1e6:.1f}M" if tp >= 1e6 else f"{tp/1e3:.0f}K"


def main():
    handlers = [
        ("e1.json", fig_e1), ("e2.json", fig_e2), ("e3.json", fig_e3),
        ("e4.json", fig_e4), ("e5.json", fig_e5), ("e6.json", num_e6),
    ]
    for name, fn in handlers:
        d = load(name)
        if d is None:
            print(f"skip {name} (absent)")
            continue
        fn(d)
        print(f"processed {name}")

    with open(NUMBERS, "w") as f:
        f.write("% Auto-generated by scripts/014-device-broker/summarize.py — do not edit.\n")
        f.write("% Core macros are \\providecommand'd in main.tex; override here.\n")
        for k, v in sorted(macros.items()):
            f.write(f"\\renewcommand{{\\{k}}}{{{v}}}\n")
    print(f"wrote {NUMBERS} ({len(macros)} macros)")


if __name__ == "__main__":
    main()
