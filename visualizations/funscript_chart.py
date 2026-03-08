"""funscript_chart.py — Reusable Plotly-based funscript chart widget.

Renders a single funscript channel as a colour-coded line chart with
phrase annotation boxes and an optional selection highlight.

Requirements
------------
    pip install plotly
"""

from __future__ import annotations

from math import ceil
from typing import List, Optional, Tuple

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


# When the zoom window contains more action points than this threshold,
# fall back to coloured markers only (no per-segment traces).
# Below the threshold, each segment is drawn as its own coloured trace,
# giving a full velocity/amplitude heatmap on the line itself.
# 600 comfortably covers a 60-second zoomed phrase at typical funscript density.
_MAX_SEGMENT_TRACES = 600


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
        view_state,
        key: str = "chart",
        height: int = 300,
    ):
        """Render the chart inside a Streamlit app.

        Returns the Plotly event dict (may be None or empty).
        """
        import streamlit as st

        if not HAS_PLOTLY:
            st.warning("plotly is not installed — run `pip install plotly`.")
            return None

        fig = self._build_figure(view_state, height)
        try:
            event = st.plotly_chart(
                fig,
                key=key,
                on_select="rerun",
                selection_mode=["points", "box"],
                use_container_width=True,
            )
        except TypeError:
            # Newer Streamlit removed use_container_width from plotly_chart
            event = st.plotly_chart(
                fig,
                key=key,
                on_select="rerun",
                selection_mode=["points", "box"],
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
            zoom_start = s.times_ms[0]  if s.times_ms else 0
            zoom_end   = s.times_ms[-1] if s.times_ms else self.duration_ms

        colors = s.colors_velocity if color_mode == "velocity" else s.colors_amplitude

        fig = go.Figure()

        # --- Annotation bands ---
        enabled_kinds = view_state.enabled_kinds()
        # Phrases are always shown as boxed regions
        enabled_with_phrases = set(enabled_kinds) | {"phrase"}

        for band in visible_bands:
            if band.kind not in enabled_with_phrases:
                continue

            if band.kind == "phrase":
                # Highlight selected phrase differently
                is_selected = (
                    view_state.has_selection()
                    and view_state.selection_start_ms == band.start_ms
                    and view_state.selection_end_ms   == band.end_ms
                )
                border = "rgba(255,220,50,0.9)"  if is_selected else "rgba(218,112,214,0.55)"
                fill   = "rgba(255,220,50,0.07)" if is_selected else "rgba(218,112,214,0.07)"
                fig.add_vrect(
                    x0=band.start_ms, x1=band.end_ms,
                    fillcolor=fill,
                    line_width=1, line_color=border,
                    layer="below",
                    annotation_text=band.label[:30],
                    annotation_position="top left",
                    annotation_font_size=9,
                    annotation_font_color=border,
                )

            elif band.kind == "transition":
                fig.add_vline(
                    x=band.start_ms,
                    line_width=1, line_dash="dash",
                    line_color="rgba(255,99,71,0.65)",
                    annotation_text=band.label,
                    annotation_position="top right",
                    annotation_font_size=8,
                )

            else:
                fig.add_vrect(
                    x0=band.start_ms, x1=band.end_ms,
                    fillcolor=band.color, layer="below",
                    line_width=0,
                    annotation_text=band.label[:20],
                    annotation_position="top left",
                    annotation_font_size=8,
                )

        # --- Selection dim (outside selection) ---
        if view_state.has_selection():
            sel_s = view_state.selection_start_ms
            sel_e = view_state.selection_end_ms
            if sel_s > zoom_start:
                fig.add_vrect(
                    x0=zoom_start, x1=sel_s,
                    fillcolor="rgba(0,0,0,0.25)", layer="above", line_width=0,
                )
            if sel_e < zoom_end:
                fig.add_vrect(
                    x0=sel_e, x1=zoom_end,
                    fillcolor="rgba(0,0,0,0.25)", layer="above", line_width=0,
                )

        # --- Motion line ---
        n = len(s.times_ms)

        if n > 1 and (n - 1) <= _MAX_SEGMENT_TRACES:
            # Per-segment coloured lines — each segment gets the colour of
            # its start point, giving a velocity/amplitude heat-map effect.
            for i in range(n - 1):
                fig.add_trace(go.Scatter(
                    x=[s.times_ms[i], s.times_ms[i + 1]],
                    y=[s.positions[i], s.positions[i + 1]],
                    mode="lines",
                    line=dict(color=colors[i], width=2),
                    showlegend=False,
                    hoverinfo="skip",
                ))
            # Markers on top for hover and point-click detection
            fig.add_trace(go.Scatter(
                x=s.times_ms,
                y=s.positions,
                mode="markers",
                marker=dict(color=colors, size=5, line=dict(width=0)),
                hovertemplate="t=%{x} ms  pos=%{y}<extra></extra>",
                name=self.title,
            ))

        elif n > 0:
            # Full-view fallback: coloured markers only — too many points for
            # per-segment traces, but coloured dots still show the heatmap.
            fig.add_trace(go.Scatter(
                x=s.times_ms,
                y=s.positions,
                mode="markers",
                marker=dict(color=colors, size=4, line=dict(width=0)),
                hovertemplate="t=%{x} ms  pos=%{y}<extra></extra>",
                name=self.title,
            ))

        # --- Layout ---
        tickvals, ticktext = _compute_ticks(zoom_start, zoom_end)

        fig.update_layout(
            title=dict(text=self.title, font=dict(size=12)) if self.title else None,
            height=height,
            margin=dict(l=45, r=10, t=30 if self.title else 10, b=30),
            paper_bgcolor="#0e1117",
            plot_bgcolor="#1a1d23",
            font=dict(color="#cccccc"),
            xaxis=dict(
                title=None,
                range=[zoom_start, zoom_end],
                color="#aaaaaa",
                gridcolor="#2a2d35",
                tickvals=tickvals,
                ticktext=ticktext,
                tickangle=0,
            ),
            yaxis=dict(
                title="pos",
                range=[-2, 102],
                color="#aaaaaa",
                gridcolor="#2a2d35",
            ),
            showlegend=False,
            dragmode="pan",   # drag to scroll left/right; click a point to select phrase
        )

        return fig


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _compute_ticks(start_ms: int, end_ms: int) -> Tuple[List[int], List[str]]:
    """Return (tickvals, ticktext) for a human-readable time axis."""
    span = end_ms - start_ms
    if   span > 600_000: step = 60_000
    elif span > 120_000: step = 30_000
    elif span > 30_000:  step = 10_000
    elif span > 10_000:  step = 5_000
    elif span > 3_000:   step = 1_000
    else:                step = 500

    first = ceil(start_ms / step) * step
    vals  = list(range(first, end_ms + 1, step))
    texts = [_format_ms(v) for v in vals]
    return vals, texts


def _format_ms(ms: int) -> str:
    """Format milliseconds as M:SS or M:SS.t (tenths of a second)."""
    total_s = ms // 1000
    m  = total_s // 60
    s  = total_s % 60
    sub = ms % 1000
    if sub == 0:
        return f"{m}:{s:02d}"
    return f"{m}:{s:02d}.{sub // 100}"
