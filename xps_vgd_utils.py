from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
from vgd_reader import read_vgd

from xps_fitting.plotting.themes import _apply_figure_font_family, load_theme


def min_max_normalise(series: pd.Series) -> pd.Series:
    min_value = series.min()
    max_value = series.max()

    if max_value == min_value:
        return series * 0

    return (series - min_value) / (max_value - min_value)


def read_vgd_to_dataframe(vgd_path: str | Path) -> pd.DataFrame:
    vgd_path = Path(vgd_path)
    data = read_vgd(vgd_path)

    print(f"File: {vgd_path}")
    print(f"Number of spectra found: {len(data.spectra)}")

    if len(data.spectra) == 0:
        raise ValueError(f"No spectra found in {vgd_path}")

    dfs = []

    for spectrum in data.spectra:
        df_spectrum = pd.DataFrame({
            "binding_energy_eV": spectrum.binding_energy,
            "kinetic_energy_eV": spectrum.kinetic_energy,
            "intensity": spectrum.intensity,
            "corrected_intensity": spectrum.corrected_intensity,
        })

        df_spectrum["core_level"] = spectrum.core_level
        df_spectrum["spectrum_index"] = spectrum.spectrum_index
        df_spectrum["sample_id"] = spectrum.sample_id
        df_spectrum["title"] = spectrum.title
        df_spectrum["technique"] = spectrum.technique
        df_spectrum["source_energy_eV"] = spectrum.source_energy
        df_spectrum["pass_energy_eV"] = spectrum.pass_energy
        df_spectrum["dwell_time_s"] = spectrum.dwell_time
        df_spectrum["periods"] = spectrum.periods
        df_spectrum["txf_applied"] = spectrum.txf_applied
        df_spectrum["file"] = str(vgd_path)

        dfs.append(df_spectrum)

    return pd.concat(dfs, ignore_index=True)

def _normalise_sheet_name(core_level: str) -> str:
    """Convert parsed VGD core-level names into KherveFitting-compatible sheet names."""
    aliases = {
        "XPS_Survey": "Survey",
        "Survey": "Survey",
        "C1s": "C1s",
        "C1s_Scan": "C1s",
        "N1s": "N1s",
        "N1s_Scan": "N1s",
        "O1s": "O1s",
        "O1s_Scan": "O1s",
        "S2p": "S2p",
        "S2p_Scan": "S2p",
        "Zn2p": "Zn2p",
        "Zn2p_Scan": "Zn2p",
        "In3d": "In3d",
        "In3d_Scan": "In3d",
    }

    if core_level in aliases:
        return aliases[core_level]

    cleaned = core_level.replace(" ", "").replace("_Scan", "")
    return cleaned[:31]


def save_khervefitting_xlsx(
    xps_df: pd.DataFrame,
    output_dir: str | Path,
    output_name: str,
    intensity_column: str = "corrected_intensity",
) -> Path:
    """Save KherveFitting-compatible XLSX files.

    KherveFitting rejects default sheet names such as Sheet1. Each sheet is therefore
    named after the core level, such as C1s, N1s, S2p, or Survey. The first row uses
    the headers expected by KherveFitting: Binding Energy and Raw Data.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    required_columns = {"binding_energy_eV", intensity_column, "core_level", "spectrum_index"}
    missing_columns = required_columns.difference(xps_df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns for KherveFitting export: {sorted(missing_columns)}")

    xlsx_path = output_dir / f"{output_name}_for_khervefitting.xlsx"

    used_sheet_names: set[str] = set()

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        for (core_level, spectrum_index), group in xps_df.groupby(["core_level", "spectrum_index"]):
            sheet_name = _normalise_sheet_name(str(core_level))

            if sheet_name in used_sheet_names:
                sheet_name = f"{sheet_name}_{spectrum_index + 1}"[:31]

            used_sheet_names.add(sheet_name)

            kherve_df = group[["binding_energy_eV", intensity_column]].copy()
            kherve_df.columns = ["Binding Energy", "Raw Data"]
            kherve_df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"Saved KherveFitting XLSX to: {xlsx_path}")

    return xlsx_path

def add_normalised_intensity(
    xps_df: pd.DataFrame,
    intensity_column: str = "corrected_intensity",
) -> pd.DataFrame:
    xps_df = xps_df.copy()

    xps_df["normalised_intensity"] = (
        xps_df
        .groupby(["core_level", "spectrum_index"], group_keys=False)[intensity_column]
        .apply(min_max_normalise)
    )

    return xps_df


def save_xps_outputs(
    xps_df: pd.DataFrame,
    output_dir: str | Path,
    output_name: str,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    csv_path = output_dir / f"{output_name}_extracted.csv"
    xps_df.to_csv(csv_path, index=False)

    print(f"Saved CSV to: {csv_path}")

    return csv_path


def extract_peak_maximum(
    xps_df: pd.DataFrame,
    be_min: float,
    be_max: float,
    intensity_column: str = "corrected_intensity",
    smoothing_window: int = 5,
) -> pd.DataFrame:
    """Extract peak maximum position from a selected binding-energy window.

    This is useful for quick peak-position comparison of clean single core-level peaks.
    It is not a replacement for background-subtracted XPS peak fitting.
    """
    results = []

    for (core_level, spectrum_index), group in xps_df.groupby(["core_level", "spectrum_index"]):
        region = group[
            (group["binding_energy_eV"] >= be_min)
            & (group["binding_energy_eV"] <= be_max)
        ].copy()

        if region.empty:
            raise ValueError(f"No data found between {be_min} and {be_max} eV")

        region = region.sort_values("binding_energy_eV")

        region["smoothed_intensity"] = (
            region[intensity_column]
            .rolling(window=smoothing_window, center=True, min_periods=1)
            .mean()
        )

        max_row = region.loc[region["smoothed_intensity"].idxmax()]

        results.append({
            "core_level": core_level,
            "spectrum_index": spectrum_index,
            "peak_binding_energy_eV": max_row["binding_energy_eV"],
            "peak_intensity": max_row[intensity_column],
            "peak_smoothed_intensity": max_row["smoothed_intensity"],
            "be_min": be_min,
            "be_max": be_max,
            "intensity_column": intensity_column,
            "smoothing_window": smoothing_window,
        })

    return pd.DataFrame(results)


def plot_normalised_xps(
    xps_df: pd.DataFrame,
    output_dir: str | Path,
    output_name: str,
    figure_title: str,
    mode: str = "core_level",
    peak_df: pd.DataFrame | None = None,
    colour_map: dict[str, str] | None = None,
    figsize: tuple[float, float] | None = None,
    spine_width: float = 1.8,
    line_width: float = 2.0,
    save: bool = True,
) -> tuple[Path | None, Path | None]:
    """Plot normalised XPS spectra.

    mode="survey" is intended for wide survey scans.
    mode="core_level" is intended for high-resolution core-level scans.
    """

    if mode not in {"survey", "core_level"}:
        raise ValueError("mode must be either 'survey' or 'core_level'")

    if colour_map is not None and not isinstance(colour_map, dict):
        raise TypeError("colour_map must be a dictionary mapping core-level names to colour strings")

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    if figsize is None:
        figsize = (8, 6)

    fig_path_png = output_dir / f"{output_name}_normalized.png" if save else None
    fig_path_pdf = output_dir / f"{output_name}_normalized.pdf" if save else None

    fig, ax = plt.subplots(figsize=figsize, facecolor="white")
    ax.set_facecolor("white")

    for spine in ax.spines.values():
        spine.set_linewidth(spine_width)
        spine.set_color("black")

    for (core_level, spectrum_index), group in xps_df.groupby(["core_level", "spectrum_index"]):
        if mode == "survey":
            label = f"{core_level}"
        else:
            label = f"{core_level} #{spectrum_index + 1}"

        if mode == "survey":
            colour = "#111810"
        elif colour_map is not None:
            colour = colour_map.get(core_level)
        else:
            colour = None

        ax.plot(
            group["binding_energy_eV"],
            group["normalised_intensity"],
            lw=line_width,
            label=label,
            color=colour,
        )

    if mode == "core_level" and peak_df is not None and not peak_df.empty:
        peak_be = peak_df.loc[0, "peak_binding_energy_eV"]

        ax.axvline(
            peak_be,
            linestyle="--",
            linewidth=spine_width,
            label=f"Peak max = {peak_be:.2f} eV",
            color=colour,
        )

    ax.invert_xaxis()
    ax.margins(x=0)
    ax.set_xlabel("Binding energy (eV)", fontsize=22, fontweight="bold", color="black")
    ax.set_ylabel("Normalized intensity (a.u.)", fontsize=22, fontweight="bold", color="black")
    ax.set_title(figure_title, fontsize=18, fontweight="bold", color="black")
    ax.tick_params(axis="x", colors="black", labelsize=14, width=spine_width)
    ax.tick_params(axis="y", colors="black", labelsize=14, width=spine_width)

    for tick_label in ax.get_xticklabels():
        tick_label.set_fontweight("bold")
        tick_label.set_color("black")

    if mode == "survey":
        for tick_label in ax.get_yticklabels():
            tick_label.set_fontweight("bold")
            tick_label.set_color("black")
    else:
        ax.set_yticks([])
        legend = ax.legend(frameon=True, prop={"size": 12, "weight": "bold"}, loc="upper left")
        legend.get_frame().set_edgecolor("black")
        legend.get_frame().set_linewidth(1.0)
        legend.get_frame().set_facecolor("white")
        legend.get_frame().set_alpha(1.0)
        if legend is not None:
            for text in legend.get_texts():
                text.set_color("black")

    fig.tight_layout()
    theme = load_theme("angze_publication")
    _apply_figure_font_family(fig, theme.font_family)

    with mpl.rc_context(theme.font_rc_params()):
        if save:
            fig.savefig(fig_path_png, dpi=300, bbox_inches="tight", facecolor="white")
            fig.savefig(fig_path_pdf, bbox_inches="tight", facecolor="white")

        plt.show()

    if save:
        print(f"Saved figure to: {fig_path_png}")
        print(f"Saved figure to: {fig_path_pdf}")

    return fig_path_png, fig_path_pdf
