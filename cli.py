#!/usr/bin/env python3
"""Funscript Updater CLI

Four-step workflow:

  Step 1 — Assess
    python cli.py assess path/to/input.funscript [--output assessment.json]

  Step 2 — Review (human step — open assessment.json, review suggested windows)

  Step 3 — Manual updates (human step — edit manual_performance.json etc.)

  Step 4 — Generate
    python cli.py transform path/to/input.funscript \\
        --assessment assessment.json \\
        [--output output.funscript] \\
        [--config config.json] \\
        [--perf manual_performance.json] \\
        [--break manual_break.json] \\
        [--raw raw_windows.json]

Additional commands:

  python cli.py visualize path/to/input.funscript --assessment assessment.json [--output viz.png]
  python cli.py config --output config.json   # dump default config
  python cli.py test                          # run unit tests
"""

import argparse
import json
import os
import sys

# Ensure the project root is on the path so all modules resolve correctly
sys.path.insert(0, os.path.dirname(__file__))


# ------------------------------------------------------------------
# Command implementations
# ------------------------------------------------------------------

def cmd_assess(args):
    from assessment.analyzer import FunscriptAnalyzer, AnalyzerConfig

    config = None
    if args.config:
        import json as _json
        with open(args.config) as f:
            d = _json.load(f)
        config = AnalyzerConfig(**{
            k: v for k, v in d.items()
            if k in AnalyzerConfig.__dataclass_fields__
        })

    analyzer = FunscriptAnalyzer(config=config)
    analyzer.load(args.funscript)
    result = analyzer.analyze()

    output = args.output or _default_path(args.funscript, "_assessment.json")
    result.save(output)

    print(f"Assessment saved: {output}")
    print(f"  Duration:  {result.duration_ts}  ({result.duration_ms} ms)")
    print(f"  BPM:       {result.bpm}")
    print(f"  Actions:   {result.action_count}")
    print(f"  Phases:    {len(result.phases)}")
    print(f"  Cycles:    {len(result.cycles)}")
    print(f"  Patterns:  {len(result.patterns)}")
    print(f"  Phrases:   {len(result.phrases)}")
    perf = len(result.auto_mode_windows.get("performance", []))
    brk  = len(result.auto_mode_windows.get("break", []))
    dflt = len(result.auto_mode_windows.get("default", []))
    print(f"  Auto windows — performance: {perf}, break: {brk}, default: {dflt}")


def cmd_transform(args):
    from suggested_updates.transformer import FunscriptTransformer
    from suggested_updates.config import TransformerConfig

    config = TransformerConfig.load(args.config) if args.config else TransformerConfig()
    transformer = FunscriptTransformer(config)
    transformer.load_funscript(args.funscript)
    transformer.load_assessment_from_file(args.assessment)

    if args.beats:
        transformer.load_beats_from_file(args.beats)

    transformer.load_manual_overrides(
        perf_path=args.perf,
        break_path=args.break_windows,
        raw_path=args.raw,
    )

    merged = transformer.merge_windows()

    # Optionally save merged windows snapshot
    if args.save_merged:
        with open(args.save_merged, "w") as f:
            json.dump(merged, f, indent=2)
        print(f"Merged windows saved: {args.save_merged}")

    transformer.transform()

    output = args.output or _default_path(args.funscript, "_transformed.funscript")
    transformer.save(output)

    for line in transformer.get_log():
        print(line)
    print(f"\nTransformed funscript saved: {output}")


def cmd_visualize(args):
    import json as _json

    from assessment.visualizer import FunscriptVisualizer, HAS_MATPLOTLIB
    from models import AssessmentResult

    if not HAS_MATPLOTLIB:
        print("Error: matplotlib is not installed. Run: pip install matplotlib")
        sys.exit(1)

    with open(args.funscript) as f:
        data = _json.load(f)
    actions = data["actions"]

    assessment = AssessmentResult.load(args.assessment)
    output = args.output or _default_path(args.funscript, "_visualization.png")

    viz = FunscriptVisualizer(assessment, actions)
    viz.plot(output)
    print(f"Visualization saved: {output}")


def cmd_config(args):
    from suggested_updates.config import TransformerConfig

    cfg = TransformerConfig()
    output = args.output or "transformer_config.json"
    cfg.save(output)
    print(f"Default config written: {output}")
    print("Edit the values then pass with --config when running 'transform'.")


def cmd_test(_args):
    import unittest
    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=os.path.join(os.path.dirname(__file__), "tests"),
        pattern="test_*.py",
    )
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


# ------------------------------------------------------------------
# Argument parser
# ------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="Funscript Updater — analyze and transform funscripts",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- assess ---
    p_assess = sub.add_parser("assess", help="Step 1: analyze a funscript")
    p_assess.add_argument("funscript", help="Path to input .funscript file")
    p_assess.add_argument("--output", help="Path for the assessment JSON output")
    p_assess.add_argument("--config", help="Path to analyzer config JSON (optional)")

    # --- transform ---
    p_tx = sub.add_parser("transform", help="Step 4: generate a new funscript")
    p_tx.add_argument("funscript", help="Path to input .funscript file")
    p_tx.add_argument("--assessment", required=True, help="Path to assessment JSON")
    p_tx.add_argument("--output", help="Path for the output .funscript file")
    p_tx.add_argument("--config", help="Path to transformer config JSON")
    p_tx.add_argument("--beats", help="Path to beats JSON (enables Task 6)")
    p_tx.add_argument("--perf", help="Path to manual performance windows JSON")
    p_tx.add_argument(
        "--break", dest="break_windows", help="Path to manual break windows JSON"
    )
    p_tx.add_argument("--raw", help="Path to raw-preserve windows JSON")
    p_tx.add_argument("--save-merged", dest="save_merged",
                      help="Save merged windows snapshot to this path")

    # --- visualize ---
    p_viz = sub.add_parser("visualize", help="Visualize an assessment (requires matplotlib)")
    p_viz.add_argument("funscript", help="Path to input .funscript file")
    p_viz.add_argument("--assessment", required=True, help="Path to assessment JSON")
    p_viz.add_argument("--output", help="Path for the output PNG file")

    # --- config ---
    p_cfg = sub.add_parser("config", help="Dump default transformer config to JSON")
    p_cfg.add_argument("--output", help="Output path (default: transformer_config.json)")

    # --- test ---
    sub.add_parser("test", help="Run unit tests")

    return parser


def _default_path(source: str, suffix: str) -> str:
    base, _ = os.path.splitext(source)
    return base + suffix


def main():
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "assess": cmd_assess,
        "transform": cmd_transform,
        "visualize": cmd_visualize,
        "config": cmd_config,
        "test": cmd_test,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
