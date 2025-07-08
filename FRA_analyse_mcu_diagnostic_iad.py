import os
from re import split

import pandas as pd
import glob
import matplotlib.pyplot as plt
import numpy as np


# produces one file res.csv that contains all IAD rows
# produces SNXXXXXXXX file that contains IAD rows of each serial number
# Each IAD row will have structure listed in iad_headers array
# Turn off One Drive Synchronization while running this function
# noinspection DuplicatedCode
def mcu_diagnostic_alert_to_iad(data_dir, output_dir: str, to_feather=False):
    """IAD diagnostic alert"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir,exist_ok=True)

    iad_headers = [
        "DATE",
        "IAD",
        "flags_when_air_detected",
        "last_bubble_count",
        "accumulated_bubble_count",
        "delta_time_in_ms",
        "inject_progress",
        "fill_state_machine"]

    df_dict = dict()
    for data_csv in glob.glob(os.path.join(data_dir, "*.csv")):
        df = pd.read_csv(data_csv)
        df['ActiveAt'] = pd.to_datetime(df['ActiveAt'], utc=True, format='ISO8601')
        print("Processing", data_csv)
        serial = os.path.basename(data_csv).split("_")[1]

        single_file_entries = []
        for index, df_row in df.iterrows():
            if "IAD:" not in str(df_row.Data):
                continue
            diagnostic_fields = df_row.Data.split('|')
            for field in filter(lambda x: "IAD:" in x, diagnostic_fields):
                # data is in the form "06:23:33.321321:IAD...
                start = field.find("IAD:")
                # attempt to fix non-well formed data because some data has date string, some don't (old data)
                time_str = ""
                if start != 0:
                    time_str = field[:start].strip()   # "06:23:33.321321:"
                    time_str = time_str[:-1]   # "06:23:33.321321"

                if len(time_str) > 0:
                    date_start = str(df_row.ActiveAt).split(" ")[0].strip() + " " + time_str
                else:
                    date_start = str(df_row.ActiveAt)
                date_start = date_start.split("+")[0]

                row = [date_start] + [int(x) for x in field[start:].strip().split(':')[1:]]
                if len(row) != len(iad_headers):
                    print("IAD error:", field, row, len(row))
                    continue
                single_file_entries.append(row)

        sdf = pd.DataFrame(single_file_entries, columns=iad_headers)
        sdf['DATE'] = pd.to_datetime(sdf['DATE'], utc=True, format='ISO8601')
        if serial not in df_dict:
            df_dict[serial] = sdf
        else:
            df_dict[serial] = pd.concat([df_dict[serial], sdf])

    names = []
    summary = []
    for sn, df in df_dict.items():
        df["SN"] = sn
        df.sort_values(by=['DATE'], inplace=True)
        if to_feather:
            output_name = os.path.join(output_dir, f"{sn}_IAD.feather")
            df.reset_index(inplace=True)
            df.to_feather(output_name)
        else:
            output_name = os.path.join(output_dir, f"{sn}_IAD.csv")
            df.to_csv(output_name, index=False)
        print("Created", output_name)
        names.append(output_name)
        summary.append([sn, len(df), df.DATE.min(), df.DATE.max()])

    summary_df = pd.DataFrame(summary, columns=["SN", "Count", "Start", "End"])
    output_name = os.path.join(output_dir, "McuDiagnostic_IAD_summary.csv")
    summary_df.to_csv(output_name, index=False)
    print("Created", output_name)
    return names


# noinspection DuplicatedCode
def mcu_diagnostic_alert_to_iad_adc(data_dir, output_dir: str, to_feather=False):
    """IADadc diagnostic alert"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir,exist_ok=True)

    iad_headers = [
        "DATE",
        "IAD",
        "ADC",
        "IrK_adc"
    ]

    df_dict = dict()
    for data_csv in glob.glob(os.path.join(data_dir, "*.csv")):
        df = pd.read_csv(data_csv)
        df['ActiveAt'] = pd.to_datetime(df['ActiveAt'], utc=True, format='ISO8601')
        print("Processing", data_csv)
        serial = os.path.basename(data_csv).split("_")[1]

        single_file_entries = []
        for index, df_row in df.iterrows():
            if "IADadc:" not in str(df_row.Data):
                continue
            diagnostic_fields = df_row.Data.split('|')
            for field in filter(lambda x: "IADadc:" in x, diagnostic_fields):
                # data is in the form "06:23:33.321321:IADadc:...
                start = field.find("IADadc:")
                # attempt to fix non-well formed data because some data has date string, some don't (old data)
                time_str = ""
                if start != 0:
                    time_str = field[:start].strip()   # "06:23:33.321321:"
                    time_str = time_str[:-1]   # "06:23:33.321321"

                if len(time_str) > 0:
                    date_start = str(df_row.ActiveAt).split(" ")[0].strip() + " " + time_str
                else:
                    date_start = str(df_row.ActiveAt)
                date_start = date_start.split("+")[0]

                row = [date_start] + [int(x) for x in field[start:].strip().split(':')[1:]]
                if len(row) != len(iad_headers):
                    print("IAD adc error:", field, row, len(row))
                    continue
                single_file_entries.append(row)

        sdf = pd.DataFrame(single_file_entries, columns=iad_headers)
        sdf['DATE'] = pd.to_datetime(sdf['DATE'], utc=True, format='ISO8601')
        if serial not in df_dict:
            df_dict[serial] = sdf
        else:
            df_dict[serial] = pd.concat([df_dict[serial], sdf])

    names = []
    summary = []
    for sn, df in df_dict.items():
        df["SN"] = sn
        df.sort_values(by=['DATE'], inplace=True)
        if to_feather:
            output_name = os.path.join(output_dir, f"{sn}_IAD_ADC.feather")
            df.reset_index(inplace=True)
            df.to_feather(output_name)
        else:
            output_name = os.path.join(output_dir, f"{sn}_IAD_ADC.csv")
            df.to_csv(output_name, index=False)
        print("Created", output_name)
        names.append(output_name)
        summary.append([sn, len(df), df.DATE.min(), df.DATE.max()])

    summary_df = pd.DataFrame(summary, columns=["SN", "Count", "Start", "End"])
    output_name = os.path.join(output_dir, "McuDiagnostic_IAD_ADC_summary.csv")
    summary_df.to_csv(output_name, index=False)
    print("Created", output_name)
    return names


# noinspection DuplicatedCode
def plot_iad_adc_csv(csv_filename: str, output_dir=None):
    df = pd.read_csv(csv_filename)
    # print("header", df.columns)

    if len(df) < 20:
        return False

    basename = os.path.splitext(os.path.basename(csv_filename))[0]
    basename = basename.split("_")[0]  # remove postfix
    df.DATE = pd.to_datetime(df.DATE, format='mixed')
    df = df.sort_values(by='DATE')

    fig, axes = plt.subplots(3, 1, figsize=(14, 8), tight_layout=True, sharex=True)
    # ax0, ax1 = axes
    ids = sorted(list(df.IAD.unique()))
    iad_names = ["S0", "C1", "C2"]

    for iad_id in ids:
        fdf = df[df.IAD == iad_id]
        axes[iad_id].scatter(fdf.DATE, fdf.ADC, color="blue", label="Voltage")
        axes[iad_id].scatter(fdf.DATE, fdf.IrK_adc, color='green', label="Current")
        axes[iad_id].set_ylabel(f"ADC count for index {iad_names[iad_id]}")
        axes[iad_id].grid()
        axes[iad_id].legend()
        axes[iad_id].set_xlabel(None)
    axes[2].tick_params(axis='x', labelrotation=90)

    if output_dir:
        output_name = os.path.join(output_dir, f"{basename}_IAD_ADC.png")
        plt.savefig(output_name, dpi=200)
        print("Created", output_name)
    else:
        plt.show()
    plt.close()
    plt.clf()
    return True


# sample usage
# noinspection DuplicatedCode
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Analyse MCUDiagnosticEventOccurred IAD data.')
    parser.add_argument('alert_dir', type=str,
                        help="The MCUDiagnosticEventOccurred alert directory")
    parser.add_argument('--output_dir', type=str, default=None,
                        help="The output directory. The default is <alert_dir>/../../McuDiagnosticEventOccurred_IAD")
    parser.add_argument('--to_feather', action='store_true',
                        help='if specified, output feather format instead of csv')
    parser.add_argument('--plot', action='store_true',
                        help='if specified, plot the data for each serial number')

    args = parser.parse_args()

    output_dir = args.output_dir
    alert_dir = args.alert_dir
    alert_dir = os.path.abspath(alert_dir)

    if output_dir is None:
        output_dir = os.path.join(args.alert_dir, "..", "..", "McuDiagnosticEventOccurred_IAD")
    else:
        output_dir = os.path.abspath(output_dir)

    output_dir = os.path.abspath(output_dir)
    print("McuDiagnosticEventOccurred directory:", alert_dir)
    print("                    Output directory:", output_dir)

    if not os.path.exists(output_dir):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        print("Processing ", alert_dir, output_dir)
        os.makedirs(output_dir, exist_ok=True)
        # mcu_diagnostic_alert_to_iad(alert_dir, output_dir, to_feather=args.to_feather)
        mcu_diagnostic_alert_to_iad_adc(alert_dir, output_dir, to_feather=args.to_feather)

    if args.plot:
        all_files = list(glob.glob(os.path.join(output_dir, "*_IAD_ADC.csv"))) + glob.glob(
            os.path.join(output_dir, "*_IAD_ADC.feather"))
        plot_dir = os.path.join(output_dir, "iad_adc_plots")
        os.makedirs(plot_dir, exist_ok=True)
        for alert_dir in all_files:
            plot_iad_adc_csv(alert_dir, plot_dir)

    print("done")


if __name__ == "__main__":
    main()
