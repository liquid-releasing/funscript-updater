"""Pipeline orchestration helper for the Funscript Updater.

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

import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Allow imports from the project root regardless of CWD.
_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from suggested_updates import FunscriptTransformer, TransformerConfig
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
        :class:`~suggested_updates.TransformerConfig` defaults.
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
