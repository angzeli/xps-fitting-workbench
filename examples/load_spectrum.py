"""Exercise DataFrame, CSV, XLSX, and optional tracked VGD spectrum loading."""

import argparse

import pandas as pd
from _shared import ROOT, add_output_argument, check_output_paths, prepare_output

from xps_fitting.io import read_csv, read_xlsx, spectrum_from_dataframe


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_output_argument(parser)
    args = parser.parse_args(argv)
    output = prepare_output(args.output_dir)

    frame = pd.DataFrame({"energy": [286.0, 285.0, 285.0, "bad", 284.0], "counts": [1, 3, 5, 9, 2]})
    dataframe_spectrum = spectrum_from_dataframe(frame, "energy", "counts", region="C 1s", sample_name="synthetic")
    table = pd.DataFrame(
        {"binding_energy_eV": dataframe_spectrum.binding_energy, "intensity": dataframe_spectrum.intensity}
    )
    csv_path, xlsx_path = output / "synthetic_c1s.csv", output / "synthetic_c1s.xlsx"
    check_output_paths([csv_path, xlsx_path], overwrite=args.overwrite)
    table.to_csv(csv_path, index=False)
    table.to_excel(xlsx_path, index=False)
    csv_spectrum, xlsx_spectrum = read_csv(csv_path), read_xlsx(xlsx_path)

    vgd_summary = "optional VGD skipped (vgd-reader unavailable)"
    try:
        from xps_fitting.io_vgd import read_vgd

        experimental = read_vgd(ROOT / "example_data/PDI-H-COOH/C1s Scan.VGD")
        vgd_summary = f"tracked experimental VGD: {experimental.binding_energy.size} points"
    except ImportError:
        pass

    print(
        f"DataFrame/CSV/XLSX: {csv_spectrum.binding_energy.size}/{xlsx_spectrum.binding_energy.size} ordered synthetic points; {vgd_summary}"
    )
    print(f"Created: {csv_path}, {xlsx_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
