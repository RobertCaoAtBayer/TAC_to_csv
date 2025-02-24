"""
Export all ADB backup to:
- csv per table
- Extract flight recorder data into
-- json per file
-- one big csv
"""
import sys
import pandas as pd
import os.path
import pgdumplib         # for postgresql dump file
import json
import zipfile
import pyzipper
from FRA_analyse_mcu_diagnostic_suds import generate_suds_analog_summary
# from IPython.core.compilerop import code_name


def get_serials_from_comm_service_resumed(df: pd.DataFrame) -> dict:
    """
          "CodeName": "CommServiceResumed", "Data": "Stellinity2;100049",

    @param df:
    @return:
    """
    fdf = df[df['CodeName'] == "CommServiceResumed"]
    ret_dict = {"SRUSerial": "unknown"}

    if len(fdf) == 0:
        return ret_dict
    else:
        for i, row in fdf.iterrows():
            data = row["Data"].split(";")
            if len(data) == 2:
                ret_dict["InjectorType"] = data[0]
                ret_dict["SRUSerial"] = data[1]
            else:
                print("ERROR: CommServiceResumed data", data)
        if "SRUSerial" not in ret_dict:
            ret_dict["SRUSerial"] = "unknown"
        return ret_dict


def get_serials_from_system_identification_information(df: pd.DataFrame) -> dict:
    """
    SystemIdentificationInformation
    {
      ""InjectorType"": ""Centargo"",
      ""CRUSerial"": ""100095"",
      ""CRUSoftwareVersion"": ""2023.0401.23093.1325"",
      ""SRUSerial"": ""100098"",
      ""SRUSoftwareVersion"": ""2023.0302"",
      ""SIDAlertVersion"": 1
    }
    """
    fdf = df[df['CodeName'] == "SystemIdentificationInformation"]
    ret_dict = {"SRUSerial": "unknown"}
    if len(fdf) == 0:
        return ret_dict
    else:
        ret_dict = {}
        for i, row in fdf.iterrows():
            data = json.loads(row["Data"])
            if "SRUSerial" in data:
                val = data["SRUSerial"]
                if val.lower() != "unknown":
                    ret_dict["SRUSerial"] = val     # overriding
        return ret_dict


def get_serial_number_from_data_frame(df: pd.DataFrame) -> str:
    # detect the serial number base on the wireless network started data (CRUWirelessNetworkStarted)
    if len(df) == 0:
        return "unknown"

    fdf = df[df['CodeName'] == "CRUWirelessNetworkStarted"]
    serial = "unknown"
    if len(fdf):
        for _, row in fdf.iterrows():
            data = row["Data"]
            serial = data.split(";")[0].split("_")[-1]

    if serial == "unknown":
        info = get_serials_from_comm_service_resumed(df)
        serial = info["SRUSerial"]

    if serial == "unknown":
        info = get_serials_from_system_identification_information(df)
        serial = info["SRUSerial"]

    if serial.startswith("SN"):
        return serial
    else:
        return f"SN{serial}"


def merge_duplicate_alerts(alert1: dict, alert2: dict) -> dict:
    """Merge two alerts"""
    if alert1["GUID"] != alert2["GUID"]:
        print("ERROR: not the same GUID. Not expect to be here")
        print("alert1", alert1)
        print("alert2", alert2)
        sys.exit(1)
    if alert1["ActiveAt"] != alert2["ActiveAt"]:
        print("WARNING: not the same ActiveAt. Not expect to be here")
    if alert1["InactiveAt"] is None:
        return alert2
    else:
        if alert1["InactiveAt"] is not None and alert2["InactiveAt"] is not None:
            if alert1["InactiveAt"] != alert2["InactiveAt"]:
                print("WARNING: not the same InactiveAt. Not expect to be here")
                print(alert1)
                print(alert2)
        # assume both alert are the same
        return alert1


def extract_alert_from_tac_report_zip(zip_file_path: str, output_dir: str) -> pd.DataFrame:
    """Extract alert from TACReport zip file"""

    # noinspection DuplicatedCode
    def extract_compressed_file(filename: str, to_directory='.') -> list:
        opener, mode = pyzipper.ZipFile, 'r'

        names = []
        try:
            file = opener(filename, mode)
            try:
                for member in file.namelist():   # FlightRecorder-2024-05-29.json
                    if "FlightRecorder-" in member and member.endswith(".json"):
                        print("Extracting", member)
                        file.extract(member, to_directory)
                        names.append(os.path.join(to_directory, member))
            finally:
                file.close()
        finally:
            pass
        names = sorted(names)
        return names

    file_list = extract_compressed_file(zip_file_path, output_dir)
    all_alert_map = {}
    duplicate_counts = 0
    serial = "unknown"
    for fra_filename in file_list:
        # print(fra_filename)
        df = pd.read_json(fra_filename)
        if len(df):
            print("Processing", fra_filename, len(df))
        else:
            continue
        new_serial = get_serial_number_from_data_frame(df)
        if new_serial != serial:
            if new_serial != "SNunknown":       # assume the last serial number is the correct one
                print("Serial number changed", serial, new_serial)
                serial = new_serial
        for index, row in df.iterrows():
            guid = row["GUID"]
            if guid in all_alert_map:
                value = merge_duplicate_alerts(all_alert_map[guid], row.to_dict())
                duplicate_counts += 1
            else:
                value = row.to_dict()
            value["SN"] = serial
            all_alert_map[guid] = value

    print("len(all_alert_map)", len(all_alert_map))
    new_df = pd.DataFrame(all_alert_map.values())

    print("Total alerts", len(new_df),"duplicate:", duplicate_counts, " columns:", new_df.columns)
    new_df.sort_values(by=['ActiveAt'], inplace=True)
    return new_df


def extract_alert_from_memento(df: pd.DataFrame, output_dir: str, output_json=False) -> pd.DataFrame:
    """Extract alert from pgdumplib memento data frame"""
    all_alert_map = {}
    serial = "unknown"
    for i, row in df.iterrows():
        if row["name"].startswith("FlightRecorder-"):
            content = row["content_flex"]
            x = content.replace("\\r\\n", "\n")
            x2 = x.replace("\\\\\"", '\\\"')
            if output_json:
                out_name = os.path.join(output_dir, row["name"] + ".json")
                with open(out_name, "w") as f:
                    f.write(x2)
                    print("Created", out_name)
            alert_map = json.loads(x2)['AlertMap']
            new_serial = get_serial_number_from_data_frame(pd.DataFrame(alert_map.values()))
            if new_serial != serial:
                if new_serial != "SNunknown":       # assume the last serial number is the correct one
                    print("Serial number changed", serial, new_serial)
                    serial = new_serial

            print(row["name"], len(alert_map))
            for key, value in alert_map.items():
                if key in all_alert_map:
                    # print("duplicate key", key, value)
                    value = merge_duplicate_alerts(all_alert_map[key], value)
                else:
                    all_alert_map[key] = value
                value["SN"] = serial
                all_alert_map[key] = value

    new_df = pd.DataFrame(all_alert_map.values())
    print("Total alerts", len(new_df), new_df.columns)
    new_df.sort_values(by=['ActiveAt'], inplace=True)

    # detect the serial number base on the wireless network started
    # serial = get_serial_number_from_data_frame(new_df)
    # output_feather = os.path.join(output_dir, f"{serial}.feather")
    # output_excel = os.path.join(output_dir, f"{serial}.xlsx")
    # new_df.to_excel(output_excel, index=False)
    # print("output name", output_excel)

    new_df['ActiveAt'] = pd.to_datetime(new_df['ActiveAt'], utc=True)
    new_df['InactiveAt'] = pd.to_datetime(new_df['InactiveAt'], utc=True)
    new_df.reset_index(inplace=True)
    # new_df.to_feather(output_feather)
    # print("output feather", output_feather)
    return new_df


def get_table_members(_entry) -> list:
    """
    @param _entry: pgdumplib.Entry
    @return:
    """
    arr = _entry.defn.split("\n")[1:-2]
    arr = [x.strip().split(" ")[0] for x in arr]
    return arr


def table_to_data_frame(dump, entry) -> pd.DataFrame:
    """Convert the table to data frame
    @param dump: pgdumplib.Dump
    @param entry: pgdumplib.Entry
    """
    _table = dump.table_data(entry.namespace, entry.tag)
    _members = get_table_members(entry)
    data = [list(row) for row in _table]
    return pd.DataFrame(data, columns=_members)


def adb_to_csv(name: str, output_dir: str, output_json) -> pd.DataFrame:
    """Convert the adb file(.backup) to csv"""
    print("Convert the adb file(.backup) to csv", name)
    # noinspection PyTypeChecker
    dump = pgdumplib.load(name)
    print('Database: {}'.format(dump.dbname))
    print('Archive Timestamp: {}'.format(dump.timestamp))
    print('Server Version: {}'.format(dump.server_version))
    print('Dump Version: {}'.format(dump.dump_version))
    for entry in dump.entries:
        print(entry.namespace, entry.desc, entry.tag)
        if entry.desc == "TABLE":
            df = table_to_data_frame(dump, entry)
            if len(df):
                output_name = os.path.join(output_dir, f"{entry.tag}.csv")
                df.to_csv(output_name, index=False)
                print("output to", output_name)
                if entry.tag == "memento":
                    return_df = extract_alert_from_memento(df, output_dir, output_json=output_json)
                    return return_df
    return pd.DataFrame()


def adb_zipfile_to_csv(zip_file_path: str, output_dir: str, output_json) -> pd.DataFrame:
    """Extract the zip file to output_dir"""
    output_dir = os.path.abspath(output_dir)
    if zip_file_path.endswith(".backup"):
        return adb_to_csv(zip_file_path, output_dir, output_json)
    return_df = pd.DataFrame()

    with pyzipper.AESZipFile(zip_file_path, 'r', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as extracted_zip:
        password = "C3rt3gr@!".encode("utf8")
        for info in extracted_zip.infolist():
            if info.filename.endswith(".backup"):
                print("Extracting", info.filename)
                extracted_zip.extract(info, path=output_dir, pwd=password)
                name = os.path.join(output_dir, info.filename)
                print("extracted to", name)
                return adb_to_csv(name, output_dir, output_json)

    opener, mode = zipfile.ZipFile, 'r'
    try:
        print("here3")
        # noinspection PyTypeChecker
        file = opener(zip_file_path, mode)
        try:
            for member in file.namelist():
                print("member", member)
                if member.endswith(".backup"):
                    print("Extracting", member)
                    file.extract(member, output_dir)
                    adb_filename = os.path.join(output_dir, member)
                    return adb_to_csv(adb_filename, output_dir, output_json)
        finally:
            file.close()
    finally:
        pass

    return return_df


def split_df_by_code_name(df: pd.DataFrame, output_dir: str):
    out_dir = os.path.join(output_dir, "CodeName")
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    for name in sorted(list(df['CodeName'].unique())):
        fdf = pd.DataFrame(df[df['CodeName'] == name])
        filename = os.path.join(out_dir, name + ".csv")
        fdf.to_csv(filename, index=False)
        print("Created ", filename)


def generate_output_from_df(all_df: pd.DataFrame, output_dir: str):
    for serial in all_df['SN'].unique():
        df = pd.DataFrame(all_df[all_df['SN'] == serial])
        generate_output_from_df_for_serial(serial, df, output_dir)


def generate_output_from_df_for_serial(injector_serial: str, all_df: pd.DataFrame, output_dir: str):
    print("serial", injector_serial)
    output_dir = os.path.join(output_dir, injector_serial)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    all_df.reset_index(inplace=True)
    if "NextAlertGuid" in all_df.columns:
        all_df.drop(columns=['NextAlertGuid'], inplace=True)
    print("All data", all_df.columns, all_df.shape)
    all_df["ActiveAt"] = pd.to_datetime(all_df["ActiveAt"], utc=True)
    all_df["InactiveAt"] = pd.to_datetime(all_df["InactiveAt"], utc=True)
    serial_dir = os.path.join(output_dir, "Serial")
    if not os.path.exists(serial_dir):
        os.mkdir(serial_dir)
    all_df.to_csv(os.path.join(serial_dir, injector_serial + ".csv"), index=False)
    all_df.to_feather(os.path.join(serial_dir, injector_serial + ".feather"))
    print("Created", os.path.join(serial_dir, injector_serial + ".csv"))
    print("Created", os.path.join(serial_dir, injector_serial + ".feather"))

    split_df_by_code_name(all_df, output_dir)
    counts = all_df['CodeName'].value_counts()
    counts.sort_values(ascending=False, inplace=True)
    name = os.path.join(output_dir, "summary.csv")
    counts.to_csv(name)
    print("Created", name)

    generate_suds_analog_summary(all_df, output_dir, injector_serial)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Centegra ADB conversion')
    parser.add_argument('--adb', type=str, default="", help='The Centegra ADB backup file zip')
    parser.add_argument('--tac', type=str, default="", help='The Centegra TacReport zip file')
    parser.add_argument('--output_json', type=bool, action=argparse.BooleanOptionalAction, default=False, help='Output the FRA json files')
    parser.add_argument('--output_dir', type=str, default=".", help="The output directory")
    args = parser.parse_args()
    if not args.adb and not args.tac:
        print("Nothing to do")
        return False
    output_dir = args.output_dir
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    adb_filename = args.adb
    tac_filename = args.tac
    output_json = args.output_json

    process_adb_or_tac_files(adb_filename, tac_filename, output_dir, output_json)


def process_adb_or_tac_files(adb_filename, tac_filename, output_dir, output_json=False):
    adb_df = None
    tac_df = None
    if adb_filename:
        print("ADB", adb_filename)
        adb_df = adb_zipfile_to_csv(adb_filename, output_dir, output_json)
    if tac_filename:
        tac_df = extract_alert_from_tac_report_zip(tac_filename, output_dir)
    # combine the adb and tac data frame
    if adb_df is not None and tac_df is not None:
        print("Combining the data frame and remove duplicate")

        adb_df.set_index('GUID', inplace=True)
        all_dict = adb_df.to_dict("index")

        tac_df.set_index('GUID', inplace=True)
        tac_df["ActiveAt"] = pd.to_datetime(tac_df["ActiveAt"], utc=True, format='mixed')
        tac_df["InactiveAt"] = pd.to_datetime(tac_df["InactiveAt"], utc=True, format='mixed')

        tac_dict = tac_df.to_dict("index")
        new_count = 0
        for key, value in tac_dict.items():
            if key in all_dict:
                d1 = all_dict[key]
                d2 = value
                d1["GUID"] = key
                d2["GUID"] = key
                all_dict[key] = merge_duplicate_alerts(d1, d2)
            else:
                all_dict[key] = value
                new_count += 1
                print("new", value)

        all_df = pd.DataFrame(all_dict.values())
        all_df.sort_values(by=['ActiveAt'], inplace=True)
        all_df.drop(columns=['index'], inplace=True)

        generate_output_from_df(all_df, output_dir)
    else:
        if adb_df is not None:
            generate_output_from_df(adb_df, output_dir)
        if tac_df is not None:
            generate_output_from_df(tac_df, output_dir)


if __name__ == '__main__':
    main()
