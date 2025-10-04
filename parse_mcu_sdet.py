"""
 - combine all logs files into 1 file
 - find sdet and parsing data
"""
import datetime

import matplotlib.pyplot as plt
import pandas as pd
import os
import glob

from bokeh.io import output_file


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
    if os.path.isfile(filename):
        pass
    elif os.path.isdir(filename):
        filename = combine_sdet_file_in_dir(filename)

    has_sdet = False
    all_data = []
    start_time = None
    year_str = str(datetime.datetime.now().year)
    all_df = []
    group_id = 0
    with open(filename) as in_file:
        for line in in_file:
            arr = line.split(" ")
            if " HFE:SDET#" in line:
                if len(all_data):
                    headers = "time(ms),Inlet_SUDS,IR_K,digital,MIN,MAX".split(',')
                    df = pd.DataFrame(data=all_data, columns=headers)
                    df["date"] = start_time + pd.to_timedelta(df["time(ms)"], unit='ms')
                    df["group_id"] = int(group_id)
                    all_df.append(df)
                    group_id += 1

                all_data = []
                print(line)
                has_sdet = True
                start_time = arr[0]
                print("start_time", start_time)
                # "0916-13:48:39.147"
                start_time = pd.to_datetime(year_str + start_time, utc=True, format="mixed")
                print("start_time", start_time)
            elif has_sdet and ',' in line:
                row = arr[-1].split(',')
                if len(row) != 6:
                    # print("skip", line)
                    continue
                row[-1] = row[-1].split("\\")[0]
                try:
                    row = [int(x) for x in row]
                    all_data.append(row)
                except ValueError:
                    # print("skip", line)
                    continue
    if len(all_data):
        headers = "time(ms),Inlet_SUDS,IR_K,digital,MIN,MAX".split(',')
        df = pd.DataFrame(data=all_data, columns=headers)
        df["date"] = start_time + pd.to_timedelta(df["time(ms)"], unit='ms')
        df["group_id"] = int(group_id)
        all_df.append(df)
    combined_df = pd.concat(all_df, ignore_index=True)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_filename = os.path.join(output_dir, "SDECT.csv")
        if os.path.exists(output_filename):
            df.to_csv(output_filename, index=False)
            print(f"Create {output_filename}")

    return combined_df

def plot_sdet_data(df: pd.DataFrame, show: bool = False, output_dir: str = ".", x_field = "T(s)"):
    df["T(s)"] = df["time(ms)"] / 1000.0
    for group in df["group_id"].unique():
        fdf = df[df["group_id"] == group]
        print("Group", group, len(fdf))
        # print(fdf["IR_K"].describe())

        # time(ms),Inlet_SUDS,IR_K,digital,MIN,MAX,date,group_id
        fig, ax = plt.subplots(figsize=(16, 8))
        ax = fdf.plot(x_field, ["Inlet_SUDS", "IR_K"], marker='.', ax=ax)
        ax.set_ylabel("Analog value")
        ax.set_title(f"SDET group {group} N={len(fdf)}")
        ax.axhspan(100, 110, color='yellow', alpha=0.3)  # Rectangle between y=100 and y=110
        ax.grid()
        ax1 = ax.twinx()
        ax1.set_ylabel("Digital value")
        fdf.plot(x_field, ["digital"], color='red', ax=ax1)
        output_name = os.path.join(output_dir, f"SDET_group{group}.png")
        plt.savefig(output_name, dpi=200)
        print("Created", output_name)
        if show:
            plt.show()
        plt.clf()
        plt.close()

def match_sdet_to_injections_at_directory(sdet_df: pd.DataFrame, injection_dir: str):
    sdet_df["date"] = pd.to_datetime(sdet_df["date"], utc=True, format='mixed')
    for filename in glob.glob(injection_dir + '/protocol_*_digest.csv'):
        # print("Matching SDET to", filename)
        injection_df = pd.read_csv(filename, skiprows=1)  # skip first row
        injection_df.reset_index(drop=True, inplace=True)
        # print("injection_df", injection_df.columns)
        injection_df["time"] = pd.to_datetime(injection_df["time"], utc=True, format='mixed')
        injection_df["injector_state"] = injection_df["injector_state"].astype("category")
        injection_df = injection_df[injection_df["injector_state"] != "IDLE"]
        start_time = injection_df["time"].min()
        end_time = injection_df["time"].max()
        delta = pd.to_timedelta(0, unit='s')
        temp_df = sdet_df[sdet_df["date"].between(start_time - delta, end_time + delta)]
        if len(temp_df):
            # print("found SDET data", len(temp_df), filename)
            # print("A", start_time, "\nB", end_time)
            # time(ms),Inlet_SUDS,IR_K,digital,MIN,MAX,date,group_id
            fig, ax = plt.subplots(figsize=(16, 8))
            base_name = os.path.basename(filename)
            name_prefix = os.path.splitext(filename)[0] + "_SDET"
            x_field = "T(s)"
            ax = temp_df.plot(x_field, ["Inlet_SUDS", "IR_K"], marker='.', ax=ax)
            ax.set_ylabel("Analog value")
            ax.set_title(f"Injection {base_name}: SDET data\nN={len(temp_df)} - {start_time} to {end_time}")
            ax.axhspan(100, 110, color='yellow', alpha=0.3)  # Rectangle between y=100 and y=110
            ax.grid()
            ax1 = ax.twinx()
            ax1.set_ylabel("Digital value")
            temp_df.plot(x_field, ["digital"], color='red', ax=ax1)
            plt.tight_layout()
            temp_df.to_csv(name_prefix + ".csv", index=False)
            output_name = name_prefix +".png"
            plt.savefig(output_name, dpi=200)
            print("Created", output_name)
            # plt.show()
            plt.clf()
            plt.close()


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

    plot_sdet_data(df, args.show, args.output_dir)

    match_sdet_to_injections_at_directory(df, args.output_dir)



if __name__ == '__main__':
    main()
