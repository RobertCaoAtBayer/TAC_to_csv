"""
Parsing injection log.
"""
import csv

from Commands import InjectDigestCommand, DigestCommand
from alarms import Alarms
import os
import zipfile
import tarfile
from mcu_gui import show_result
import shutil
import pandas as pd
import os.path
from datetime import datetime
from parse_mcu_sdet import parse_mcu_sdet, plot_sdet_data, match_sdet_to_injections_at_directory, extract_sdet_data_between_times

class DigestsData:

    def __init__(self):
        self.data = []

    def from_mcu_log(self, log_filename, verbose=False):
        with open(log_filename, 'r') as file:
            for line in file:
                if "RX: [DIGEST][][" in line:
                    parts = line.split("[")
                    digest_data = parts[3].split("]")[0]
                    digest_time = parts[0].split(" ")[0].strip()
                    digest_data = digest_data.split(",")

                    # decode the alarms field - the first field in digest_data
                    alarms_str = digest_data[0]
                    if alarms_str != "0":
                        alarm_strs = Alarms.get_alarm_names(alarms_str)
                        alarms_str = ":".join(alarm_strs)
                        print("Alarms:", alarms_str)
                    else:
                        alarms_str = ""
                    digest_data.append(alarms_str)

                    if verbose:
                        print(digest_time,  digest_data)

                    if len(parts) > 1:
                        self.data.append([digest_time] +  digest_data)

    def save_digests(self, output_filename):
        header = DigestCommand.header + ["alarms"]
        # Save the digests to a CSV file
        with open(output_filename, 'w') as file:
            csv_writer = csv.writer(file, dialect='excel', lineterminator='\n')
            csv_writer.writerow(["time"] + header)
            # Write each digest as a row in the CSV file
            csv_writer.writerows(self.data)
            print(f"Digests saved to {output_filename}")


def extract_digests(log_filename):
    digest_data = DigestsData()
    digest_data.from_mcu_log(log_filename)
    filename = os.path.splitext(log_filename)[0] + "_digests.csv"
    digest_data.save_digests(filename)
    return filename

def get_sru_log_file_list(prefix):
    return [prefix + "." + ext for ext in ['old3.log', 'old2.log', 'old1.log', 'log']]

def parse_sru_bottle_data(dir_name):
    file_lists = get_sru_log_file_list("DS_Device-Bottle")
    data = []
    year_str = '2021'  # todo
    for filename in file_lists:
        filename = os.path.join(dir_name, filename)
        if os.path.exists(filename):
            print("reading", filename)
            with open(filename) as fh:
                for line in fh:
                    if "signalDataChanged_BottleBubbleStates(): Spike State Changed from" in line:
                        line = line.strip()
                        arr = line.split(" ")
                        # time = pd.to_datetime("1129-07:06:41.884", format="%m%d-%H:%M:%S.%f")
                        time = pd.to_datetime(year_str + arr[0], format="%Y%m%d-%H:%M:%S.%f")
                        row = time, arr[7], arr[9].split(".")[0]
                        print(row, line)
                        data.append(row)
    df = pd.DataFrame(data, columns=['time', 'old', 'new'])
    print("df", df.shape, df.columns)
    df['old'] = df["old"].astype("category")
    df['new'] = df["new"].astype("category")
    filename = os.path.join(dir_name, "DS_Device-Bottle_air_state.xlsx")
    print("Creating", filename)
    df.to_excel(filename, index=False)
    return df


def extract_mcu_file(path, to_directory='.'):
    if path.endswith('.zip'):
        opener, mode = zipfile.ZipFile, 'r'
    elif path.endswith('.tar.gz') or path.endswith('.tgz'):
        opener, mode = tarfile.open, 'r:gz'
    elif path.endswith('.tar.bz2') or path.endswith('.tbz'):
        opener, mode = tarfile.open, 'r:bz2'
    else:
        raise ValueError

    names = []
    try:
        file = opener(path, mode)
        try:
            if hasattr(file, "namelist"):
                name_list = file.namelist()
            elif hasattr(file, "getmembers"):
                name_list = [x.name for x in file.getmembers()]
            else:
                name_list = []
            for member_name in name_list:
                if "SruLogArchive.tar.gz" in member_name:
                    print("Extracting embedded SRU log", member_name)
                    file.extract(member_name, to_directory)
                    sru_log = os.path.join(to_directory, member_name)
                    return extract_mcu_file(sru_log, to_directory)
                if "Mcu." in member_name:
                    file.extract(member_name, to_directory)
                    print("Extracting", member_name)
                elif "All." in member_name:
                    file.extract(member_name, to_directory)
                    print("Extracting", member_name)
                elif "QML_DebugTool" in member_name:
                    file.extract(member_name, to_directory)
                    print("Extracting", member_name)
                elif "lastBacktrace.log" in member_name:
                    file.extract(member_name, to_directory)
                    print("Extracting", member_name)
                elif "DS_Mcu-Link" in member_name:
                    print("Extracting", member_name)
                    file.extract(member_name, to_directory)
                    # DS_Mcu-Link.old3.log
                    # DS_Mcu-Link.old2.log
                    # DS_Mcu-Link.old1.log
                    # DS_Mcu-Link.log
                    if "IMAX_USER/log/DS_Mcu-Link.old" in member_name:
                        old_x = member_name.split(".")[-2]
                        # print("old_x", old_x, member.name)
                        if old_x == "old":
                            print("Skip", member_name)
                            continue
                        x = old_x[-1]   # assume 1 digit indexing only
                        x = int(x)
                        names.append([x, os.path.join(to_directory, member_name)])
                    else:
                        names.append([0, os.path.join(to_directory, member_name)])
        finally:
            file.close()
    finally:
        pass

    names = [x[1] for x in sorted(names, reverse=True)]   # sort by index in reverse order (olddest first) then return the names only
    return names


def extract_all_injections(filename, out_dir, injected_count=0):
    found = False
    index = 0
    inject_digest_fh = None
    digest_fh = None
    file_list = list()
    inject_complete_state = ""
    digest_name = ""
    inject_digest_name = ""
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    # all commands in the log file excluding injectdigest and digest commands
    all_commands_fh = open(os.path.join(out_dir, "all_commands.txt"), "w")

    summary_filename = os.path.join(out_dir, "all_injections.txt")
    summary_fh = open(summary_filename, "w")
    summary_fh.write("Extracting injections from %s\n" % filename)
    summary_fh.write("Output directory: %s\n" % out_dir)

    creation_time = os.path.getctime(filename)
    year_prefix_str = str(datetime.fromtimestamp(creation_time).year)

    oadi_str = ""

    with open(filename) as fh:
        for line in fh:
            time_str = line.split(" ")[0]
            time_str = year_prefix_str + time_str
            if " : RX: [" in line and "RX: [INJECTDIGEST]" not in line and "RX: [DIGEST]" not in line and "RX: [LEDS]" not in line and "T_BMSDIGESTFAILED_Read" not in line and "RX: [CLEARALARMS]" not in line:
                all_commands_fh.write(line.strip() + "\n")

            if "TX: >ARM" in line:
                oadi_str = ""
                # "0906-04:39:23.829 INFO : TX: >ARM@2068,1,SALINE,40,75,SALINE,0,100.0,10.0,0\"
                arm = line.split(":")[-1].strip()[:-1]
                arm_time = time_str
                print("At", arm_time,  arm)
                found = True
                index = 0
                if inject_digest_fh:
                    inject_digest_fh.close()
                if digest_fh:
                    digest_fh.close()

                inject_digest_name = os.path.join(out_dir, "protocol_%04d_injectdigest.csv" % (injected_count,))
                print("Creating inject digest for", inject_digest_name)
                file_list.append(inject_digest_name)
                inject_digest_fh = open(inject_digest_name, "w")
                inject_digest_fh.write(arm.strip() + " " + arm_time + '\n')
                inject_digest_fh.write(",".join(["time", "index"] + InjectDigestCommand.header))
                inject_digest_fh.write("\n")

                digest_name = os.path.join(out_dir, "protocol_%04d_digest.csv" % (injected_count,))
                digest_fh = open(digest_name, "w")
                digest_fh.write(arm.strip() + " " + arm_time + '\n')
                digest_fh.write(",".join(["time", "inject_index"] + DigestCommand.header) + '\n')
                inject_complete_state = ""

                injected_count += 1

            elif found and "RX: [INJECTDIGEST]" in line:
                index += 1
                if "SAME_AS_PREV" not in line:
                    line = line.strip()
                    arr = line.split("[")
                    line = arr[3].split("]")[0]
                    inject_digest_fh.write(time_str + "," + str(index) + "," + line + "\n")
            elif index > 0 and "RX: [DIGEST]" in line:
                # print("Found digest in", filename, "at", line)
                if "SAME_AS_PREV" not in line:
                    digest_line = line.strip()
                    arr = digest_line.split("[")
                    line = arr[3].split("]")[0]
                    if "OADI:" in line:
                        oadi_str = line[line.find("OADI:"):]
                        oadi_str = oadi_str.split("]")[0]
                        oadi_str = oadi_str.split(",")[0]
                        oadi_str = oadi_str.split(" ")[0]
                        oadi_str = ",".join(oadi_str.split(":"))  # forget the rest

                    digest_fh.write(time_str + "," + str(index) + "," + line + "\n")

                    # attempt to detect of injection status
                    # "0724-07:09:51.144 INFO : RX: [DIGEST][][0,IDLE,COMPLETED_NORMAL,..."
                    arr = line.split(",")
                    if inject_complete_state == "" and len(arr) >= 3 and arr[1] == "IDLE":
                        print("End of injection detected at", time_str, "in", filename)
                        inject_complete_state = arr[2]
                        print("Inject complete state:", inject_complete_state)
                        info_line = ",".join([
                            arm_time,
                            time_str,
                            str(injected_count),
                            oadi_str,
                            os.path.basename(inject_digest_name),
                            os.path.basename(digest_name),
                            inject_complete_state,
                            arm
                        ]) + "\n"
                        summary_fh.write(info_line)
                        oadi_str = ""

                        all_commands_fh.write(digest_line + "\n")
                        all_commands_fh.write(arm_time + " " + inject_digest_name + "\n")
                        all_commands_fh.write(arm_time + " " + digest_name + "\n")

    if inject_digest_fh:
        inject_digest_fh.close()
    if summary_fh:
        summary_fh.close()
    if digest_fh:
        digest_fh.close()
    if all_commands_fh:
        all_commands_fh.close()
    return file_list


def combine_mcu_link_log(log_list: list) -> str:
    if len(log_list) == 1:
        return log_list[0]

    if len(log_list) == 0:
        return ""

    out_name = ""
    out_fh = None
    for name in log_list:
        if out_fh is None:
            out_name = os.path.join(os.path.dirname(name), "DS_Mcu-Link-all.log")
            out_fh = open(out_name, "w")
        if os.path.exists(name):
            print("Merging", name, "to", out_name)
            with open(name) as in_fh:
                for line in in_fh:
                    out_fh.write(line)
    return out_name


def extract_diagnostic_message_from_digest_csv(csv_filename):
    """
    Extract diagnostic messages from digest csv file and save to a separate csv file for easier analysis.
    Expect the digest csv file to have the following columns:
    time,alarmcode,injector_state,inject_complete_reason,pressure,sc1,sc2,sc3,plng1,plng2,plng3,syract1,syract2,syract3,
    vol1,vol2,vol3,flow1,flow2,flow3,battery_level,ac_powered,door,wastebin,muds_present,muds_latch,inbubble1,inbubble2,inbubble3,
    suds,sudsbubble,primebtn,stopbtn,doorbtn,outlet_door_state,heater1_temperature,heater2_temperature,heater_state,shutdown_state,
    diagnostic,mcu_log_message,alarms
    """
    df = pd.read_csv(csv_filename)
    # only keep rows with diagnostic messages
    df = df[df["diagnostic"].notna() & (df["diagnostic"] != "")]

    diagnostic_message_df = pd.DataFrame(df[["time", "diagnostic"]])
    if len(diagnostic_message_df):
        diagnostic_message_filename = os.path.splitext(csv_filename)[0] + "_diagnostic_messages.csv"
        diagnostic_message_df.to_csv(diagnostic_message_filename, index=False)
        print("Created", diagnostic_message_filename)


def process_mcu_log_or_zip(log_filename, output_dir, new_oad: bool):
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    file_list = []
    sdet_df = None
    if os.path.isdir(log_filename):
        log_list = get_sru_log_file_list(os.path.join(log_filename, "DS_Mcu-Link"))
        combine_log_name = combine_mcu_link_log(log_list)
        if os.path.exists(combine_log_name):
            file_list = file_list + extract_all_injections(combine_log_name, output_dir, len(file_list) + 1)
            extract_digests(combine_log_name)
        sdet_df = parse_mcu_sdet(log_filename, output_dir)  # log_filename is a directory
        if len(sdet_df):
            plot_sdet_data(sdet_df, output_dir=output_dir, x_field="date")
            match_sdet_to_injections_at_directory(sdet_df, output_dir)
    elif log_filename.endswith(".log"):
        file_list += extract_all_injections(log_filename, output_dir, len(file_list) + 1)
        digest_csv_filename = extract_digests(log_filename)
        extract_diagnostic_message_from_digest_csv(digest_csv_filename)
        # assume no sdet data in single log file
    else:
        if log_filename.endswith('.tar.gz'):
            basename = os.path.basename(log_filename)
            output_dir = os.path.join(output_dir, os.path.splitext(basename)[0])
            if not os.path.exists(output_dir):
                os.mkdir(output_dir)

        log_list = extract_mcu_file(log_filename, output_dir)
        combine_log_name = combine_mcu_link_log(log_list)
        if os.path.exists(combine_log_name):
            file_list = file_list + extract_all_injections(combine_log_name, output_dir, len(file_list) + 1)
            digest_csv_filename = extract_digests(combine_log_name)
            extract_diagnostic_message_from_digest_csv(digest_csv_filename)

        sdet_df = parse_mcu_sdet(os.path.dirname(combine_log_name), output_dir)
        if len(sdet_df):
            plot_sdet_data(sdet_df, output_dir=output_dir, x_field="date")
            match_sdet_to_injections_at_directory(sdet_df, output_dir)

    # parse SDET data if any

    # plotting
    # copy index.html for viewing the output
    print("copying file")
    dst_index_filename = os.path.join(output_dir, "index.html")
    src_index_filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    if not os.path.exists(dst_index_filename) and os.path.exists(src_index_filename):
        print("copying file2")
        shutil.copy(src_index_filename, dst_index_filename)

    for name in file_list:
        file_list = [os.path.basename(name)]
        digest_name = "_".join(name.split("_")[:-1] + ["digest.csv"])
        if os.path.exists(digest_name):
            sdet_inject_data_df = pd.DataFrame()
            try:
                digest_df = pd.read_csv(digest_name, skiprows=1)
                digest_df["time"] = pd.to_datetime(digest_df["time"], utc=True, format='mixed')
                digest_df["injector_state"] = digest_df["injector_state"].astype("category")

                # only keep rows where injector_state is not IDLE as injecting
                digest_df = digest_df[digest_df["injector_state"] != "IDLE"]
                start_time = digest_df["time"].min()
                end_time = digest_df["time"].max()
                sdet_inject_data_df = extract_sdet_data_between_times(sdet_df, start_time, end_time)
            except Exception as e:
                digest_df = pd.DataFrame()
                print("Failed to read digest file", digest_name, "due to", e)

            if len(digest_df):
                file_list.append(os.path.basename(digest_name))
                first_row = digest_df.iloc[0]
                last_row = digest_df.iloc[-1]
                start_vols = [float(x) for x in [first_row["vol1"], first_row["vol2"], first_row["vol3"]]]
                end_vols = [float(x) for x in [last_row["vol1"], last_row["vol2"], last_row["vol3"]]]
            else:
                start_vols = end_vols = [0.0, 0.0, 0.0]
            show_result(
                csv_filename=name,
                new_oad=new_oad,
                start_volumes=start_vols,
                end_volumes=end_vols,
                filename_list=file_list,
                sdet_inject_data_df=sdet_inject_data_df
            )
        else:
            show_result(csv_filename=name, filename_list=file_list, new_oad=new_oad, )

    print("Done")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Parsing HCU-MCU logs and generating injection plots.')
    parser.add_argument('log_filename', help='The MCU log file from HCU')
    parser.add_argument('--command', default="TX: >ARM", help='The command to look for')
    parser.add_argument('--output_dir', default=".", help='output directory')
    parser.add_argument('--new_oad', action='store_true', help='Data capture with new INJECTDIGEST (has air volume)')
    args = parser.parse_args()
    process_mcu_log_or_zip(args.log_filename, args.output_dir, args.new_oad)
