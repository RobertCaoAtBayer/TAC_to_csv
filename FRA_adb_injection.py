import pandas as pd
import matplotlib.pyplot as plt
from io import StringIO
import os.path
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET

from matplotlib.pyplot import tight_layout
from openpyxl.styles.alignment import horizontal_alignments
from pendulum import duration
from win32trace import flush


def get_phase_time(df: pd.DataFrame) -> list:
    all_phase_time = []
    for pn in sorted(list(df["PN"].unique())):
        pn = int(pn)
        if pn < 0:
            continue    # skip negative phase
        phase_df = df[df["PN"] == pn]
        min_t = float(phase_df["TO"].min())
        max_t = float(phase_df["TO"].max())
        all_phase_time.append([pn, min_t, max_t])
    return all_phase_time


def find_transitions(df: pd.DataFrame, column: str) -> list:
    """
    Find the transition times of 0 and 1 in the specified column of the DataFrame.

    @param df: DataFrame containing the data
    @param column: The column to check for transitions
    @return: List of tuples with (index, value) where transitions occur
    """
    transitions = []
    previous_value = None

    for index, value in df.iterrows():
        if previous_value is not None and value[column] != previous_value[column]:
            transitions.append((index, value[column]))
        previous_value = value

    return transitions


def plot_injection(df: pd.DataFrame, timestamp: str, units_dict: dict, output_dir: str = None, output_prefix: str = "injection"):
    """

    @param df: Index(['TO', 'PN', 'LM', 'AV', 'AR', 'AP', 'BV', 'BR', 'BP'], dtype='object')
    @param timestamp:
    @param units_dict: e.g. {'AV': 'ml', 'AR': 'ml/s', 'AP': 'kpa', 'BV': 'ml', 'BR': 'ml/s', 'BP': 'kpa'}
    @param output_dir:
    @param output_prefix:
    @return:
    """

    # remove negative phase index
    df = pd.DataFrame(df[df["PN"] >= 0])

    fig, (ax0, ax1, ax2) = plt.subplots(nrows=3, ncols=1, figsize=(15, 9), sharex=True, tight_layout=True)
    df.plot(x='TO', y=['AV', "BV"], ax=ax2)
    df.plot(x='TO', y=['AR', "BR"], ax=ax1)
    df.plot(x='TO', y=['AP', "BP"], ax=ax0)
    ax0.set_ylabel("Pressure(%s)" % units_dict["AP"])
    ax1.set_ylabel("Flow rate(%s)" % units_dict["AR"])
    ax2.set_ylabel("Volume(%s)" % units_dict["AV"])

    all_phase_time = get_phase_time(df)
    # print("all_phase_time", all_phase_time)
    for ax in [ax0, ax1, ax2]:
        t = 0
        for pn, min_t, max_t in all_phase_time:
            if int(pn) % 2 == 1:
                ax.axvspan(t, max_t, facecolor='xkcd:sky blue', alpha=0.2)
            else:
                pass    # not drawing
            t = max_t
        ax.legend()
        ax.grid()

    # add phase number to the volume plot
    for pn, min_t, max_t in all_phase_time:
        ax2.text(min_t, 0, "Phase %d" % pn, rotation=90, verticalalignment='bottom', horizontalalignment='center')

    # find adaptive flow and show on the pressure plot
    af_transitions = find_transitions(df, "LM")
    if len(af_transitions) > 0:
        print(af_transitions)
    t0 = df["TO"].min()
    for index, value in af_transitions:
        current_time = df["TO"].iloc[index]
        if value == 1:
            t0 = current_time
            continue
        else:
            ax0.axvspan(t0, current_time, facecolor='red', alpha=0.3)

    # graph title
    flush_vol = df["AV"].max()
    contrast_vol = df["BV"].max()
    dt = df["TO"].max()
    title = "% saline: %.1f mL contrast: %.01f mL duration: %.02fs (%s)" % (output_prefix, flush_vol, contrast_vol, dt, timestamp)
    plt.suptitle(title)

    if output_dir:
        ts = pd.to_datetime(timestamp, utc=True, format='mixed')
        save_plot_name = os.path.join(output_dir, "%s_%s.png" % (output_prefix, ts.strftime("%Y%m%d_%H%M%S")))
        plt.savefig(save_plot_name, dpi=200)
        print("Created", save_plot_name)
    else:
        plt.show()

    plt.clf()
    plt.close()


def generate_injection_plots_from_injection_csv(path: str, output_dir: str = None, output_prefix: str = "injection", last_n_injections=100):
    print("loading csv", path)
    injections_df = pd.read_csv(path)
    print(injections_df.shape, injections_df.columns)

    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)

    if last_n_injections is not None:
        index = len(injections_df) - last_n_injections
        if index > 0:
            injections_df = injections_df[index:]

    for i, row in injections_df.iterrows():
        print("row %d/%d" % (int(i), len(injections_df)))
        df, units_dict = extract_cdata(row["samples_xml"])
        timestamp = row["created_date_time"]
        plot_injection(df, timestamp, units_dict, output_dir, output_prefix)


def extract_cdata(xml_str: str) -> (pd.DataFrame, dict):
    """
    grand_child tag: units Text: AV="ml",AR="ml/s",AP="kpa",BV="ml",BR="ml/s",BP="kpa"
    Child tag: data-points Attributes: {'format': 'TO, PN, LM, AV, AR, AP, BV, BR, BP'}

    @param xml_str:
    @return:
    """
    units_text = 'AV="ml",AR="ml/s",AP="kpa",BV="ml",BR="ml/s",BP="kpa"'
    try:
        root = ET.fromstring(xml_str)
        for child in root:
            for grand_child in child:
                if "units" == grand_child.tag:
                    units_text = grand_child.text
        units_arr = units_text.split(",")
        units_dict = {x.split("=")[0]: x.split("=")[1][1:-1] for x in units_arr}  # remove quotes
        for data_points in root.findall('.//data-points'):
            header = data_points.attrib["format"].split(", ")
            cdata_content = data_points.text.strip()
            cdata_content = cdata_content.replace("\\r\\n", "\n")
            cdata_content = cdata_content.replace(", ", ",")
            cdata_content = cdata_content.replace("P0YT", "")
            cdata_content = cdata_content.replace("S,", ",")
            cdata_content = cdata_content.replace("False", "0")
            cdata_content = cdata_content.replace("True", "1")
            df = pd.read_csv(StringIO(cdata_content))
            df.columns = header
            return df, units_dict

    except ET.ParseError as e:
        print("Error parsing XML:", e)


# noinspection GrazieInspection
def check_sample_xml(xml_str: str):
    """
    <sample-data xml-version="2"><data-source><device GetConfigInfo="" /></data-source>
    <preamble><units>AV="ml",AR="ml/s",AP="kpa",BV="ml",BR="ml/s",BP="kpa"</units></preamble>
    <data-points format="TO, PN, LM, AV, AR, AP, BV, BR, BP">
        <![CDATA
        [
        TO, PN, LM, AV, AR, AP, BV, BR, BP
        P0YT0.00S, -1, False, 0, 0, 0, 0, 0, 0
        P0YT0.00S, 1, False, 0, 0, 0, 0, 0, 0
        ....
        ]]>
    </data-points></sample-data>

    where:
    TO: Time. Appear to be in the format P0YT0.00S as  time unit in seconds
    PN = Phase number
    LM = Limit? as pressure limit?
    AV = Flush Volume
    AR = Flush Rate
    AP = Flush Pressure
    BV = Contrast Volume
    BR = Contrast Rate
    BP = Contrast Pressure
    """
    length = len(xml_str)
    print("length", length)
    # parsing xml string
    try:
        root = ET.fromstring(xml_str)
        print("Root tag:", root.tag)
        for child in root:
            print("Child tag:", child.tag, "Attributes:", child.attrib)
            for grand_child in child:
                print("grand_child tag:", grand_child.tag, "Text:", grand_child.text)
    except ET.ParseError as e:
        print("Error parsing XML:", e)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Analyse FRA ADB injections')
    parser.add_argument('csv', type=str, help='The injection csv ')
    parser.add_argument('--output_dir', type=str, default=None, help='The output directory')
    parser.add_argument('--output_prefix', type=str, default=None, help='Injection plot name prefix (e.g. serial number')

    parser.add_argument('--show_plot', type=bool, action=argparse.BooleanOptionalAction, default=False,
                        help='Show plot')
    args = parser.parse_args()
    generate_injection_plots_from_injection_csv(args.csv, output_dir=args.output_dir, output_prefix=args.output_prefix, last_n_injections=100)


if __name__ == '__main__':
    main()
