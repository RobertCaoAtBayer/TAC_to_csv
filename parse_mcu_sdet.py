"""
 - combine all logs files into 1 file
 - find sdet and parsing data
"""
import datetime
import matplotlib.pyplot as plt
import pandas as pd
import os
import glob

def combine_sdet_file_in_dir(dir_name):
    output_filename = os.path.join(dir_name, 'QML_DebugTool-all.log')
    if os.path.exists(output_filename):
        return output_filename

    sdet_files = []
    for filename in glob.glob(dir_name + '/QML_DebugTool*.log'):
        sdet_files.append(filename)
    sdet_files = sorted(sdet_files, reverse=True)

    # combine into 1 file
    with open(output_filename, 'w') as out_file:
        for filename in sdet_files:
            with open(filename) as in_file:
                for line in in_file:
                    out_file.write(line)
    print(output_filename)
    return output_filename

def parse_mcu_sdet(filename: str, output_dir: str | None) -> pd.DataFrame:
    """Parse SDET data from QML_DebugTool log file for PSV version 1.12.0 and newer with SDET prefix"""
    if os.path.isdir(filename):
        filename = combine_sdet_file_in_dir(filename)

    if not os.path.isfile(filename):
        print(f"File {filename} does not exist")
        return pd.DataFrame()

    has_sdet = False
    all_data = []
    start_time = None
    year_str = str(datetime.datetime.now().year)
    all_df = []
    group_id = 0
    headers = "time(ms),mcu_time(ms),Inlet_SUDS,IR_K,digital,MIN,MAX".split(',')
    psv_gt_1_12 = False
    with open(filename) as in_file:
        last_line = ""
        for line_number, line in enumerate(in_file):
            arr = line.split(" ")
            if " HFE:SDET#" in line:
                if "SDET, " in line:
                    psv_gt_1_12 = True
                    headers = "time(ms),mcu_time(ms),Inlet_SUDS,IR_K,digital,MIN,MAX,Injector_State".split(',')
                else:
                    psv_gt_1_12 = False
                    headers = "time(ms),mcu_time(ms),Inlet_SUDS,IR_K,digital,MIN,MAX".split(',')
                if len(all_data):
                    df = pd.DataFrame(data=all_data, columns=headers)
                    df["time(ms)"] = df["time(ms)"] - df["time(ms)"].min()
                    df["date"] = start_time + pd.to_timedelta(df["time(ms)"], unit='ms')
                    df["group_id"] = int(group_id)
                    all_df.append(df)
                    group_id += 1

                all_data = []
                print(line)
                has_sdet = True
            elif not has_sdet and "SDET, " in line:
                # someone put in the command manually or the new SDET format has been wrapped (can't detect the old SDET format)
                has_sdet = True
                all_data = []
                psv_gt_1_12 = True
                headers = "time(ms),mcu_time(ms),Inlet_SUDS,IR_K,digital,MIN,MAX,Injector_State".split(',')
            elif has_sdet and ',' in line:
                if psv_gt_1_12 and "SDET, " not in line:
                    # print("skip", line)
                    continue
                row = arr[-1].split(',')
                if len(row) != len(headers) -1:  # the header contain extra hcu time field after parsing
                    continue

                row[-1] = row[-1].split("\\")[0]
                line_time = pd.to_datetime(year_str + arr[0], utc=True, format="mixed")

                if len(all_data) == 0:
                    # get start time - this time is from HCU so it should be correct.
                    # want to alight the time to the first sample
                    start_time = line_time
                    print("start_time", start_time)
                # Unfortunately, the debug text data can be corrupted, so we need to check each field if it is valid
                # Tt is not 100% sure if the data is valid!!!!
                try:
                    row = [int(x) for x in row]

                    # try to check each field
                    if row[1] < 0 or row[1] > 255:
                        print(f"Corrupted Inlet_SUDS {row[1]}: '{line}")
                        continue
                    if row[2] < 0 or row[2] > 255:
                        print(f"Corrupted IR_K {row[1]}: '{line}")
                        continue
                    if row[3] < 0 or row[3] > 1:
                        print(f"Corrupted digital {row[1]}: '{line}")
                        continue
                    if row[4] < 0 or row[4] > 255:
                        print(f"Corrupted MIN {row[1]}: '{line}")
                        continue
                    if row[5] < 0 or row[5] > 255:
                        print(f"Corrupted MAX {row[1]}: '{line}")
                        continue
                    last_line = line

                    delta_time = line_time - start_time
                    hcu_time_ms = int(delta_time.total_seconds() * 1000)
                    row = [hcu_time_ms] + row
                    all_data.append(row)

                except ValueError:
                    print("SDET parse error. Skip", line_number, line)
                    continue
    print("SDET last valid line:", last_line)
    if len(all_data):
        df = pd.DataFrame(data=all_data, columns=headers)
        offset = df["time(ms)"].min()
        if offset:
            print("Time offset", offset)
            df["time(ms)"] = df["time(ms)"] - offset
            # df.plot("time(ms)")
        df["date"] = start_time + pd.to_timedelta(df["time(ms)"], unit='ms')
        df["group_id"] = int(group_id)
        all_df.append(df)
    else:
        print("No SDET logs found in {}".format(filename))
        return pd.DataFrame()

    combined_df = pd.concat(all_df, ignore_index=True)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_filename = os.path.join(output_dir, "SDET.csv")
        df.to_csv(output_filename, index=False)
        print(f"Create {output_filename}")
        plot_sdet_data(df, False, output_dir, x_field="date")

    return combined_df

def plot_sdet_data(df: pd.DataFrame, show: bool = False, output_dir: str = ".", x_field = "T(s)"):
    if len(df) == 0:
        return
    df["T(s)"] = df["time(ms)"] / 1000.0
    for group in df["group_id"].unique():
        fdf = df[df["group_id"] == group]
        print("Group", group, len(fdf))
        # print(fdf["IR_K"].describe())

        # time(ms),Inlet_SUDS,IR_K,digital,MIN,MAX,date,group_id
        fig, ax = plt.subplots(figsize=(16, 8))
        # noinspection PyArgumentList
        ax = fdf.plot(x_field, ["Inlet_SUDS", "IR_K"], marker='.', ax=ax)
        ax.set_ylabel("Analog value")
        ax.set_title(f"SDET group {group} N={len(fdf)}")
        ax.axhspan(100, 110, color='yellow', alpha=0.3)  # Rectangle between y=100 and y=110
        ax.grid()
        ax1 = ax.twinx()
        ax1.set_ylabel("Digital value")
        # noinspection PyArgumentList
        fdf.plot(x_field, ["digital"], color='red', ax=ax1)
        output_name = os.path.join(output_dir, f"SDET_group{group}.png")
        plt.savefig(output_name, dpi=200)
        print("Created", output_name)
        if show:
            plt.show()
        plt.clf()
        plt.close(fig)

def extract_sdet_data_between_times(sdet_df: pd.DataFrame, start_time: pd.Timestamp, end_time: pd.Timestamp) -> pd.DataFrame:
    delta = pd.to_timedelta(0, unit='s')
    temp_df = pd.DataFrame(sdet_df[sdet_df["date"].between(start_time - delta, end_time + delta)])
    if len(temp_df) == 0:
        return temp_df

    if "T(s)" not in temp_df.columns:
        temp_df["T(s)"] = temp_df["time(ms)"] / 1000.0

    # "T(s)" offset to start of the injection
    min_time = temp_df["date"].min()
    offset = (min_time - start_time).total_seconds()
    ts_min = temp_df["T(s)"].min()
    temp_df["T(s)"] = temp_df["T(s)"] + offset - ts_min

    return temp_df


def match_sdet_to_injections_at_directory(sdet_df: pd.DataFrame, injection_dir: str, show_plot: bool = False):
    if len(sdet_df) == 0:
        return
    sdet_df["date"] = pd.to_datetime(sdet_df["date"], utc=True, format='mixed')
    for filename in glob.glob(injection_dir + '/protocol_*_digest.csv'):
        try:
            digest_df = pd.read_csv(filename, skiprows=1)  # skip first row
            digest_df.reset_index(drop=True, inplace=True)
        except pd.errors.ParserError as e:
            print("FAIL to parse ", filename)
            print(e)
            continue
        # print("injection_df", injection_df.columns)
        digest_df["time"] = pd.to_datetime(digest_df["time"], utc=True, format='mixed')
        digest_df["injector_state"] = digest_df["injector_state"].astype("category")
        digest_df = digest_df[digest_df["injector_state"] != "IDLE"]
        start_time = digest_df["time"].min()
        end_time = digest_df["time"].max()
        temp_df = extract_sdet_data_between_times(sdet_df, start_time, end_time)
        print("Matching SDET to", filename, len(temp_df), start_time, end_time)
        x_field = "T(s)"
        if len(temp_df):
            # print("found SDET data", len(temp_df), filename)
            # print("A", start_time, "\nB", end_time)
            # time(ms),Inlet_SUDS,IR_K,digital,MIN,MAX,date,group_id
            fig, ax = plt.subplots(figsize=(16, 8))
            base_name = os.path.basename(filename)
            name_prefix = os.path.splitext(filename)[0] + "_SDET"

            # noinspection PyArgumentList
            ax = temp_df.plot(x_field, ["Inlet_SUDS", "IR_K"], marker='.', ax=ax)
            ax.set_ylabel("Analog value")
            ax.set_title(f"Injection {base_name}: SDET data\nN={len(temp_df)} - {start_time} to {end_time}")
            ax.axhspan(100, 110, color='yellow', alpha=0.3)  # Rectangle between y=100 and y=110
            ax.grid()
            ax1 = ax.twinx()
            ax1.set_ylabel("Digital value")
            # noinspection PyArgumentList
            temp_df.plot(x_field, ["digital"], color='red', ax=ax1)
            plt.tight_layout()
            temp_df.to_csv(name_prefix + ".csv", index=False)
            output_name = name_prefix +".png"
            plt.savefig(output_name, dpi=200)
            print("Created", output_name)
            if show_plot:
                plt.show()
            plt.clf()
            plt.close(fig)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Parsing QML_DebugTool log for SDET data')
    parser.add_argument('log_filename', help='Path to a QML_DebugTool log file or a directory containing multiple QML_DebugTool log files')
    parser.add_argument('--output_dir', default=".", help='output directory')
    parser.add_argument("--show", action="store_true", default=False, help="Show plots")
    args = parser.parse_args()
    df = parse_mcu_sdet(args.log_filename, args.output_dir)
    if len(df) == 0:
        print("No SDET logs found in {}".format(args.log_filename))
        return

    plot_sdet_data(df, args.show, args.output_dir, x_field="date")

    match_sdet_to_injections_at_directory(df, args.output_dir, args.show)



if __name__ == '__main__':
    main()
