#!/usr/bin/env python3
"""Funscript Forge CLI

Full-pipeline shortcut (Steps 1 + 3 + 4 in one command):

  python cli.py pipeline path/to/input.funscript --output-dir output/
      [--perf performance.json] [--break break.json] [--raw raw.json]
      [--beats beats.json] [--transformer-config tc.json]
      [--customizer-config cc.json]

Individual steps:

  Step 1 — Assess
    python cli.py assess path/to/input.funscript [--output assessment.json]
                        [--config analyzer_config.json]
                        [--min-phrase-duration SECONDS]
                        [--amplitude-tolerance FRACTION]

  Step 2 — Review (human step — open assessment.json, review bpm_transitions and phrase BPMs)

  Step 3 — Transform (BPM-threshold based)
    python cli.py transform path/to/input.funscript \\
        --assessment assessment.json \\
        [--output output.funscript] \\
        [--config transformer_config.json]

  Step 4 — Customize (human-defined windows)
    python cli.py customize path/to/transformed.funscript \\
        --assessment assessment.json \\
        [--output customized.funscript] \\
        [--config customizer_config.json] \\
        [--perf manual_performance.json] \\
        [--break manual_break.json] \\
        [--raw raw_windows.json] \\
        [--beats beats.json]

  Step 2b — Phrase Transform (catalog transform on individual phrases)
    python cli.py phrase-transform path/to/input.funscript \\
        --assessment assessment.json \\
        --transform smooth --phrase 3 [--param strength=0.25]    # one phrase
        --transform normalize --all                               # all phrases
        --suggest [--bpm-threshold 120]                          # auto-pick per phrase
        --dry-run                                                # print plan only

    For split-phrase workflows (different transforms in different time ranges within
    a single phrase) use the Streamlit Pattern Editor UI — it supports adding split
    boundaries, per-segment transform selection, and proportional copy to all
    instances of the same behavioral tag.

Additional commands:

  python cli.py finalize path/to/transformed.funscript          # blend seams + final smooth, then save
      [--output finalized.funscript]
      [--param seam_max_velocity=0.3]   # blend_seams param override
      [--param smooth_strength=0.05]    # final_smooth param override
      [--skip-seams] [--skip-smooth]    # disable either pass

  python cli.py catalog [--catalog PATH]                       # show catalog summary
  python cli.py catalog --tag stingy                           # list all stingy phrases
  python cli.py catalog --remove Timeline1.original.funscript  # remove one entry
  python cli.py catalog --clear                                # clear all entries

  python cli.py visualize path/to/input.funscript --assessment assessment.json [--output viz.png]
  python cli.py config --output transformer_config.json        # dump default transformer config
  python cli.py config --customizer --output cc.json           # dump customizer config
  python cli.py config --analyzer --output analyzer_config.json  # dump analyzer config
  python cli.py test                                            # run all tests
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))


# ------------------------------------------------------------------
# Command implementations
# ------------------------------------------------------------------

def _build_analyzer_config(args):
    """Build an AnalyzerConfig from CLI args and optional --config file."""
    from assessment.analyzer import AnalyzerConfig
    config = AnalyzerConfig()
    if getattr(args, "config", None):
        with open(args.config) as f:
            d = json.load(f)
        config = AnalyzerConfig(**{
            k: v for k, v in d.items()
            if k in AnalyzerConfig.__dataclass_fields__
        })
    if getattr(args, "min_phrase_duration", None) is not None:
        config.min_phrase_duration_ms = int(args.min_phrase_duration * 1000)
    if getattr(args, "amplitude_tolerance", None) is not None:
        config.amplitude_tolerance = args.amplitude_tolerance
    return config


def cmd_pipeline(args):
    from assessment.analyzer import FunscriptAnalyzer
    from pattern_catalog.config import TransformerConfig
    from user_customization.config import CustomizerConfig
    from user_customization.customizer import WindowCustomizer
    from pattern_catalog.transformer import FunscriptTransformer
    import tempfile, os

    output_dir = args.output_dir or os.path.join(
        os.path.dirname(args.funscript), "output"
    )
    os.makedirs(output_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(args.funscript))[0]

    # Stage 1 — Assess
    analyzer = FunscriptAnalyzer(config=_build_analyzer_config(args))
    analyzer.load(args.funscript)
    t0 = time.time()
    assessment = analyzer.analyze()
    assessment_path = os.path.join(output_dir, f"{base}.assessment.json")
    assessment.save(assessment_path)
    print(f"Assessment saved: {assessment_path}  ({time.time() - t0:.2f}s)")
    print(f"  BPM: {assessment.bpm}  Phrases: {len(assessment.phrases)}"
          f"  Transitions: {len(assessment.bpm_transitions)}")

    # Stage 2 — Transform
    tx_config = TransformerConfig.load(args.transformer_config) if args.transformer_config else TransformerConfig()
    transformer = FunscriptTransformer(tx_config)
    transformer.load_funscript(args.funscript)
    transformer.load_assessment(assessment)
    t0 = time.time()
    transformer.transform()
    transformed_path = os.path.join(output_dir, f"{base}.transformed.funscript")
    transformer.save(transformed_path)
    print(f"Transformed:  {transformed_path}  ({time.time() - t0:.2f}s)")

    # Stage 3 — Customize
    cust_config = CustomizerConfig.load(args.customizer_config) if args.customizer_config else CustomizerConfig()
    customizer = WindowCustomizer(cust_config)
    customizer.load_funscript(transformed_path)
    customizer.load_assessment(assessment)
    customizer.load_manual_overrides(
        perf_path=args.perf,
        break_path=args.break_windows,
        raw_path=args.raw,
    )
    if args.beats:
        customizer.load_beats_from_file(args.beats)
    t0 = time.time()
    customizer.customize()
    customized_path = os.path.join(output_dir, f"{base}.customized.funscript")
    customizer.save(customized_path)
    print(f"Customized:   {customized_path}  ({time.time() - t0:.2f}s)")


def cmd_assess(args):
    from assessment.analyzer import FunscriptAnalyzer

    analyzer = FunscriptAnalyzer(config=_build_analyzer_config(args))
    analyzer.load(args.funscript)
    t0 = time.time()
    result = analyzer.analyze()
    elapsed = time.time() - t0

    output = args.output or _default_path(args.funscript, "_assessment.json")
    result.save(output)

    print(f"Assessment saved: {output}  ({elapsed:.2f}s)")
    print(f"  Duration:  {result.duration_ts}  ({result.duration_ms} ms)")
    print(f"  BPM:       {result.bpm}")
    print(f"  Actions:   {result.action_count}")
    print(f"  Phases:    {len(result.phases)}")
    print(f"  Cycles:    {len(result.cycles)}")
    print(f"  Patterns:  {len(result.patterns)}")
    print(f"  Phrases:   {len(result.phrases)}")
    if result.bpm_transitions:
        print(f"  BPM transitions ({len(result.bpm_transitions)}):")
        for t in result.bpm_transitions:
            print(f"    {t.description}")
    else:
        print("  BPM transitions: none detected")


def cmd_transform(args):
    from pattern_catalog.transformer import FunscriptTransformer
    from pattern_catalog.config import TransformerConfig

    config = TransformerConfig.load(args.config) if args.config else TransformerConfig()
    transformer = FunscriptTransformer(config)
    transformer.load_funscript(args.funscript)
    transformer.load_assessment_from_file(args.assessment)
    t0 = time.time()
    transformer.transform()
    elapsed = time.time() - t0

    output = args.output or _default_path(args.funscript, "_transformed.funscript")
    transformer.save(output)

    for line in transformer.get_log():
        print(line)
    print(f"\nTransformed funscript saved: {output}  ({elapsed:.2f}s)")


def cmd_customize(args):
    from user_customization.customizer import WindowCustomizer
    from user_customization.config import CustomizerConfig

    config = CustomizerConfig.load(args.config) if args.config else CustomizerConfig()
    customizer = WindowCustomizer(config)
    customizer.load_funscript(args.funscript)
    customizer.load_assessment_from_file(args.assessment)

    customizer.load_manual_overrides(
        perf_path=args.perf,
        break_path=args.break_windows,
        raw_path=args.raw,
    )

    if args.beats:
        customizer.load_beats_from_file(args.beats)

    t0 = time.time()
    customizer.customize()
    elapsed = time.time() - t0

    output = args.output or _default_path(args.funscript, "_customized.funscript")
    customizer.save(output)

    for line in customizer.get_log():
        print(line)
    print(f"\nCustomized funscript saved: {output}  ({elapsed:.2f}s)")


def cmd_visualize(args):
    from visualizations.motion import MotionVisualizer, HAS_MATPLOTLIB
    from models import AssessmentResult

    if not HAS_MATPLOTLIB:
        print("Error: matplotlib is not installed. Run: pip install matplotlib")
        sys.exit(1)

    with open(args.funscript) as f:
        data = json.load(f)
    actions = data["actions"]

    assessment = AssessmentResult.load(args.assessment)
    output = args.output or _default_path(args.funscript, "_visualization.png")

    viz = MotionVisualizer(assessment, actions)
    viz.plot(output)
    print(f"Visualization saved: {output}")


def cmd_config(args):
    if args.customizer:
        from user_customization.config import CustomizerConfig
        cfg = CustomizerConfig()
        output = args.output or "customizer_config.json"
        cfg.save(output)
        print(f"Default customizer config written: {output}")
    elif args.analyzer:
        from assessment.analyzer import AnalyzerConfig
        import dataclasses, json
        cfg = AnalyzerConfig()
        output = args.output or "analyzer_config.json"
        with open(output, "w") as f:
            json.dump(dataclasses.asdict(cfg), f, indent=2)
        print(f"Default analyzer config written: {output}")
    else:
        from pattern_catalog.config import TransformerConfig
        cfg = TransformerConfig()
        output = args.output or "transformer_config.json"
        cfg.save(output)
        print(f"Default transformer config written: {output}")
    print("Edit the values then pass with --config when running the command.")


def _coerce(v: str):
    """Parse a string value as int, float, or str."""
    try:
        i = int(v); f = float(v)
        return i if i == f else f
    except ValueError:
        return v


def cmd_phrase_transform(args):
    """Apply a catalog transform to one or all phrases of a funscript."""
    from pattern_catalog.phrase_transforms import TRANSFORM_CATALOG, suggest_transform
    from models import AssessmentResult
    import copy

    # --- load inputs ---
    with open(args.funscript) as f:
        data = json.load(f)
    actions = data["actions"]
    assessment = AssessmentResult.load(args.assessment)
    phrases = [p.__dict__ if hasattr(p, "__dict__") else p for p in assessment.phrases]
    # Normalise to plain dicts with the keys phrase_detail expects
    phrase_dicts = []
    for p in assessment.phrases:
        d = p if isinstance(p, dict) else {
            "start_ms":      p.start_ms,
            "end_ms":        p.end_ms,
            "bpm":           getattr(p, "bpm", 0),
            "pattern_label": getattr(p, "pattern_label", ""),
            "amplitude_span": getattr(p, "amplitude_span", 100),
            "cycle_count":   getattr(p, "cycle_count", None),
        }
        phrase_dicts.append(d)

    if not phrase_dicts:
        print("No phrases found in assessment — nothing to transform.")
        sys.exit(1)

    # --- resolve which phrases to process ---
    if args.all or args.suggest:
        indices = list(range(len(phrase_dicts)))
    elif args.phrase:
        indices = []
        for n in args.phrase:
            idx = n - 1   # user-facing is 1-based
            if idx < 0 or idx >= len(phrase_dicts):
                print(f"Error: --phrase {n} is out of range (1–{len(phrase_dicts)}).")
                sys.exit(1)
            indices.append(idx)
    else:
        print("Error: specify --phrase N, --all, or --suggest.")
        sys.exit(1)

    # --- parse --param key=value pairs ---
    extra_params = {}
    for kv in (args.param or []):
        if "=" not in kv:
            print(f"Error: --param must be key=value, got: {kv!r}")
            sys.exit(1)
        k, v = kv.split("=", 1)
        extra_params[k.strip()] = _coerce(v.strip())

    # --- build transform plan ---
    bpm_threshold = args.bpm_threshold or 120.0
    plan = []   # list of (phrase_idx, transform_key, param_values)
    for idx in indices:
        phrase = phrase_dicts[idx]
        if args.suggest:
            key = suggest_transform(phrase, bpm_threshold)
        else:
            key = args.transform
            if key not in TRANSFORM_CATALOG:
                print(f"Error: unknown transform {key!r}. "
                      f"Available: {', '.join(TRANSFORM_CATALOG)}")
                sys.exit(1)
        spec = TRANSFORM_CATALOG[key]
        params = {k: v.default for k, v in spec.params.items()}
        params.update(extra_params)
        plan.append((idx, key, params))

    # --- print plan ---
    print(f"Phrase-transform plan ({len(plan)} phrase{'s' if len(plan) != 1 else ''}):")
    for idx, key, params in plan:
        ph = phrase_dicts[idx]
        param_str = "  ".join(f"{k}={v}" for k, v in params.items()) if params else "-"
        label = ph.get('pattern_label', '').encode('ascii', errors='replace').decode('ascii')
        print(f"  P{idx + 1:>2}  {key:<18}  params: {param_str}"
              f"  ({ph.get('bpm', 0):.0f} BPM, {label})")

    if args.dry_run:
        print("\n--dry-run: no file written.")
        return

    # --- apply ---
    result = copy.deepcopy(actions)
    for idx, key, params in plan:
        spec  = TRANSFORM_CATALOG[key]
        ph    = phrase_dicts[idx]
        start = ph["start_ms"]
        end   = ph["end_ms"]
        slice_ = [a for a in result if start <= a["at"] <= end]
        transformed = spec.apply(slice_, params)
        if spec.structural:
            # Replace the phrase slice with the new (potentially shorter) actions
            result = [a for a in result if not (start <= a["at"] <= end)]
            result = sorted(result + transformed, key=lambda a: a["at"])
        else:
            t_map = {a["at"]: a["pos"] for a in transformed}
            for a in result:
                if a["at"] in t_map:
                    a["pos"] = t_map[a["at"]]

    # --- save ---
    data["actions"] = result
    output = args.output or _default_path(args.funscript, "_phrase_transformed.funscript")
    with open(output, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nSaved: {output}")


def cmd_finalize(args):
    """Apply blend_seams + final_smooth to the full action list, then save."""
    from pattern_catalog.phrase_transforms import TRANSFORM_CATALOG
    import copy

    with open(args.funscript) as f:
        data = json.load(f)

    result = copy.deepcopy(data["actions"])

    seam_spec   = TRANSFORM_CATALOG["blend_seams"]
    smooth_spec = TRANSFORM_CATALOG["final_smooth"]

    # Build optional param overrides from --param seam_* / smooth_* prefixes
    seam_params   = {}
    smooth_params = {}
    for kv in (args.param or []):
        if "=" not in kv:
            print(f"Error: --param must be key=value, got: {kv!r}")
            sys.exit(1)
        k, v = kv.split("=", 1)
        k = k.strip()
        val = _coerce(v.strip())
        if k.startswith("seam_"):
            seam_params[k[5:]] = val
        elif k.startswith("smooth_"):
            smooth_params[k[7:]] = val
        else:
            print(f"Error: --param key must start with seam_ or smooth_, got: {k!r}")
            sys.exit(1)

    if not args.skip_seams:
        result = seam_spec.apply(result, seam_params or None)
        print(f"Applied blend_seams  (max_velocity={seam_spec.params['max_velocity'].default if not seam_params else seam_params.get('max_velocity', seam_spec.params['max_velocity'].default)}, "
              f"max_strength={seam_params.get('max_strength', seam_spec.params['max_strength'].default)})")

    if not args.skip_smooth:
        result = smooth_spec.apply(result, smooth_params or None)
        print(f"Applied final_smooth (strength={smooth_params.get('strength', smooth_spec.params['strength'].default)})")

    data["actions"] = result
    output = args.output or _default_path(args.funscript, "_finalized.funscript")
    with open(output, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nSaved: {output}")


def cmd_catalog(args):
    """Inspect or manage the cross-funscript pattern catalog."""
    from catalog.pattern_catalog import PatternCatalog

    catalog_path = args.catalog or os.path.join(
        os.path.dirname(__file__), "output", "pattern_catalog.json"
    )
    cat = PatternCatalog(catalog_path)

    if args.clear:
        cat._data["entries"] = []
        cat.save()
        print("Catalog cleared.")
        return

    if args.remove:
        removed = cat.remove(args.remove)
        if removed:
            cat.save()
            print(f"Removed: {args.remove}")
        else:
            print(f"Not found in catalog: {args.remove}")
        return

    if args.tag:
        from assessment.classifier import TAGS
        tag = args.tag
        meta = TAGS.get(tag)
        phrases = cat.get_phrases_for_tag(tag)
        label = meta.label if meta else tag
        print(f"Tag '{label}' — {len(phrases)} phrase(s) across {len({p['_funscript'] for p in phrases})} file(s)")
        if meta:
            print(f"  Description: {meta.description}")
            print(f"  Suggested fix: {meta.suggested_transform} — {meta.fix_hint}")
        for ph in phrases:
            from utils import ms_to_timestamp
            print(f"  [{ph['_funscript']}]  {ms_to_timestamp(ph['start_ms'])} → {ms_to_timestamp(ph['end_ms'])}"
                  f"  BPM: {ph.get('bpm', 0):.1f}"
                  f"  span: {ph.get('metrics', {}).get('span', 0):.1f}")
        return

    # Default: summary
    s = cat.summary()
    print(f"Catalog: {catalog_path}")
    print(f"  Funscripts indexed : {s['funscripts_indexed']}")
    print(f"  Tagged phrases     : {s['total_tagged_phrases']}")
    if s["tags_found"]:
        stats = cat.get_tag_stats()
        print(f"  Tags found         : {', '.join(s['tags_found'])}")
        print()
        print(f"  {'Tag':<14}  {'Phrases':>7}  {'Files':>5}  {'BPM':>12}  {'Span':>12}")
        print(f"  {'-'*14}  {'-'*7}  {'-'*5}  {'-'*12}  {'-'*12}")
        for tag in s["tags_found"]:
            st = stats[tag]
            from assessment.classifier import TAGS
            label = TAGS[tag].label if tag in TAGS else tag
            bpm_range  = f"{st['bpm_min']}–{st['bpm_max']}"
            span_range = f"{st['span_min']}–{st['span_max']}"
            print(f"  {label:<14}  {st['count']:>7}  {st['funscripts']:>5}  {bpm_range:>12}  {span_range:>12}")
    else:
        print("  No tagged phrases yet — assess a funscript to populate the catalog.")


def cmd_test(_args):
    import unittest
    root = os.path.dirname(__file__)
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    # Core pipeline tests
    suite.addTests(loader.discover(start_dir=os.path.join(root, "tests"), pattern="test_*.py"))
    # UI common-layer tests
    suite.addTests(loader.discover(start_dir=os.path.join(root, "ui", "common", "tests"), pattern="test_*.py"))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


# ------------------------------------------------------------------
# Argument parser
# ------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="Funscript Forge — analyze and transform funscripts",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- pipeline ---
    p_pipe = sub.add_parser(
        "pipeline",
        help="Run all three stages (assess -> transform -> customize) in one step",
    )
    p_pipe.add_argument("funscript", help="Path to source .funscript file")
    p_pipe.add_argument(
        "--output-dir", help="Directory for all output files (default: ./output/)"
    )
    p_pipe.add_argument("--perf", help="Performance windows JSON")
    p_pipe.add_argument(
        "--break", dest="break_windows", help="Break windows JSON"
    )
    p_pipe.add_argument("--raw", help="Raw-preserve windows JSON")
    p_pipe.add_argument("--beats", help="Beats JSON (enables beat accents)")
    p_pipe.add_argument("--transformer-config", help="Transformer config JSON")
    p_pipe.add_argument("--customizer-config", help="Customizer config JSON")
    p_pipe.add_argument(
        "--min-phrase-duration", type=float, metavar="SECONDS",
        help="Merge phrases shorter than this many seconds (default: 20)",
    )
    p_pipe.add_argument(
        "--amplitude-tolerance", type=float, metavar="FRACTION",
        help="Phrase break sensitivity fraction (lower = more sensitive; default: 0.30)",
    )

    # --- assess ---
    p_assess = sub.add_parser("assess", help="Step 1: analyze a funscript")
    p_assess.add_argument("funscript", help="Path to input .funscript file")
    p_assess.add_argument("--output", help="Path for the assessment JSON output")
    p_assess.add_argument("--config", help="Path to analyzer config JSON (optional)")
    p_assess.add_argument(
        "--min-phrase-duration", type=float, metavar="SECONDS",
        help="Merge phrases shorter than this many seconds into neighbours (default: 20)",
    )
    p_assess.add_argument(
        "--amplitude-tolerance", type=float, metavar="FRACTION",
        help="Phrase break sensitivity: fraction of amplitude deviation to trigger a new phrase "
             "(lower = more sensitive, e.g. 0.25; default: 0.30)",
    )

    # --- transform ---
    p_tx = sub.add_parser("transform", help="Step 3: BPM-threshold transform")
    p_tx.add_argument("funscript", help="Path to input .funscript file")
    p_tx.add_argument("--assessment", required=True, help="Path to assessment JSON")
    p_tx.add_argument("--output", help="Path for the output .funscript file")
    p_tx.add_argument("--config", help="Path to transformer config JSON")

    # --- customize ---
    p_cust = sub.add_parser("customize", help="Step 4: apply user-defined windows")
    p_cust.add_argument("funscript", help="Path to transformed .funscript file")
    p_cust.add_argument("--assessment", required=True, help="Path to assessment JSON")
    p_cust.add_argument("--output", help="Path for the customized .funscript file")
    p_cust.add_argument("--config", help="Path to customizer config JSON")
    p_cust.add_argument("--perf", help="Path to performance windows JSON")
    p_cust.add_argument(
        "--break", dest="break_windows", help="Path to break windows JSON"
    )
    p_cust.add_argument("--raw", help="Path to raw-preserve windows JSON")
    p_cust.add_argument("--beats", help="Path to beats JSON (enables beat accents)")

    # --- visualize ---
    p_viz = sub.add_parser("visualize", help="Visualize an assessment (requires matplotlib)")
    p_viz.add_argument("funscript", help="Path to input .funscript file")
    p_viz.add_argument("--assessment", required=True, help="Path to assessment JSON")
    p_viz.add_argument("--output", help="Path for the output PNG file")

    # --- config ---
    p_cfg = sub.add_parser("config", help="Dump default config to JSON")
    p_cfg.add_argument("--output", help="Output path")
    p_cfg.add_argument(
        "--customizer", action="store_true",
        help="Dump customizer config instead of transformer config",
    )
    p_cfg.add_argument(
        "--analyzer", action="store_true",
        help="Dump analyzer config instead of transformer config",
    )

    # --- phrase-transform ---
    p_pt = sub.add_parser(
        "phrase-transform",
        help="Apply a catalog transform to one or all phrases",
    )
    p_pt.add_argument("funscript", help="Path to input .funscript file")
    p_pt.add_argument("--assessment", required=True, help="Path to assessment JSON")
    p_pt.add_argument("--output", help="Path for output .funscript (default: *_phrase_transformed.funscript)")
    p_pt.add_argument(
        "--transform", metavar="KEY",
        help=f"Transform to apply. One of: {', '.join(['passthrough','amplitude_scale','normalize','smooth','clamp_upper','clamp_lower','invert','boost_contrast','shift','recenter','break','performance','three_one','beat_accent','blend_seams','final_smooth','halve_tempo'])}",
    )
    p_pt.add_argument(
        "--phrase", type=int, metavar="N", action="append",
        help="1-based phrase index to transform (repeatable). Mutually exclusive with --all.",
    )
    p_pt.add_argument(
        "--all", action="store_true",
        help="Apply transform to every phrase.",
    )
    p_pt.add_argument(
        "--suggest", action="store_true",
        help="Use suggest_transform() to pick the best transform per phrase automatically.",
    )
    p_pt.add_argument(
        "--bpm-threshold", type=float, default=120.0, metavar="BPM",
        help="BPM threshold used by --suggest (default: 120.0).",
    )
    p_pt.add_argument(
        "--param", metavar="key=value", action="append",
        help="Override a transform parameter, e.g. --param scale=1.8 (repeatable).",
    )
    p_pt.add_argument(
        "--dry-run", action="store_true",
        help="Print the transform plan without writing any file.",
    )

    # --- finalize ---
    p_fin = sub.add_parser(
        "finalize",
        help="Apply blend_seams + final_smooth to the full action list before saving",
    )
    p_fin.add_argument("funscript", help="Path to input .funscript file")
    p_fin.add_argument("--output", help="Path for output .funscript (default: *_finalized.funscript)")
    p_fin.add_argument(
        "--param", metavar="PREFIX_key=value", action="append",
        help=(
            "Override a transform parameter. Prefix with seam_ for blend_seams params "
            "or smooth_ for final_smooth params. "
            "E.g. --param seam_max_velocity=0.3  --param smooth_strength=0.05"
        ),
    )
    p_fin.add_argument(
        "--skip-seams", action="store_true",
        help="Skip the blend_seams step.",
    )
    p_fin.add_argument(
        "--skip-smooth", action="store_true",
        help="Skip the final_smooth step.",
    )

    # --- catalog ---
    p_cat = sub.add_parser(
        "catalog",
        help="Inspect or manage the cross-funscript pattern catalog",
    )
    p_cat.add_argument(
        "--catalog", metavar="PATH",
        help="Path to catalog JSON (default: output/pattern_catalog.json)",
    )
    p_cat.add_argument(
        "--tag", metavar="KEY",
        help="Show all stored phrases for one behavioral tag (e.g. stingy, giggle)",
    )
    p_cat.add_argument(
        "--remove", metavar="FUNSCRIPT",
        help="Remove the entry for a specific funscript name",
    )
    p_cat.add_argument(
        "--clear", action="store_true",
        help="Remove all entries from the catalog",
    )

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
        "pipeline":         cmd_pipeline,
        "assess":           cmd_assess,
        "transform":        cmd_transform,
        "phrase-transform": cmd_phrase_transform,
        "customize":        cmd_customize,
        "finalize":         cmd_finalize,
        "catalog":          cmd_catalog,
        "visualize":        cmd_visualize,
        "config":           cmd_config,
        "test":             cmd_test,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
