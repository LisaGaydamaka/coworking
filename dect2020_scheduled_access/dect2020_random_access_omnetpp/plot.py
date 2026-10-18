"""Plotting starter: implement extraction and grouping of OMNeT++ scalars."""

from pathlib import Path

PROJECT = Path(__file__).resolve().parent
SCALARS = PROJECT / "results"
FIGURES = PROJECT / "figures"


def load_experiments(directory: Path):
    # TODO: Read .sca files and collect run parameters and scalar metrics.
    raise NotImplementedError("Implement OMNeT++ scalar parsing")


def plot_figures(experiments):
    # TODO: Reproduce the required parameter-vs-metric plots.
    # TODO: Add correct symbol units, legends and figure names.
    raise NotImplementedError("Implement experimental plots")


if __name__ == "__main__":
    plot_figures(load_experiments(SCALARS))
