"""funscript_chart.py — Reusable Plotly-based funscript chart widget.

Renders a single funscript channel as a colour-coded line chart with
optional assessment annotation bands and a selection highlight.

Designed to be instantiated once per panel and called via
``render_streamlit()`` which returns any Plotly selection event data
for the caller to act on.

Requirements
------------
    pip install plotly

The ``HAS_PLOTLY`` flag lets callers degrade gracefully if plotly is not
installed.
"""

from __future__ import annotations

from typing import List, Optional

from visualizations.chart_data import (
    AnnotationBand,
    PointSeries,
    slice_bands,
    slice_series,
)

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


# Height of each annotation row band as a fraction of the [0,100] y-axis
_BAND_HEIGHT = 4.0   # position units per row band
_BAND_BASE   = 101.0  # y position where annotation rows start (above the chart)


class FunscriptChart:
    """Renders a single funscript panel.

    Parameters
    ----------
    series:
        Pre-computed :class:`~visualizations.chart_data.PointSeries`.
    bands:
        Pre-computed annotation bands (all of them — filtering by enabled
        kinds happens inside the render call).
    title:
        Panel title shown at the top.
    duration_ms:
        Full funscript duration.  Used to set the default x-axis range.
    """

    def __init__(
        self,
        series: PointSeries,
        bands: List[AnnotationBand],
        title: str = "",
        duration_ms: int = 0,
    ) -> None:
        self.series = series
        self.bands = bands
        self.title = title
        self.duration_ms = duration_ms

    # ------------------------------------------------------------------
    # Streamlit rendering
    # ------------------------------------------------------------------

    def render_streamlit(
        self,
        view_state,           # ViewState — imported lazily to avoid circular dep
        key: str = "chart",
        height: int = 300,
    ):
        """Render the chart inside a Streamlit app.

        Returns the Plotly selection event dict (may be None or empty).
        Requires plotly and streamlit to be installed.
        """
        import streamlit as st

        if not HAS_PLOTLY:
            st.warning("plotly is not installed — run `pip install plotly`.")
            return None

        fig = self._build_figure(view_state, height)
        event = st.plotly_chart(
            fig,
            key=key,
            on_select="rerun",
            selection_mode="box",
            use_container_width=True,
        )
        return event

    # ------------------------------------------------------------------
    # Figure construction
    # ------------------------------------------------------------------

    def _build_figure(self, view_state, height: int) -> "go.Figure":
        zoom_start = view_state.zoom_start_ms
        zoom_end   = view_state.zoom_end_ms
        color_mode = view_state.color_mode

        # Slice data to zoom window
        if view_state.has_zoom():
            s = slice_series(self.series, zoom_start, zoom_end)
            visible_bands = slice_bands(self.bands, zoom_start, zoom_end)
        else:
            s = self.series
            visible_bands = self.bands
            zoom_start = s.times_ms[0] if s.times_ms else 0
            zoom_end   = s.times_ms[-1] if s.times_ms else self.duration_ms

        colors = s.colors_velocity if color_mode == "velocity" else s.colors_amplitude

        fig = go.Figure()

        # --- Annotation bands (background) ---
        enabled_kinds = view_state.enabled_kinds()
        for band in visible_bands:
            if band.kind not in enabled_kinds:
                continue
            if band.kind == "transition":
                # Vertical line marker
                fig.add_vline(
                    x=band.start_ms,
                    line_width=2,
                    line_dash="dash",
                    line_color="rgba(255,99,71,0.8)",
                    annotation_text=band.label,
                    annotation_position="top right",
                    annotation_font_size=9,
                )
            else:
                fig.add_vrect(
                    x0=band.start_ms,
                    x1=band.end_ms,
                    fillcolor=band.color,
                    layer="below",
                    line_width=0,
                    annotation_text=band.label[:20],
                    annotation_position="top left",
                    annotation_font_size=8,
                )

        # --- Selection highlight ---
        if view_state.has_selection():
            sel_s = view_state.selection_start_ms
            sel_e = view_state.selection_end_ms
            # Outside-selection dim
            if sel_s > zoom_start:
                fig.add_vrect(
                    x0=zoom_start, x1=sel_s,
                    fillcolor="rgba(0,0,0,0.30)", layer="above",
                    line_width=0,
                )
            if sel_e < zoom_end:
                fig.add_vrect(
                    x0=sel_e, x1=zoom_end,
                    fillcolor="rgba(0,0,0,0.30)", layer="above",
                    line_width=0,
                )
            # Selection border
            fig.add_vrect(
                x0=sel_s, x1=sel_e,
                fillcolor="rgba(255,255,255,0.05)",
                line_width=2, line_color="rgba(255,255,255,0.8)",
                layer="above",
            )

        # --- Motion line ---
        if s.times_ms:
            fig.add_trace(go.Scatter(
                x=s.times_ms,
                y=s.positions,
                mode="lines+markers",
                marker=dict(
                    color=colors,
                    size=4,
                    showscale=False,
                ),
                line=dict(color="rgba(200,200,200,0.4)", width=1),
                hovertemplate=(
                    "t=%{x} ms<br>pos=%{y}<extra></extra>"
                ),
                name=self.title,
            ))

        # --- Layout ---
        fig.update_layout(
            title=dict(text=self.title, font=dict(size=12)),
            height=height,
            margin=dict(l=40, r=10, t=30, b=30),
            paper_bgcolor="#0e1117",
            plot_bgcolor="#1a1d23",
            font=dict(color="#cccccc"),
            xaxis=dict(
                title="Time (ms)",
                range=[zoom_start, zoom_end],
                color="#aaaaaa",
                gridcolor="#2a2d35",
                tickformat=_ms_tickformat(zoom_end - zoom_start),
            ),
            yaxis=dict(
                title="Position",
                range=[-2, 102],
                color="#aaaaaa",
                gridcolor="#2a2d35",
            ),
            showlegend=False,
            dragmode="select",   # box-select by default
        )

        return fig


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _ms_tickformat(span_ms: int) -> str:
    """Choose a readable x-axis tick format based on the visible span."""
    if span_ms > 60_000:
        return "%M:%S"
    if span_ms > 5_000:
        return "%S.%L s"
    return "%L ms"
