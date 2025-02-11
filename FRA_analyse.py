import shutil
import py7zr
import pandas as pd
import os
import json
from collections import defaultdict
import datetime
import zipfile
import time
import glob
# from tqdm import tqdm


class TacReport:
    def __init__(self, filename, output_dir):
        self.df = pd.DataFrame()
        self.filename = filename
        self.output_dir = output_dir
        self.code_name_dict = defaultdict(list)
        self.summary_array = []
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)

        self._warning_filename = os.path.join(self.output_dir, "warning.txt")
        self._warning_file = open(self._warning_filename, "w", encoding="utf-8")

    def __del__(self):
        self._warning_file.close()

    def log_warning(self, *args):
        """
        log  the values to the waring file stream, and stdout
        """

        end = '\n'
        str_ = " ".join([str(x) for x in args])
        self._warning_file.write(str_ + end)
        print(str_)     # output to the stdout

    def load_sru_flight_recorder(self, filename, optional_serial_number=None):
        """Loading a file e.g. _Stellinity2/SRU/FlightRecorder-2023-03-08.json """
        if os.path.getsize(filename) < 1:
            print("WARNING: empty data", filename)
            return 0

        base = os.path.basename(filename)
        name = os.path.splitext(base)[0]
        data = json.load(open(filename, encoding='utf-8'))
        if name.startswith("FRR-"):
            serial_number = name[4:]
        else:
            if optional_serial_number is not None:
                serial_number = optional_serial_number
            else:
                # don't know the serial format let assume the whole path is the serial number
                print("WARNING: unknown FRR file name convention for", filename)
                serial_number = filename
        print(name, len(data))

        if 1:
            df = pd.read_json(filename)
            new_name = os.path.splitext(filename)[0] + ".xlsx"
            df.to_excel(new_name, index=False)
            print("created", new_name)

        for row in data:
            if "CodeName" in row:
                # row["source"] = filename
                row["SN"] = serial_number
                del row["NextAlertGuid"]    # this will reduce duplication
                self.code_name_dict[row["CodeName"]].append(row)
        return len(data)

    @staticmethod
    def ensure_unique(list_data):
        unique_set = set()
        for entry in list_data:
            if "NextAlertGuid" in entry:
                del entry["NextAlertGuid"]  # this will reduce duplication
            text = json.dumps(entry)
            unique_set.add(text)
        ret_data = [json.loads(entry) for entry in sorted(list(unique_set))]
        return ret_data

    def combine_all_codes(self):
        all_dfs = []
        for name in self.code_name_dict.keys():
            unique_arr = self.ensure_unique(self.code_name_dict[name])
            print(name, len(self.code_name_dict[name]), len(unique_arr))
            df = pd.DataFrame(unique_arr)
            all_dfs.append(df)
        df = pd.concat(all_dfs)
        df['ActiveAt'] = pd.to_datetime(df['ActiveAt'], utc=True, format="mixed")
        df['InactiveAt'] = pd.to_datetime(df['InactiveAt'], utc=True, format="mixed")

        df['ActiveAt'] = df['ActiveAt'].dt.tz_localize(None)
        df['InactiveAt'] = df['InactiveAt'].dt.tz_localize(None)

        df['latest_date'] = df[['ActiveAt', 'InactiveAt']].apply(lambda x: x.max(), axis=1)
        df.sort_values(by=['latest_date'], inplace=True)   # need to sort before used

        # df.sort_values(by=["InactiveAt", "ActiveAt"], inplace=True)
        sn_dir = os.path.join(self.output_dir, "Serial")
        if not os.path.exists(sn_dir):
            os.mkdir(sn_dir)
        feather_name = os.path.join(self.output_dir, "Serial", "SN9XXXXXXX.feather")
        df.reset_index(inplace=True)
        df.to_feather(feather_name)
        print("Created", feather_name)

        out_name = os.path.join(self.output_dir, "all_codes.xlsx")
        df.to_excel(out_name, index=False)
        print("Created", out_name, df.shape, df.columns)
        out_name = os.path.join(self.output_dir, "all_codes.csv")
        df.to_csv(out_name, index=False)
        print("Created", out_name)

    def split_by_code_name(self):
        out_dir = os.path.join(self.output_dir, "CodeName")
        summary = dict()
        if not os.path.exists(out_dir):
            os.mkdir(out_dir)
        for name in sorted(list(self.code_name_dict.keys())):
            summary[name] = len(self.code_name_dict[name])
            unique_arr = self.ensure_unique(self.code_name_dict[name])
            print(name, len(self.code_name_dict[name]), len(unique_arr))
            filename = os.path.join(out_dir, name + ".csv")
            summary[name] = len(unique_arr)
            df = pd.DataFrame(unique_arr)
            df.to_csv(filename, index=False)

        base_name = os.path.splitext(os.path.basename(self.filename))[0]
        sum_name = os.path.join(self.output_dir, base_name + ".json")
        data = dict()
        data['name'] = self.filename
        data['dateUS'] = base_name
        data['summary'] = summary
        with open(sum_name, "w") as fh:
            json.dump(data, fh, indent=2)

    @classmethod
    def load_zip(cls, tac_zip_filename, output_dir: str, ignore_set: set, want_all_data: bool):
        report = TacReport(tac_zip_filename, output_dir)
        opener, mode = zipfile.ZipFile, 'r'
        names = []
        zip_name = os.path.splitext(os.path.basename(tac_zip_filename))[0]
        print("ZIP name", zip_name)
        if "TACReport-SN" in zip_name:
            serial_number = zip_name.split("-")[1]
        else:
            serial_number = None

        try:
            # noinspection PyTypeChecker
            file = opener(tac_zip_filename, mode)
            try:
                dir(file)

                for zi in file.infolist():
                    # if member.endswith(".json") and "FlightRecorder" in member:
                    member = zi.filename
                    if member.endswith(".json"):
                        if "FRR-" in member or "FlightRecorder-" in member:
                            dir_name = os.path.dirname(member)
                            while 1:
                                parent_dir = os.path.dirname(dir_name)
                                if len(parent_dir):
                                    dir_name = parent_dir
                                else:
                                    break
                            if dir_name in ignore_set:
                                print("ignore", member)
                            else:
                                name = file.extract(member, output_dir)
                                date_time = time.mktime(zi.date_time + (0, 0, -1))
                                os.utime(name, (date_time, date_time))

                                if not want_all_data:
                                    match, date_text = cls.check_file_date_us(name, zip_name)
                                    if not match:
                                        print("not-date-skip", zip_name, date_text, member)
                                        continue
                                print("member", member)
                                names.append(os.path.join(output_dir, member))
                                report.load_sru_flight_recorder(name, serial_number)
                        else:
                            print("Skip", member)
                report.split_by_code_name()
            finally:
                file.close()
        finally:
            pass
        return names, report

    @staticmethod
    def check_file_date_us(filename: str, date_str: str) -> (bool, str):
        """check date in mm-dd-yyy format"""
        m_time = os.path.getmtime(filename)
        m_dt = datetime.datetime.fromtimestamp(m_time)
        date_text = "%02d-%02d-%d" % (m_dt.month, m_dt.day, m_dt.year)
        # print("m_time", m_time, m_dt, date_text)
        return date_text == date_str, date_text

    @classmethod
    def load_7z(cls, tac_zip_filename, output_dir: str, ignore_set: set, want_all_data: bool):
        report = TacReport(tac_zip_filename, output_dir)
        opener, mode = py7zr.SevenZipFile, 'r'
        names = []
        zip_name = os.path.splitext(os.path.basename(tac_zip_filename))[0]
        print("ZIP name", zip_name)
        try:
            file = opener(tac_zip_filename, mode)
            files_to_extract = []
            try:
                for member in file.files:
                    # if member.endswith(".json") and "FlightRecorder" in member:
                    filename = member.filename
                    if filename.endswith(".json"):
                        if "FRR-" in filename:
                            arr = filename.split("/")
                            if len(arr) > 2 and arr[1] in ignore_set:
                                skip = True
                            elif len(arr) > 1 and arr[0] in ignore_set:
                                skip = True
                            else:
                                skip = False
                            if skip:
                                print("ignore", filename)
                            else:
                                print("member", filename)
                                files_to_extract.append(filename)
                        else:
                            print("Skip", filename)
                # extract in batches
                file.extract(output_dir, targets=files_to_extract)
                for filename in files_to_extract:
                    name = os.path.join(output_dir, filename)
                    if not want_all_data:
                        match, date_text = cls.check_file_date_us(name, zip_name)
                        if not match:
                            print("not-date-skip", zip_name, date_text, filename)
                            continue
                    names.append(name)
                    # print("processing", name)
                    report.load_sru_flight_recorder(name)
                report.split_by_code_name()
            finally:
                file.close()
        finally:
            pass
        return names, report

    @staticmethod
    def get_all_json_group_by_serial(dir_name) -> dict:
        """ return a dictionary of filename with serial number as dictionary key"""
        all_files = {}
        for filename in glob.glob(dir_name + "/*"):
            if os.path.isdir(filename):
                serial = os.path.basename(filename)
                all_files[serial] = []
                for json_name in glob.glob(filename + "/*.json"):
                    all_files[serial].append(json_name)
            else:
                print("skip", filename)

        return all_files

    def save_summary(self):
        filename = os.path.join(self.output_dir, "summary.csv")
        df = pd.DataFrame(self.summary_array)
        df.to_csv(filename, index=False)

    def proceess_frr_from_dir(self, dir_name):
        """ Each subdirectory is a unique machine identifying by the serial number, then FRA per day in json form
            for each serial number:
            - ensure the entries are uniques.
            - output each alert into a file ( <last_occurance>_<SN>_<event>.csv
         """
        all_files_dict = self. get_all_json_group_by_serial(dir_name)
        print("loading", dir_name, "num files", len(all_files_dict))
        for serial, file_list in all_files_dict.items():
            if len(file_list):
                self._process_single_machine_fra(serial, file_list)

    def _rows_are_equal(self, r1: dict, r2: dict, filename: str) -> bool:
        diff = []
        for key in r1.keys():
            if key in r2:
                if r1[key] != r2[key]:
                    if r1['CodeName'] == "ExamFinalized" and key == "Data":
                        # the Data field of the patient ID is anonymized. each time request log the anonymized value
                        # will be different value let assume they are the same for ExamFinalized
                        continue
                    diff.append(key)

        if len(diff) > 0:
            self.log_warning("diff", diff, filename)
            self.log_warning("r1", r1)
            self.log_warning("r2", r2)
            return False

        return True

    def _process_single_machine_fra(self, serial_number: str, file_list):
        empty_file_count = 0
        code_name_dict = dict()
        by_serial_dir = os.path.join(self.output_dir, "Serial")
        if not os.path.exists(by_serial_dir):
            os.mkdir(by_serial_dir)
        # serial_filename = os.path.join(by_serial_dir, serial_number + ".csv")
        feather_filename = os.path.join(by_serial_dir, serial_number + ".feather")
        if os.path.exists(feather_filename):
            print("Skip", feather_filename)
            return

        for filename in file_list:
            if os.path.getsize(filename) <= 2:
                # print("WARNING: empty file", filename)
                empty_file_count += 1
                continue
            try:
                data = json.load(open(filename, encoding='utf-8'))
            except json.JSONDecodeError:
                print("WARNING: skip due to json error for", filename)
                with open(os.path.join(self.output_dir, "json_error.txt"), "a") as fh:
                    fh.write(filename + "\n")
                continue
            # print("loading", name, len(data))
            for row in data:
                if "CodeName" in row:
                    del row["NextAlertGuid"]   # this could be changed over time
                    id_str = row["ActiveAt"] + row["GUID"]
                    # id_str = row["GUID"]
                    if id_str in code_name_dict:
                        org_row = code_name_dict[id_str]
                        if org_row["InactiveAt"] is not None and row["InactiveAt"] is None:
                            continue    # the current record data already up to day
                        if org_row["InactiveAt"] is None:
                            code_name_dict[id_str] = row   # replace and hope for the update
                        elif self._rows_are_equal(row, org_row, filename):
                            pass
                        elif org_row["InactiveAt"] is not None and row["InactiveAt"] is not None and org_row["InactiveAt"] < row["InactiveAt"]:
                            # handle this case:
                            # r1 {... 'InactiveAt': '2024-01-10T07:39:34.883Z', 'CodeName': 'TimeoutExamEnded', ...}
                            # r2 {... 'InactiveAt': '2024-01-09T18:18:52.439Z', 'CodeName': 'TimeoutExamEnded', ...}
                            code_name_dict[id_str] = row  # replace and hope for the update
                    else:
                        code_name_dict[id_str] = row

        if len(code_name_dict) > 0:
            df = pd.DataFrame(code_name_dict.values())
            df['ActiveAt'] = pd.to_datetime(df['ActiveAt'], utc=True, format="mixed")
            df.sort_values('ActiveAt', inplace=True)
            # df.to_csv(serial_filename, index=False)
            df.reset_index(inplace=True)
            df.to_feather(feather_filename)
            start_day = df['ActiveAt'].dt.date[0]
            last_day = df['ActiveAt'].dt.date[len(df)-1]
            print("output", start_day, last_day, len(df), feather_filename)
            self.summary_array.append({
                "serial": serial_number,
                "name": feather_filename,
                "count": len(df),
                "first_day": start_day,
                "last_day": last_day
            })

            code_name_base_dir = os.path.join(self.output_dir, "CodeName")
            if not os.path.exists(code_name_base_dir):
                os.mkdir(code_name_base_dir)

            unique_code_names = df['CodeName'].unique()
            for code_name in unique_code_names:
                dff = pd.DataFrame(df[df['CodeName'] == code_name])
                dff['ActiveAt'] = pd.to_datetime(dff['ActiveAt'], utc=True, format="mixed")
                if len(dff) > 0:
                    code_name_dir = os.path.join(code_name_base_dir, code_name)
                    if not os.path.exists(code_name_dir):
                        os.mkdir(code_name_dir)
                    last_row = dff.iloc[-1]
                    last_day = str(last_row['ActiveAt'].date())
                    name = "%s_%s_%s.csv" % (last_day, serial_number, code_name)
                    code_name_csv = os.path.join(code_name_dir, name)
                    dff.to_csv(code_name_csv, index=False)


def analyse_compressed_tac_directory(tac_file: str, output_dir: str, want_all_data: bool):
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    ignore_set = set()
    if os.path.isdir(tac_file):
        import glob
        ignore_file = os.path.join(tac_file, "ignore.txt")
        if os.path.exists(ignore_file):
            with open(ignore_file) as fh:
                for line in fh:
                    line = line.strip()
                    if len(line):
                        ignore_set.add(line)

        for filename in glob.glob(tac_file + "/*.7z"):
            # name is US date in mm-dd-yyy
            name = os.path.splitext(os.path.basename(filename))[0]
            print("TAC", filename, name)
            out_dir = os.path.join(output_dir, name)
            if not os.path.exists(out_dir):
                os.mkdir(out_dir)
                _ = TacReport.load_7z(filename, out_dir, ignore_set, want_all_data)
            else:
                print("Skip analyzing", filename)

        for filename in glob.glob(tac_file + "/*.zip"):
            # name is US date in mm-dd-yyy
            name = os.path.splitext(os.path.basename(filename))[0]
            print("TAC", filename, name)
            out_dir = os.path.join(output_dir, name)
            if not os.path.exists(out_dir):
                os.mkdir(out_dir)
                names, reporter = TacReport.load_zip(filename, out_dir, ignore_set, want_all_data)
                reporter.combine_all_codes()
            else:
                print("Skip analyzing", filename)

    else:
        names, reporter = TacReport.load_zip(tac_file, output_dir, ignore_set, want_all_data)
        reporter.combine_all_codes()


def move_file_by_serial_number_and_date(filename: str, output_dir: str):
    m_time = os.path.getmtime(filename)
    m_dt = datetime.datetime.fromtimestamp(m_time)
    date_text = "%d-%02d-%02d" % (m_dt.year, m_dt.month, m_dt.day)
    name, ext = os.path.splitext(os.path.basename(filename))
    if name.startswith("FRR-"):
        serial_number = name[4:]
        name = "%s-%s%s" % (serial_number, date_text, ext)
        output_dir = os.path.join(output_dir, serial_number)
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
    else:
        name = "%s-%s%s" % (name, date_text, ext)
    dest = os.path.join(output_dir, name)
    shutil.move(filename, dest)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='TAC data extraction and analysis')
    parser.add_argument('--TAC_file', type=str, default=None, help="The TAC zip file or a directory contain all the TAC zip file")
    parser.add_argument('--combine', type=str,  help="The combine directory contain all the TAC zip file")
    parser.add_argument('--output_dir', type=str, default=".", help="Output directory")
    parser.add_argument('--verbose', action='store_true', help="Verbose")
    parser.add_argument('--all', action='store_true', help="Want all data (no filtering")

    args = parser.parse_args()
    if args.TAC_file:
        analyse_compressed_tac_directory(args.TAC_file, args.output_dir, args.all)
    if args.combine:
        report = TacReport(args.combine, args.output_dir)
        report.proceess_frr_from_dir(args.combine)
        report.save_summary()


if __name__ == '__main__':
    main()
