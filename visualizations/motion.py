"""MotionVisualizer: plots the raw motion curve and phase boundaries.

Requires matplotlib. Install with: pip install matplotlib
"""

from models import AssessmentResult

try:
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class MotionVisualizer:
    """Renders a motion + phase-boundary plot from a funscript and its assessment.

    Usage::

        viz = MotionVisualizer(assessment, actions)
        viz.plot("output.png")
    """

    def __init__(self, assessment: AssessmentResult, actions: list):
        self.assessment = assessment
        self.actions = actions

    def plot(self, output_path: str) -> None:
        """Save a visualization PNG to output_path."""
        if not HAS_MATPLOTLIB:
            raise RuntimeError(
                "matplotlib is required for visualization. "
                "Install it with: pip install matplotlib"
            )

        times = [a["at"] for a in self.actions]
        positions = [a["pos"] for a in self.actions]
        a = self.assessment

        fig, ax = plt.subplots(figsize=(20, 5))

        # --- Phase boundary tick marks ---
        for phase in a.phases:
            ax.axvline(phase.start_ms, color="gray", linewidth=0.3, alpha=0.3, zorder=1)

        # --- Motion curve on top ---
        ax.plot(times, positions, color="steelblue", linewidth=0.7, zorder=2, label="motion")

        # --- X-axis: format ms as MM:SS ---
        def _fmt_ms(x, _):
            ms = int(x)
            minutes = ms // 60_000
            seconds = (ms % 60_000) // 1_000
            return f"{minutes}:{seconds:02d}"

        ax.xaxis.set_major_formatter(ticker.FuncFormatter(_fmt_ms))
        ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=20, integer=True))
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)

        ax.set_title(f"Funscript Motion — {a.source_file}  |  {a.bpm:.1f} BPM avg")
        ax.set_xlabel("Time (MM:SS)")
        ax.set_ylabel("Position (0-100)")
        ax.set_ylim(-5, 112)

        ax.legend(loc="upper right", fontsize=7)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
