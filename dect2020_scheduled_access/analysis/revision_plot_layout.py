"""Compact, reproducible vector/raster export for MDPI revision figures.

Only figure styling/cropping; this module does not read or modify data.
Captions remain in the LaTeX manuscript, not duplicated by oversized titles.
"""
from pathlib import Path


def save_compact(fig, output, stem, dpi=500):
    """Export a full-data figure with efficient margins and no clipped labels."""
    output=Path(output)
    for ax in fig.axes:
        ax.tick_params(axis="both", which="major", labelsize=8, pad=2,
                       length=3, width=.7)
        ax.xaxis.label.set_fontsize(9.5)
        ax.yaxis.label.set_fontsize(9.5)
        if ax.get_title():
            ax.set_title(ax.get_title(),fontsize=9,pad=3)
        legend=ax.get_legend()
        if legend is not None:
            for txt in legend.get_texts():
                txt.set_fontsize(7.5)
    fig.tight_layout(pad=.55)
    for ext in (".pdf",".png"):
        fig.savefig(output/(stem+ext),
                    dpi=dpi if ext==".png" else None,
                    bbox_inches="tight", pad_inches=.065,
                    facecolor="white")
