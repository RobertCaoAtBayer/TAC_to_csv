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


class DigestsData:

    def __init__(self):
        self.data = []

    def from_mcu_log(self, log_filename):
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
    digest_data.save_digests(os.path.splitext(log_filename)[0] + "_digests.csv")

def get_sru_log_file_list(prefix):
    return [prefix + "." + ext for ext in ['old3.log', 'old2.log', 'old1.log', 'log']]


def parse_SRU_bottle_data(dir_name):
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
                if "DS_Mcu-Link" in member_name:
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
    out_fh = None
    file_list = list()

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    with open(filename) as fh:
        for line in fh:
            if "TX: >ARM" in line:
                # "0906-04:39:23.829 INFO : TX: >ARM@2068,1,SALINE,40,75,SALINE,0,100.0,10.0,0\"
                arm = line.split(":")[-1].strip()[:-1]
                arm_time = line.split(" ")[0]
                print("At", arm_time,  arm)
                found = True
                index = 0
                if out_fh:
                    out_fh.close()

                out_name = os.path.join(out_dir, "protocol_%04d_injectdigest.csv" % (injected_count,))
                print("Creating inject digest for", out_name)
                file_list.append(out_name)
                injected_count += 1
                out_fh = open(out_name, "w")
                out_fh.write(arm.strip() + " " + arm_time + '\n')
                out_fh.write(",".join(["index"] + InjectDigestCommand.header))
                out_fh.write("\n")
            elif found and "RX: [INJECTDIGEST]" in line:
                index += 1
                if "SAME_AS_PREV" not in line:
                    line = line.strip()
                    arr = line.split("[")
                    line = arr[3].split("]")[0]
                    out_fh.write(str(index) + "," + line + "\n")
    if out_fh:
        out_fh.close()
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


def process_mcu_log_or_zip(log_filename, output_dir, new_oad: bool):
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    file_list = []
    if os.path.isdir(log_filename):
        log_list = get_sru_log_file_list(os.path.join(log_filename, "DS_Mcu-Link"))
        combine_log_name = combine_mcu_link_log(log_list)
        if os.path.exists(combine_log_name):
            file_list = file_list + extract_all_injections(combine_log_name, output_dir, len(file_list) + 1)
    elif log_filename.endswith(".log"):
        file_list += extract_all_injections(log_filename, output_dir, len(file_list) + 1)
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
            extract_digests(combine_log_name)

    # plotting
    # copy index.html for viewing the output
    print("copying file")
    dst_index_filename = os.path.join(output_dir, "index.html")
    src_index_filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    if not os.path.exists(dst_index_filename) and os.path.exists(src_index_filename):
        print("copying file2")
        shutil.copy(src_index_filename, dst_index_filename)

    for name in file_list:
        show_result(csv_filename=name, filename_list=[name], new_oad=new_oad)

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
