import os

import pandas as pd
import glob
import matplotlib.pyplot as plt
import numpy as np
from FRA_analyse_histogram import FraSingleEventAnalyzer
from tqdm import tqdm


def mcu_diagnostic_generate_suds_from_feather(alert_dir, output_dir, to_feather=True):
    df_dict = dict()
    sea = FraSingleEventAnalyzer(alert_dir, output_dir, event_name='MCUDiagnosticEventOccurred')
    if not sea.load_event():
        print("Failed to load MCU diagnostic event")
        return
    mcu_alert_df = sea.get_df()

    names = []
    summary = []
    all_serial = mcu_alert_df.SN.unique()
    progress_bar = tqdm(total=len(all_serial))
    for sn in all_serial:
        progress_bar.update(1)
        if to_feather:
            output_name = os.path.join(output_dir, f"{sn}_SUDS.feather")
        else:
            output_name = os.path.join(output_dir, f"{sn}_SUDS.csv")
        if os.path.exists(output_name):
            continue

        df = pd.DataFrame(mcu_alert_df[mcu_alert_df.SN == sn])
        if len(df) == 0:
            continue    # skip empty data
        sdf = convert_df_to_suds_analog_data(df)
        if to_feather:
            sdf.reset_index(inplace=True)
            sdf.to_feather(output_name)
        else:
            sdf.to_csv(output_name, index=False)
        names.append(output_name)
        summary.append([sn, len(sdf), sdf.DATE.min(), sdf.DATE.max()])

    summary_df = pd.DataFrame(summary, columns=["SN", "Count", "Start", "End"])
    output_name = os.path.join(output_dir, "McuDiagnosticSUDS_summary.csv")
    summary_df.to_csv(output_name, index=False)
    print("Created", output_name)
    return names

# produces one file res.csv that contains all SUDS rows
# produces SN123456789 file that contains SUDS rows of each serial number
# Each SUDS row will have structure -> DATE, SUDS, VOLTAGE, CURRENT, DELTA_TIME, INJ_PROGRESS
# Turn off One Drive Synchronization while running this function
# noinspection DuplicatedCode
def mcu_diagnostic_alert_to_suds(data_dir, output_dir: str, to_feather=False):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir,exist_ok=True)



    df_dict = dict()
    for data_csv in glob.glob(os.path.join(data_dir, "*.csv")):
        df = pd.read_csv(data_csv)
        df['ActiveAt'] = pd.to_datetime(df['ActiveAt'], utc=True, format='mixed')
        print("Processing", data_csv)
        # noinspection PyUnresolvedReferences
        serial = os.path.basename(data_csv).split("_")[1]

        sdf = convert_df_to_suds_analog_data(df)
        if serial not in df_dict:
            df_dict[serial] = sdf
        else:
            df_dict[serial] = pd.concat([df_dict[serial], sdf])

    names = []
    summary = []
    for sn, df in df_dict.items():
        df["SN"] = sn
        df.sort_values(by=['DATE'], inplace=True)
        if len(df) == 0:
            continue    # skip empty data

        if to_feather:
            output_name = os.path.join(output_dir, f"{sn}_SUDS.feather")
            df.reset_index(inplace=True)
            df.to_feather(output_name)
        else:
            output_name = os.path.join(output_dir, f"{sn}_SUDS.csv")
            df.to_csv(output_name, index=False)
        print("Created", output_name)
        names.append(output_name)
        summary.append([sn, len(df), df.DATE.min(), df.DATE.max()])

    summary_df = pd.DataFrame(summary, columns=["SN", "Count", "Start", "End"])
    output_name = os.path.join(output_dir, "McuDiagnosticSUDS_summary.csv")
    summary_df.to_csv(output_name, index=False)
    print("Created", output_name)
    return names


# noinspection DuplicatedCode
def generate_suds_analog_summary(all_df: pd.DataFrame, output_dir: str, serial: str, to_feather=False):
    output_dir = os.path.join(output_dir, "McuDiagnosticEventOccurred_SUDS")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    names = []
    summary = []
    all_df = all_df[all_df.CodeName == "MCUDiagnosticEventOccurred"]
    df = convert_df_to_suds_analog_data(all_df)
    df.sort_values(by=['DATE'], inplace=True)
    if len(df) == 0:
        print("Empty SUDS MCUDiagnosticEventOccurred data for", serial)
        return
    df["SN"] = serial

    if to_feather:
        output_name = os.path.join(output_dir, f"{serial}_SUDS.feather")
        df.reset_index(inplace=True)
        df.to_feather(output_name)
    else:
        output_name = os.path.join(output_dir, f"{serial}_SUDS.csv")
        df.to_csv(output_name, index=False)
    print("Created", output_name)
    names.append(output_name)
    summary.append([serial, len(df), df.DATE.min(), df.DATE.max()])

    summary_df = pd.DataFrame(summary, columns=["SN", "Count", "Start", "End"])
    output_name = os.path.join(output_dir, "McuDiagnosticSUDS_summary.csv")
    summary_df.to_csv(output_name, index=False)
    print("Created", output_name)

    suds_plot_histogram(df, serial, output_dir)
    plot_suds_analogs(df, serial, output_dir)


# noinspection DuplicatedCode
def convert_df_to_suds_analog_data(df: pd.DataFrame):
    # df = df[df.CodeName == "MCUDiagnosticEventOccurred"]
    single_file_suds_entries = []
    for index, df_row in df.iterrows():
        if "SUDS" not in str(df_row.Data):
            continue
        diagnostic_fields = df_row.Data.split('|')
        for field in filter(lambda x: "SUDS" in x, diagnostic_fields):
            # data is in the form "06:23:33.321321:SUDS:1:215:95:292784:0"
            start = field.find("SUDS")
            # attempt to fix non-well formed SUDS data because some data has date string, some don't (old data)
            time_str = ""
            if start != 0:
                time_str = field[:start].strip()  # "06:23:33.321321:"
                time_str = time_str[:-1]  # "06:23:33.321321"

            if len(time_str) > 0:
                date_start = str(df_row.ActiveAt).split(" ")[0].strip() + " " + time_str
            else:
                date_start = str(df_row.ActiveAt)
            date_start = date_start.split("+")[0]

            row = [date_start] + [int(x) for x in field[start:].strip().split(':')[1:]]
            if len(row) != 6:
                print("SUDS error:", field, row)
                continue
            single_file_suds_entries.append(row)
    sdf = pd.DataFrame(single_file_suds_entries,
                       columns=["DATE", "SUDS", "VOLTAGE", "CURRENT", "DELTA_TIME", "INJ_PROGRESS"])
    sdf['DATE'] = pd.to_datetime(sdf['DATE'], utc=True, format='mixed')
    return sdf


def suds_plot_histogram(df: pd.DataFrame, basename, output_dir=None):
    # Plot the data by SUDS detected, one for SUDS absent
    # Two plots generated, one for VOLTAGE and one for CURRENT

    bins = np.linspace(0, 255, 255)
    df_suds_on = df[df.SUDS == 1]
    df_suds_off = df[df.SUDS == 0]

    fig, axes = plt.subplots(2, 1, figsize=(10, 5), sharex=True)

    df_suds_on.VOLTAGE.hist(bins=bins, alpha=0.5, label='detected', ax=axes[0])
    df_suds_off.VOLTAGE.hist(bins=bins, alpha=0.5, label='not detected', ax=axes[0])
    axes[0].set_title(f'VOLTAGE Histogram for {basename}')
    axes[0].set_xlabel(None)
    axes[0].legend()

    df_suds_on.CURRENT.hist(bins=bins, alpha=0.5, label='detected', ax=axes[1])
    df_suds_off.CURRENT.hist(bins=bins, alpha=0.5, label='not detected', ax=axes[1])
    axes[1].set_title('CURRENT Histogram for %s' % basename)
    axes[1].legend()
    if output_dir:
        output_name = os.path.join(output_dir, f"{os.path.splitext(basename)[0]}_histogram.png")
        plt.savefig(output_name, dpi=200)
        print("Created", output_name)
    else:
        plt.show()

    plt.close()
    plt.clf()


def single_file_plot(csv_filename, output_dir=None, optional_min_date=None) -> pd.DataFrame:
    # Generate two DATE sorted plots on both VOLTAGE and CURRENT
    # One for SUDS detected, one for SUDS absent
    # Not sure how to format it as the date can get really long, currently one plot in one plane
    # noinspection DuplicatedCode
    if csv_filename.endswith(".feather"):
        df = pd.read_feather(csv_filename)
    else:
        df = pd.read_csv(csv_filename)

    if len(df) < 5:
        return pd.DataFrame()
    basename = os.path.splitext(os.path.basename(csv_filename))[0]
    if "_summary" in basename:
        return pd.DataFrame()

    df.DATE = pd.to_datetime(df.DATE, format='mixed')
    df = df.sort_values(by='DATE')

    if optional_min_date:
        fdf = df[df.DATE >= optional_min_date]
        # skip because it does not contain the min date
        if len(fdf) == 0:
            return pd.DataFrame()

    print("Processing", csv_filename)

    df = plot_suds_analogs(df, basename, output_dir)
    return df


def plot_suds_analogs(df: pd.DataFrame, serial: str, output_dir: str):
    first_date = df.DATE.min()
    last_date = df.DATE.max()
    dt = last_date - first_date
    first_date_str = str(first_date).split(" ")[0]
    last_date_str = str(last_date).split(" ")[0]
    serial = serial.split("_")[0]
    duration_string = "%s [from %s to %s (%s days) %d samples]" % (serial, first_date_str, last_date_str, dt.days, len(df))
    print("duration_string", duration_string)

    df_suds_on = df[df.SUDS == 1]
    df_suds_off = df[df.SUDS == 0]
    fig, axes = plt.subplots(2, 1, figsize=(10, 10), tight_layout=True, sharex=True)
    for ax, df, detected_state in zip(axes, [df_suds_on, df_suds_off], ["detected", "not detected"]):
        ax.scatter(df.DATE, df.VOLTAGE, color="blue", label="VOLTAGE")
        ax.scatter(df.DATE, df.CURRENT, color='green', label="CURRENT")
        ax.set_ylabel('VOLTAGE')
        ax.set_title(f'VOLTAGE when SUDS {detected_state}')
        ax.tick_params(axis='x', labelrotation=90)
        ax.grid()
        ax.legend()
    axes[0].set_xlabel(None)
    axes[0].set_title(duration_string)
    if output_dir:
        output_name = os.path.join(output_dir, f"{serial}_SUDS_by_date.png")
        plt.savefig(output_name, dpi=200)
        print("Created", output_name)
    else:
        plt.show()

    plt.close()
    plt.clf()
    return df


# sample usage
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Analyse MCUDiagnosticEventOccurred SUDS data.')
    parser.add_argument('alert_dir', type=str, help="The MCUDiagnosticEventOccurred alert directory")
    parser.add_argument('--output_dir', type=str, default=None, help="The output directory. The default is <alert_dir>/../../McuDiagnosticEventOccurred_SUDS")
    parser.add_argument('--to_feather', action='store_true', help='if specified, output feather format instead of csv')
    parser.add_argument('--from_feather', action='store_true', help='Load the McuDiagnosticEventOccurred from feather and process SUDS data')
    parser.add_argument('--plot', action='store_true', help='if specified, plot the data for each serial number')
    parser.add_argument('--min_date', type=str, default="", help='The minimum date filtering')

    args = parser.parse_args()

    # dir_name = os.path.dirname(path)
    # dir_name = os.path.dirname(dir_name)
    output_dir = args.output_dir
    alert_dir = args.alert_dir
    alert_dir = os.path.abspath(alert_dir)

    optional_min_date = None
    if args.min_date:
        min_date = args.min_date
        optional_min_date = pd.Timestamp(pd.to_datetime(min_date), tz='UTC')
        print("Minimum date", optional_min_date)

    if output_dir is None:
        output_dir = os.path.join(args.alert_dir, "..", "..", "McuDiagnosticEventOccurred_SUDS")
    else:
        output_dir = os.path.abspath(output_dir)
    output_dir = os.path.abspath(output_dir)
    print("McuDiagnosticEventOccurred directory:", alert_dir)
    print("                    Output directory:", output_dir)
    if not os.path.exists(output_dir):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

    if args.to_feather:
        print("Regenerate SUDS feather file", alert_dir, output_dir)
        os.makedirs(output_dir, exist_ok=True)
        mcu_diagnostic_alert_to_suds(alert_dir, output_dir, to_feather=args.to_feather)

    if args.from_feather:
        print("Regenerate SUDS feather file", alert_dir, output_dir)
        os.makedirs(output_dir, exist_ok=True)
        mcu_diagnostic_generate_suds_from_feather(alert_dir, output_dir)

    if args.plot:
        print("here output", output_dir)
        all_files = list(glob.glob(os.path.join(output_dir, "*.csv"))) + glob.glob(os.path.join(output_dir, "*.feather"))
        plot_time_dir = os.path.join(output_dir, "plot_time")
        plot_hist_dir = os.path.join(output_dir, "plot_histogram")
        os.makedirs(plot_time_dir, exist_ok=True)
        os.makedirs(plot_hist_dir, exist_ok=True)
        print("all_files", all_files)
        if len(all_files):
            for filename in all_files:
                df = single_file_plot(filename, plot_time_dir, optional_min_date)
                if len(df) > 10:
                    suds_plot_histogram(df, os.path.basename(filename), plot_hist_dir)


    print("done")


if __name__ == "__main__":
    main()
