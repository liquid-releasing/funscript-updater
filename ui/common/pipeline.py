# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Pipeline orchestration helper for the Funscript Forge.

Provides a single entry point that chains the three core pipeline stages:

  1. Assessment  — FunscriptAnalyzer → AssessmentResult
  2. Transform   — FunscriptTransformer → transformed funscript
  3. Customize   — WindowCustomizer (with project's work-item windows) → final funscript

Typical usage::

    from ui.common.pipeline import run_pipeline
    from ui.common.project import Project

    project = Project.from_funscript("input.funscript")
    # … user reviews and types work items …
    result = run_pipeline(project, output_dir="output/")
    print(result.transformed_path)
    print(result.customized_path)
"""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Allow imports from the project root regardless of CWD.
_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from pattern_catalog import FunscriptTransformer, TransformerConfig
from user_customization import WindowCustomizer, CustomizerConfig


@dataclass
class PipelineResult:
    """Paths and log lines produced by a completed pipeline run.

    Attributes
    ----------
    transformed_path:
        Path to the transformer output funscript (Stage 2).
    customized_path:
        Path to the customizer output funscript (Stage 3), or ``None`` if
        no typed work items were present.
    assessment_path:
        Path to the saved assessment JSON (if ``save_assessment`` was True).
    window_paths:
        Dict mapping window type (``"performance"``, ``"break"``, ``"raw"``)
        to the exported JSON file path.
    log:
        Concatenated log lines from all three stages.
    """

    transformed_path: str = ""
    customized_path: Optional[str] = None
    assessment_path: Optional[str] = None
    window_paths: Dict[str, str] = field(default_factory=dict)
    log: List[str] = field(default_factory=list)


def run_pipeline(
    project: "Project",  # noqa: F821 — avoid circular import at module level
    output_dir: str,
    *,
    transformer_config: Optional[TransformerConfig] = None,
    customizer_config: Optional[CustomizerConfig] = None,
    save_assessment: bool = True,
    beats_path: Optional[str] = None,
) -> PipelineResult:
    """Run all three pipeline stages and write outputs to *output_dir*.

    Parameters
    ----------
    project:
        A loaded :class:`~ui.common.project.Project` with ``assessment``
        populated (call ``Project.from_funscript()`` first).
    output_dir:
        Directory where output files are written (created if absent).
    transformer_config:
        Optional custom settings for Stage 2.  Defaults to
        :class:`~pattern_catalog.TransformerConfig` defaults.
    customizer_config:
        Optional custom settings for Stage 3.  Defaults to
        :class:`~user_customization.CustomizerConfig` defaults.
    save_assessment:
        When ``True`` (default), write the assessment JSON to *output_dir*.
    beats_path:
        Optional path to a beats JSON file for the customizer's beat-accent
        feature.

    Returns
    -------
    PipelineResult
        Paths to all output files and merged log lines.
    """
    if project.assessment is None:
        raise RuntimeError(
            "Project has no assessment — call Project.from_funscript() or "
            "project.run_assessment() before running the pipeline."
        )

    os.makedirs(output_dir, exist_ok=True)
    base = project.name
    result = PipelineResult()

    # ------------------------------------------------------------------
    # (optional) Save assessment JSON
    # ------------------------------------------------------------------
    if save_assessment:
        apath = os.path.join(output_dir, f"{base}.assessment.json")
        project.assessment.save(apath)
        result.assessment_path = apath
        result.log.append(f"Assessment saved: {apath}")

    # ------------------------------------------------------------------
    # Stage 2 — Transform
    # ------------------------------------------------------------------
    transformed_path = os.path.join(output_dir, f"{base}.transformed.funscript")
    transformer = FunscriptTransformer(config=transformer_config or TransformerConfig())
    transformer.load_funscript(project.funscript_path)
    transformer.load_assessment(project.assessment)
    transformer.transform()
    transformer.save(transformed_path)
    result.transformed_path = transformed_path
    result.log.extend(transformer.get_log())

    # ------------------------------------------------------------------
    # Stage 3 — Customize
    # ------------------------------------------------------------------
    # Export work-item windows to JSON files in output_dir.
    window_paths = project.export_windows(output_dir)
    result.window_paths = window_paths

    customized_path = os.path.join(output_dir, f"{base}.customized.funscript")
    customizer = WindowCustomizer(config=customizer_config or CustomizerConfig())
    customizer.load_funscript(transformed_path)
    customizer.load_assessment(project.assessment)

    customizer.load_manual_overrides(
        perf_path=window_paths.get("performance"),
        break_path=window_paths.get("break"),
        raw_path=window_paths.get("raw"),
    )

    if beats_path:
        customizer.load_beats_from_file(beats_path)

    customizer.customize()
    customizer.save(customized_path)
    result.customized_path = customized_path
    result.log.extend(customizer.get_log())

    return result


def run_pipeline_in_memory(
    funscript_path: str,
    assessment: "AssessmentResult",  # noqa: F821
    transformer_config: Optional[TransformerConfig] = None,
    customizer_config: Optional[CustomizerConfig] = None,
    performance_windows: Optional[List[dict]] = None,
    break_windows: Optional[List[dict]] = None,
    raw_windows: Optional[List[dict]] = None,
) -> Tuple[list, dict]:
    """Run FunscriptTransformer → WindowCustomizer entirely in memory.

    Intended for the Streamlit Export panel where writing final output files
    is handled by ``st.download_button`` rather than ``save()``.

    Parameters
    ----------
    funscript_path : str
        Path to the source ``.funscript`` file.
    assessment : AssessmentResult
        Pre-computed assessment (phrases for transformer; cycles for customizer).
    transformer_config : TransformerConfig, optional
        BPM-threshold transformer settings. Uses defaults if omitted.
    customizer_config : CustomizerConfig, optional
        Window customizer settings. Uses defaults if omitted.
    performance_windows, break_windows, raw_windows : list of dict, optional
        Window dicts as returned by ``project.performance_windows()`` etc.
        Each dict must have ``"start"`` / ``"end"`` as HH:MM:SS.mmm strings.

    Returns
    -------
    (actions, log) : Tuple[list, dict]
        ``actions`` — final transformed actions list.
        ``log``     — summary dict suitable for embedding in the export JSON.
    """
    tcfg = transformer_config or TransformerConfig()

    # ------------------------------------------------------------------
    # Stage 1: BPM Transformer
    # ------------------------------------------------------------------
    transformer = FunscriptTransformer(config=tcfg)
    transformer.load_funscript(funscript_path)
    transformer.load_assessment(assessment)
    transformed_actions = transformer.transform()

    # ------------------------------------------------------------------
    # Stage 2: WindowCustomizer (only when windows or explicit config given)
    # ------------------------------------------------------------------
    has_windows = any([performance_windows, break_windows, raw_windows])
    ccfg = customizer_config or CustomizerConfig()

    if has_windows or customizer_config is not None:
        # Hand off Stage 1 output via a temp file (customizer requires a path)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".funscript", delete=False, encoding="utf-8"
        ) as tmp_fs:
            json.dump({"actions": copy.deepcopy(transformed_actions)}, tmp_fs)
            tmp_fs_path = tmp_fs.name

        try:
            customizer = WindowCustomizer(config=ccfg)
            customizer.load_funscript(tmp_fs_path)
            customizer.load_assessment(assessment)

            with tempfile.TemporaryDirectory() as tmp_dir:
                def _write_windows(windows: Optional[List[dict]], filename: str) -> Optional[str]:
                    if not windows:
                        return None
                    path = os.path.join(tmp_dir, filename)
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(windows, f)
                    return path

                customizer.load_manual_overrides(
                    perf_path=_write_windows(performance_windows, "performance.json"),
                    break_path=_write_windows(break_windows, "break.json"),
                    raw_path=_write_windows(raw_windows, "raw.json"),
                )
                final_actions = customizer.customize()
        finally:
            os.unlink(tmp_fs_path)
    else:
        final_actions = transformed_actions

    log = {
        "transformer": {
            "bpm_threshold":   tcfg.bpm_threshold,
            "amplitude_scale": tcfg.amplitude_scale,
            "lpf_default":     tcfg.lpf_default,
            "time_scale":      tcfg.time_scale,
        },
        "customizer_applied": has_windows or customizer_config is not None,
        "windows": {
            "performance": len(performance_windows or []),
            "break":       len(break_windows       or []),
            "raw":         len(raw_windows         or []),
        },
    }
    return final_actions, log
