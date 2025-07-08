"""
Observe counts of events over dates, weeks, months
"""
import pandas as pd
import matplotlib.pyplot as plt
import os.path
import glob
from graph import plot_pareto_chart


class FraSingleEventAnalyzer:
    def __init__(self, alert_dir: str, output_dir: str, event_name: str):
        self.alert_dir = alert_dir
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        self._df = pd.DataFrame()
        self.event_name = event_name

    def load_dataframe_from_other_event(self, event_name: str) -> pd.DataFrame:
        another_analyzer = FraSingleEventAnalyzer(self.alert_dir, self.output_dir, event_name)
        another_analyzer.load_event()
        return another_analyzer.get_df()


    def load_event(self) -> bool:
        """ Load the event data from the alert directory. If return true the data is loaded into self._df."""
        print("Loading ", self.event_name)
        output_filename = os.path.join(self.alert_dir, self.event_name + ".feather")

        if os.path.exists(output_filename):
            self._df = pd.read_feather(output_filename)
            print("load_event: Loaded pre-transformed data", len(self._df))
            return True

        output_filename = os.path.join(self.alert_dir, self.event_name + ".csv")
        if os.path.exists(output_filename):
            self._df = pd.read_csv(output_filename)
            print("load_event csv:", len(self._df))
            return True

        event_path = os.path.join(self.alert_dir, self.event_name)
        if not os.path.exists(event_path):
            alert_dir = os.path.join(self.alert_dir, "CodeName")
            if os.path.exists(alert_dir):
                self.alert_dir = alert_dir
                return self.load_event()    # try to load from CodeName directory (recusrive call)
            print("ERROR load_event() cannot find", event_path)
            return False

        all_df = []
        for filename in glob.glob(event_path + os.path.sep + "*.csv"):
            tdf = pd.read_csv(filename)

            # extract serial number
            arr = os.path.basename(filename).split("_")
            serial = arr[1]
            tdf["SN"] = serial
            all_df.append(tdf)
        df = pd.concat(all_df)
        print("loaded", self.event_name, df.shape, df.columns)
        df['ActiveAt'] = pd.to_datetime(df['ActiveAt'], utc=True, format='mixed')
        df['InactiveAt'] = pd.to_datetime(df['InactiveAt'], utc=True, format='mixed')
        df.sort_values(by=['ActiveAt'], inplace=True)   # need to sort before used
        self._df = df

        df.reset_index(inplace=True)
        df.to_feather(output_filename)
        print("Created", output_filename, len(df))
        return True

    def get_df(self):
        return self._df

    def datetime_filter(self, start_year: str, end_year:str, field='ActiveAt') -> int:
        "inclusive filtering"
        df = self._df
        df[field] = pd.to_datetime(df[field], utc=True, format="mixed")

        init_length = len(df)
        if len(start_year):
            start_year = pd.to_datetime(start_year, utc=True)   # comparison in utc  because the log is utc
            indices = df[field] >= start_year
            df = pd.DataFrame(df[indices])
        if len(end_year):
            end_year = pd.to_datetime(end_year, utc=True, format="mixed")
            indices = df[field] <= end_year
            df = pd.DataFrame(df[indices])
        print("Filtering", start_year, end_year, init_length, "->", len(df))
        self._df = df
        return len(df)

    def get_output_filename(self, postfix_with_ext: str):
        name = "%s%s" % (self.event_name, postfix_with_ext)
        return os.path.join(self.output_dir, name)

    def _save_and_close_plot(self, post_fix_ext:str):
        out_name = self.get_output_filename(post_fix_ext)
        plt.savefig(out_name)
        plt.close()
        plt.clf()
        print("Created", out_name)

    def plot_historgram(self):
        fig, ax = plt.subplots(figsize=(12, 8), tight_layout=True)
        ax.grid()
        self._df.hist("ActiveAt", ax=ax, bins=52)
        ax.set_xlabel("Date")
        ax.set_title("Histogram for %s" % (self.event_name))
        ax.set_ylabel("Count")
        # _ = ax.set_xticklabels(ax.get_xticklabels(), rotation=90)
        ax.tick_params(axis='x', labelrotation=45)
        self._save_and_close_plot("-all.png")

        fig, ax = plt.subplots(figsize=(12, 8), tight_layout=True)
        self._df["date_of_week"] = self._df['ActiveAt'].dt.day_name()
        values = self._df["date_of_week"].value_counts()
        values.plot.bar(ax=ax)
        ax.grid()
        ax.tick_params(axis='x', labelrotation=45)
        ax.set_ylabel("Count")
        ax.set_title("Daily counts for %s" % (self.event_name, ))
        self._save_and_close_plot("-date-of-the-week.png")

        self._df['Week_Number'] = self._df['ActiveAt'].dt.isocalendar().week
        values = self._df["Week_Number"].value_counts()
        values = values.sort_index()
        ax = values.plot.bar()
        ax.tick_params(axis='x', labelrotation=90)
        ax.grid()
        ax.set_title("Weeky counts for %s" % (self.event_name,))
        self._save_and_close_plot("-Week_Number-bar.png")

        self._df['month'] = self._df['ActiveAt'].dt.month_name(locale='English')
        values = self._df["month"].value_counts()
        new_order = ['January', 'February', 'March', 'April', 'May', 'June',
                     'July', 'August', 'September', 'October', 'November', 'December']
        values = values.reindex(new_order, axis=0)
        fig, ax = plt.subplots(figsize=(12, 8), tight_layout=True)
        ax = values.plot.bar(ax=ax)
        ax.tick_params(axis='x', labelrotation=45)
        ax.set_ylabel("Count")
        ax.grid()
        ax.set_title("Monthly counts for %s" % (self.event_name,))
        self._save_and_close_plot("-month-bar.png")

        self._df['day_of_the_year'] = self._df['ActiveAt'].dt.dayofyear
        values = self._df["day_of_the_year"].value_counts()
        values.sort_index(inplace=True)
        fig, ax = plt.subplots(figsize=(36, 4), tight_layout=True)
        ax = values.plot.bar(ax=ax)
        ax.tick_params(axis='x', labelrotation=90)
        ax.set_ylabel("Count")
        ax.set_xlabel("Date of the year")
        ax.grid()
        ax.set_title("Day of year %s event counts" % (self.event_name,))
        self._save_and_close_plot("-day_of_the_year.png")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Analyse single events from FRA data')
    parser.add_argument('alert_dir', type=str, help="The directory contains alerts which has been grouped all same-alert-name in a csv file")
    parser.add_argument('event_name', type=str, help="The alert name")
    parser.add_argument('--start_date', type=str, default="2023-07", help="The starting year/date (2023-07-20, or 2023)")
    parser.add_argument('--end_date', type=str, default="", help="The last inclusive year/date to included (2024, 2023-12/30)")
    parser.add_argument('--output_dir', type=str, default=".", help="The output directory")
    args = parser.parse_args()
    if not os.path.exists(args.alert_dir):
        print("invalid alert dir")
        exit(1)
    ea = FraSingleEventAnalyzer(args.alert_dir, args.output_dir, args.event_name)
    if not ea.load_event():
        print("ERROR loading the event")
        exit(1)
    count = ea.datetime_filter(args.start_date, args.end_date)
    print("count", count)
    ea.plot_historgram()


if __name__ == '__main__':
    main()
