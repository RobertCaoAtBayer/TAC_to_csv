"""
FRA_analyse_mcu_diagnostic_message.py parses the MCU diagnostic messages into individual files
based on the MCU diagnostic alert type to allow for easier analysis.
"""
import pandas as pd
import os.path

from numpy.ma.extras import unique
from tqdm import tqdm
import matplotlib.pyplot as plt

from FRA_analyse_histogram import FraSingleEventAnalyzer
# from notebooks.inject_arm_data import output_filename


def load_mcu_diagnostics(alert_dir: str, start_year="2023", end_year="2030") -> pd.DataFrame:
    analyser = FraSingleEventAnalyzer(alert_dir,alert_dir, "MCUDiagnosticEventOccurred")
    if not analyser.load_event():
        print("Fail to load MCU diagnostic events", alert_dir)
        exit(1)
    analyser.datetime_filter(start_year, end_year)
    return analyser.get_df()

def split_mcu_diagnostics(df: pd.DataFrame, output_dir: str) -> list[str]:
    """
    Split the dataframe into multiple files based mcu alert type denoted in the 'Data' field where alerts are separated by '|'.
        "Data": "05:09:43.237237:PE:C2:0:0:0:107:-100 | 05:09:43.956956:PE:S0:0:0:0:111:-75 | 05:09:44.254254:PE:C1:0:0:0:122:-88"

    :param df: The MCU diagnostic dataframe to split
    :param output_dir: The output directory
    :return: None
    """
    all_data = dict()
    os.makedirs(output_dir, exist_ok=True)
    error_fh = open(os.path.join(output_dir, "mcu_diagnostics_parse_error.log"), "w")

    all_serials = df['SN'].unique()
    progress_bar = tqdm(total=len(all_serials))
    for i, sn in enumerate(all_serials):
        progress_bar.update()
        sn_df = df[df['SN'] == sn]
        if len(sn_df) == 0:
            error_fh.write(f"{sn} has no MCU diagnostic data\n")
            continue

        for index, df_row in sn_df.iterrows():
            data = df_row.Data
            if not isinstance(data, str) or data is None or len(data) == 0:
                error_fh.write(f"{sn} row error {index} row: {str(df_row)}\n")
                continue
            diagnostic_fields = data.split('|')
            for field in diagnostic_fields:
                field = field.strip()
                if field.startswith(":"): # some old data does not have date field in the alert
                    error_fh.write(f"{sn} bad alert {index} row: {str(df_row)}\n")
                    continue

                fields = field.split(':')    # ['05', '09', '43.237237', 'PE', 'C2', '0', '0', '0', '107', '-100 ']
                if len(fields) < 5:
                    error_fh.write(f"{sn} invalid data {index} row: {str(df_row)}\n")
                    continue
                name = fields[3]  # PE

                if name not in all_data:
                    all_data[name] = []
                time_str = ":".join(fields[:3])
                date_start = str(df_row.ActiveAt).split(" ")[0].strip() + " " + time_str
                row = [date_start, sn, ":".join(fields[4:])]
                all_data[name].append(row)

    alert_filenames = []
    for name, data in all_data.items():
        if len(data) == 0:
            continue
        # create a dataframe
        df = pd.DataFrame(data, columns=["ActiveAt", "SN", "Data"])
        output_name = os.path.join(output_dir, f"MCUDiagnosticEventOccurred_{name}.csv")
        try:
            df.to_csv(output_name)
        except PermissionError as e:
            print("Failed to save", output_name, "due to", e)

        df['ActiveAt'] = pd.to_datetime(df['ActiveAt'], utc=True, format='mixed')
        df['InactiveAt'] = df['ActiveAt']

        # save the dataframe to a csv file
        output_name = os.path.join(output_dir, f"MCUDiagnosticEventOccurred_{name}.feather")
        df.to_feather(output_name)
        print("Created", output_name)
        if "Slack" in name:
            analyse_slack_diagnostics(output_name)
        alert_filenames.append(output_name)
    return alert_filenames


def analyse_slack_diagnostics(slack_filename: str):
    if slack_filename.endswith(".csv"):
        df = pd.read_csv(slack_filename)
    elif slack_filename.endswith(".feather"):
        df = pd.read_feather(slack_filename)
    else:
        print("Invalid slack filename", slack_filename)
        return
    axis = df["Data"].apply(lambda x: x.split(":")[0])
    slack = df["Data"].apply(lambda x: x.split(":")[1])
    vol1 = df["Data"].apply(lambda x: x.split(":")[2])
    vol2 = df["Data"].apply(lambda x: x.split(":")[3])
    vol3 = df["Data"].apply(lambda x: x.split(":")[4])
    results_df = pd.DataFrame(data=df["ActiveAt"], columns=["ActiveAt"])
    results_df["Axis"] = axis
    results_df["Slack"] = slack
    results_df["Vol1"] = vol1
    results_df["Vol2"] = vol2
    results_df["Vol3"] = vol3
    if "SN" in df.columns:
        results_df["SN"] = df["SN"]
    output_filename = os.path.splitext(slack_filename)[0] + "_parsed.csv"
    results_df.to_csv(output_filename, index=False)
    print("Created", output_filename)

    unique_serials  = df["SN"].unique()
    if len(unique_serials) != 1:
        print("Multiple serials found in the slack data, skipping boxplot")
        serial = "%d_injectors" % len(unique_serials)
    else:
        serial = unique_serials[0]

    results_df["Axis"] = results_df["Axis"].astype(pd.CategoricalDtype(categories=["S0", "C1", "C2"], ordered=True))
    results_df["Slack"] = results_df["Slack"].astype("int")
    ax = results_df.boxplot(column="Slack", by="Axis", figsize=(12, 8), grid=True)
    ax.set_title("Boxplot Slack values by Axis for %s" % serial)
    ax.set_ylabel("Slack volume (.1ml)")
    ax.set_xlabel("")
    output_name = os.path.splitext(slack_filename)[0] + "_%s_boxplot.png" % serial
    plt.savefig(output_name, dpi=200)
    plt.clf()
    plt.close()
    print("Created", output_name)

    ax = results_df.plot.scatter(x="Vol1", y="Slack", c="Axis", cmap='viridis', alpha=0.5, figsize=(12, 8))
    ax.set_title("Scatter of slack-volume for %s" % serial)
    ax.set_ylabel("Slack volume (.1ml)")
    ax.set_xlabel("Volume (.1ml)")
    ax.grid(True)

    output_name = os.path.splitext(slack_filename)[0] + "_%s_scatter.png" % serial
    plt.savefig(output_name, dpi=200)
    plt.clf()
    plt.close()
    print("Created", output_name)







def main():
    import argparse
    parser = argparse.ArgumentParser(description='FRA analysing MCU diagnostic alert message')
    parser.add_argument('alert_dir', type=str,
                        help="The directory contains alerts which has been grouped all same-alert-name in a csv file")
    parser.add_argument('--output_dir', type=str, default=".",  help="The output directory")
    parser.add_argument('--show_plot', type=bool, action=argparse.BooleanOptionalAction, default=False,
                        help='Show plot')
    args = parser.parse_args()
    df = load_mcu_diagnostics(args.alert_dir)
    split_mcu_diagnostics(df, args.output_dir)
    print(df.shape, df.columns)


if __name__ == '__main__':
    main()
