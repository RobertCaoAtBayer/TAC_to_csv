import csv
import os.path

import matplotlib.pyplot as plt
import numpy as np
from bokeh.io import output_file, show, save
from bokeh.layouts import column
from bokeh.plotting import figure
from bokeh.models import BoxAnnotation, Span, LinearAxis, Range1d, SingleIntervalTicker
from bokeh.palettes import Paired12 as MyColors
import pandas as pd
from bokeh.models import ColumnDataSource
from bokeh.models.widgets import DataTable, TableColumn, PreText, Div
from Commands import InjectDigestCommand, Stopcock_id_to_name
from Protocol import Protocol
from datetime import datetime
from dateutil import tz


def hcu_utc_time_to_tz_datetime(val: str, tz_name='Australia/Sydney') -> datetime:
    """val is '1208-10:14:14.646'
    example:
        us_time = hcu_utc_time_to_tz_datetime(utc_string, tz_name="America/Indiana/Indianapolis")
        sydney_time = hcu_utc_time_to_tz_datetime(utc_string, tz_name='Australia/Sydney')
    """
    # year_prefix_str = str(datetime.now().year)
    # val = year_prefix_str + val
    from_zone = tz.gettz('UTC')
    utc = datetime.strptime(val, "%Y%m%d-%H:%M:%S.%f").replace(tzinfo=from_zone)
    to_zone = tz.gettz(tz_name)
    local_dt = utc.astimezone(to_zone)
    return local_dt


def hcu_time_str_to_pittsburgh_tz_str(utc_string: str) -> str:
    return hcu_utc_time_to_tz_datetime(utc_string, tz_name="America/Indiana/Indianapolis").strftime("%Y-%m-%d %H:%M:%S")

def hcu_time_str_to_sydney_tz_str(utc_string: str) -> str:
    return hcu_utc_time_to_tz_datetime(utc_string, tz_name='Australia/Sydney').strftime("%Y-%m-%d %H:%M:%S")


# InjectDigestData.headers:
# 0 phase
# 1 adaptive_flow
# 2 scheduled_pulsing_active
# 3 unscheduled_pulsing_active
# 4 injection_pressure
# 5 saline_pressure
# 6 contrast1_pressure
# 7 contrast2_pressure
# 8 saline_PID
# 9 contrast1_PID
# 10 contrast2_PID
# 11 saline_SC_position
# 12 contrast1_SC_position
# 13 contrast2_SC_position
# 14 saline_motor_position
# 15 contrast1_motor_position
# 16 contrast2_motor_position
# 17 saline_ss_reduction
# 18 contrast1_ss_reduction
# 19 contrast2_ss_reduction
# 20 saline_stored_compliance
# 21 contrast1_stored_compliance
# 22 contrast2_stored_compliance
# 23 saline_phase_compliance
# 24 contrast1_phase_compliance
# 25 contrast2_phase_compliance
# 26 patient_line_air_counts -> air vol in micro litre
# 27 pin_120
# 28 pin_121
# 29 patient_line_air_volume_ul
# 30 3mm_port
# 31 saline_flow_rate_phase
# 32 contrast1_flow_rate_phase
# 33 contrast2_flow_rate_phase
# 34 saline_vol_pushed
# 35 contrast1_vol_pushed
# 36 contrast2_vol_pushed
# 37 saline_vol_delivered_phase_i
# 38 contrast1_vol_delivered_phase_i
# 39 contrast2_vol_delivered_phase_i
# 40 duration_phase_i


PULSES_PER_10ML = 83577         # Centargo count per 10 ml


class InjectDigestData:
    def __init__(self, verbose=False):
        self.data = []
        self.headers = []
        self._df = None
        self.protocol = None
        self._phase_time = None
        self._phase_durations = []   # phase duration in seconds
        self.verbose = verbose
        self.protocol_extra = ""  # name etc

    @staticmethod
    def stopcock_id_to_name(index: int) -> str:
        if len(Stopcock_id_to_name) > index >= 0:
            index = int(index)
            return Stopcock_id_to_name[index]
        return "BAD_STOPCOCK_ID(%d)" % index

    def get_phase_durations(self):
        if self._phase_time is None:
            self.get_phase_time()
        return self._phase_durations

    def load_file(self, filename, verbose=False):
        """
        Expect the file contains
        first line: ARM command
        second line header file
        the remains subsequent lines:  <index>, <inject digest data>
        :param filename: the inject-digest filename
        :param verbose:
        :return: the number of rows has been loaded
        """
        data = []
        self._phase_time = None
        self._phase_durations = []

        with open(filename) as fh:
            # from the HCU log the file contains ARM as the first line
            # the 2nd line is the header
            line = fh.readline()
            if ">ARM" == line[0:4].upper():
                # Protocol from HCU
                arr = line[line.find(">ARM"):].strip().split("\\")
                protocol = arr[0].strip()  # remove trailing "\\"
                self.protocol_extra = "\\".join(arr[1:])
                self.protocol = Protocol.from_string(protocol)
                line = fh.readline()
            # else the first line contains the header
            headers = line.split(",")
            headers[-1] = headers[-1].strip()
            # for i, field in enumerate(headers):
            #    print("#", i, field)

            idc = InjectDigestCommand()

            # detect the first data format:
            line = fh.readline()
            arr_str = line.split(",")
            # noinspection PyBroadException
            # noinspection PyBroadException
            try:
                # strip the index out
                # idx = float(arr_str[0])
                arr = [float(x) for x in idc.parse_response(",".join(arr_str[2:]), verbose=verbose)]
                headers = headers[2:]  # strip out the index
                start_time_str = arr_str[0]
                start_time = pd.to_datetime(arr_str[0], format="%Y%m%d-%H:%M:%S.%f", utc=True)
                arr = arr  + [start_time]  # starting with 0 delta time
                headers += ["datetime"]  # add the delta time column
            except:
                print("LINE:", arr_str)
                print("ERROR invalid inject digest data format in ", filename)
                return False
            data.append(arr)

            while 1:
                line = fh.readline()
                if not line:
                    break
                arr_str = line.split(",")
                # noinspection PyBroadException
                try:
                    # strip out the time and index because parse response doesn't handle index
                    arr = [float(x) for x in idc.parse_response(",".join(arr_str[2:]), verbose=verbose)]
                    id_time = pd.to_datetime(arr_str[0], format="%Y%m%d-%H:%M:%S.%f", utc=True)
                    arr = arr + [id_time]
                except:
                    arr = None
                    pass  # skip error
                if arr is not None:
                    data.append(arr)

        self.headers = headers
        if len(data) <= 1:   # if there is only 1 data point, it is not useful
            print("No data in", filename)
            self.data = np.array([])
            self._df = None
            return 0
        if verbose:
            print("data before", len(data))
            print(data[0])
        self.data = np.array(data)

        if verbose:
            print("data shape", self.data.shape, "header shape", len(self.headers))
            print(self.headers)

        if self.data.shape[1] > 0:  # can have an empty 2D array which has a length greater than 1
            # this is to use with Ethan's pressure gauge ADC to PSI conversion
            # df["ActualPressure"] = 515 * df['FLCAL'] / 4095.0 - 15
            # noinspection PyTypeChecker
            # current column 27 is air counts
            self.data[:, 27] = self.data[:, 27] * 515 / 4095.0 - 15  # pin_120

            # kPA to psi
            for i in (4, 5, 6, 7, 29):
                self.data[:, i] /= 6.894757

            self._df = pd.DataFrame({name: self.data[:, i] for i, name in enumerate(self.headers)})
            self._df["Time(s)"] = self.get_phase_time()

            output_file_name = os.path.splitext(filename)[0] + "_post.csv"
            self._df.to_csv(output_file_name, index=False)

            # it is done above
            # pin_120 is FLCAL port ADC via injectdigest data
            # this is to use pressure gauge ADC to PSI conversion
            # self._df["ActualPressure(psi)"] = self._df['pin_120'] * 515 / 4095.0 - 15  # pin_120
            # 'injection_pressure', 'saline_pressure', 'contrast1_pressure', 'contrast2_pressure'
            # self._df["InjectionPressure(psi)"] = self._df['injection_pressure'] / 6.894757
            # self._df["SalinePressure(psi)"] = self._df['saline_pressure'] / 6.894757
            # self._df["Contrast1Pressure(psi)"] = self._df['contrast1_pressure'] / 6.894757
            # self._df["Contrast2Pressure(psi)"] = self._df['contrast2_pressure'] / 6.894757
        else:
            self._df = None

        return len(self.data)

    def get_df(self) -> pd.DataFrame:
        return self._df

    def plot_oad_air_count(self, output_filename=None) -> (float, float):
        """Plot the outlet air detector result (old firmware does not have OAD volume log)"""
        ts, te = self.get_air_start_end_time()
        if ts >= te:
            print("Skip OAD plot because it is empty", ts, te)
            return ts, te
        df = self.get_df()
        cdf = pd.DataFrame(df[df['Time(s)'].between(ts - 0.2, te + 0.2)])
        if len(cdf) == 0:
            print("No data in the time range", ts, te)
            return 0, 0
        cdf['air_count'] = cdf['patient_line_aircounts']
        cdf['delta_air_count'] = cdf.air_count.diff()

        ax = cdf.plot("Time(s)", "air_count", c='green')
        ax.grid()
        ax.set_ylabel("Air count")
        ax.yaxis.label.set_color('green')
        ax.legend(loc='upper left')

        ax2 = ax.twinx()
        cdf.plot.scatter("Time(s)", "delta_air_count", ax=ax2,  c='green')
        ax2.set_ylabel("Delta Air Count")
        ax2.legend(loc='lower right')
        ax2.yaxis.label.set_color('green')
        ax.set_title("%s (%.3fs - %.3fs)" % (os.path.splitext(os.path.basename(output_filename))[0], ts, te))
        if output_filename:
            plt.savefig(output_filename)
            print("Created", output_filename)
        else:
            plt.show()
        plt.clf()
        plt.close()
        return ts, te

    def plot_oad(self, output_filename=None) -> (float, float):
        """Plot the outlet air detector result"""
        ts, te = self.get_air_start_end_time()
        if ts >= te:
            print("Skip OAD because it is empty", ts, te)
            return ts, te
        df = self.get_df()
        if len(df) == 0:
            return 0, 0
        cdf = pd.DataFrame(df[df['Time(s)'].between(ts - 0.1, te + 0.1)])

        if 'patient_line_air_volume_ul' not in cdf.columns or 'patient_line_aircounts' not in cdf.columns:
            print("No patient line air volume log")
            return 0, 0
        cdf['air_vol(ml)'] = cdf['patient_line_air_volume_ul'] / 1000
        cdf['air_count'] = cdf['patient_line_aircounts']


        ax = cdf.plot("Time(s)", "air_vol(ml)", c='orange')
        ax.grid()
        ax.set_ylabel("Air volume(ml)")
        ax.yaxis.label.set_color('orange')
        ax.legend(loc='upper left')

        ax2 = ax.twinx()
        cdf.plot("Time(s)", "air_count", ax=ax2, style='--', c='green')
        cdf['delta_air_count'] = cdf.air_count.diff()
        cdf.plot.scatter("Time(s)", "delta_air_count", c='green', ax=ax2)
        ax2.set_ylabel("Air Count")

        ax2.set_ylabel("Air Count")
        ax2.legend(loc='lower right')
        ax2.yaxis.label.set_color('green')
        ax.set_title("%s (%.3fs - %.3fs)" % (os.path.splitext(os.path.basename(output_filename))[0], ts, te))
        if output_filename:
            plt.savefig(output_filename)
            print("Created", output_filename)
        else:
            plt.show()
        plt.clf()
        plt.close()
        return ts, te

    def _plot_motor_speed(self, width, height, style='step', line_width=2):
        """
        Deriving motor speed from positional information
        :param width:
        :param height:
        :param style:
        :param line_width:
        :return:
        """
        s1 = figure(width=width, height=height,
                    title="Derived motor Speeds(from motor position and inject time)",
                    y_axis_label="Motor Speed(mL/s)")
        s1.ygrid.band_fill_color = "olive"
        s1.ygrid.band_fill_alpha = 0.1
        s1.xgrid.bounds = (50, 100)  # define vertical bonds

        x = self.get_phase_time()
        if len(x) <= 2:
            return s1

        x = np.array(x)
        dt = x[1:] - x[0:-1]  # delta time step between 2 sample
        time = x[1:]
        valid_indices = dt > 0  # only valid if the time step is > 0
        nz_dt = dt[valid_indices]
        nz_time = time[valid_indices]
        if len(nz_time) < 1:
            return s1

        phase_column = self.data[:, 0]
        phase_column = phase_column[1:]
        phase_column = phase_column[valid_indices]  # remove the corresponding non-zero dt entries
        if self.verbose:
            print("rows", phase_column.shape)

        phase_ids = np.sort(np.unique(phase_column))
        phase_counts = [np.sum(phase_column == a) for a in phase_ids]
        ys = [14, 15, 16]  # motor count
        names = ["Saline Derived Speed", "Contrast 1 Derived Speed", "Contrast 2 Derived Speed"]
        for i, motor_name, color in zip(ys, names, MyColors):
            y = self.data[:, i]
            # noinspection PyUnresolvedReferences
            dy = y[1:] - y[:-1]  # delta step for motor count
            nz_dy = dy[valid_indices]

            # nz_dy is in motor count
            # nz_dt is in seconds
            # PULSES_PER_10ML 83577
            # 1ml = 8357.7
            speed = nz_dy / (nz_dt * (PULSES_PER_10ML / 10.0))  # @todo the unit is not quite right

            # Attempt to remove the bad motor position at the end of the phase
            # due to MCU go back in time and report the last phase volume in the inject digest.
            start = 0

            for phase, count in enumerate(phase_counts):
                end = start + count - 1
                if speed[end] > speed[end - 1]:
                    speed[end] = speed[end - 1]  # assume the first speed the same as the 2nd speed
                    if end + 2 < len(speed):
                        # as the data point has been contributed to the speed at both side of the t=end,
                        # let linearly interpolate the 2nd point since we are expecting the motor to change speed.
                        speed[end + 1] = (speed[end - 1] + speed[end + 2]) / 2
                start += count  # advance the start index for the next phase

            if len(speed) < 3:
                continue

            if speed[-2] < speed[-1]:
                # if the last data point speed increase - it should be the same as 2nd last
                # for the same reason as above
                speed[-1] = speed[-2]

            if style == 'line':
                s1.line(nz_time, speed, line_width=line_width, color=color, legend_label=motor_name)
            elif style == 'step':
                s1.step(nz_time, speed, line_width=line_width, color=color, legend_label=motor_name)
            else:
                s1.oval(nz_time, speed, line_width=line_width, color=color, legend_label=motor_name)
        return s1

    @staticmethod
    def _create_sdet_figure(sdet_inject_data_df: pd.DataFrame, width, height, title: str="SDET", line_width=2, y_axis_label="SUDS ADC(count)"):
        s1 = figure(width=width, height=height, title=title, y_axis_label=y_axis_label, sizing_mode="stretch_width")
        # add bands to the y-grid
        s1.ygrid.band_fill_color = "olive"
        s1.ygrid.band_fill_alpha = 0.1
        s1.xgrid.bounds = (50, 100)  # define vertical bonds
        x = sdet_inject_data_df["T(s)"]
        for i, field in enumerate(["Inlet_SUDS", "IR_K"]):
            y = sdet_inject_data_df[field]
            s1.line(x, y, line_width=line_width, color=MyColors[i], legend_label=field)
            s1.scatter(x, y, fill_color="white", size=8, marker="+", color='orange')

        yellow_box = BoxAnnotation(fill_color='yellow', fill_alpha=0.2, left=None, right=None, top=100, bottom=110)
        s1.add_layout(yellow_box)

        # Add the second y-axis to plot the digital signal
        s1.extra_y_ranges = {"y2": Range1d(start=0, end=1)}
        axis = LinearAxis(y_range_name="y2", axis_label='Digital')
        axis.ticker = SingleIntervalTicker(interval=1, num_minor_ticks=1)
        s1.add_layout(axis, 'right')
        digital = sdet_inject_data_df["digital"]
        mode = "after"
        s1.step(x, digital, line_width=line_width, color='brown', legend_label="Digital", y_range_name="y2", mode=mode)
        return s1

    def _create_figure(self, width, height, title, x, ys, style='step', line_width=2, y_axis_label=None):
        s1 = figure(width=width, height=height, title=title, y_axis_label=y_axis_label,
                    sizing_mode="stretch_width"
                    # ,output_backend="webgl"
                    )

        # add bands to the y-grid
        s1.ygrid.band_fill_color = "olive"
        s1.ygrid.band_fill_alpha = 0.1
        s1.xgrid.bounds = (50, 100)  # define vertical bonds

        colors = MyColors[:len(ys)]
        for i, color in zip(ys, colors):
            y = self.data[:, i]
            if style == 'line':
                s1.line(x, y, line_width=line_width, color=color, legend_label=self.headers[i])
            elif style == 'step':
                s1.step(x, y, line_width=line_width, color=color, legend_label=self.headers[i])
            else:
                s1.oval(x, y, line_width=line_width, color=color, legend_label=self.headers[i])
        return s1

    def get_phase_volumes(self, phase: int) -> list:
        """
        return a list of 3 volumes s0, c1, c2
        """
        # the saline,c1, c2 volumes, phase time are the last columns
        # cols = self.data[self.data[:, 0] == phase, -4:-1]   # does not work, but worked in the past [:, -5:-2] work
        phase_data = self.data[self.data[:,0] == phase]
        cols = phase_data[:, -5:-2]
        return cols[-1, :]  # and the last row

    # noinspection PyAugmentAssignment
    def get_phase_time(self):
        """
        :return: array of absolute time steps in second unit
        """
        if self._phase_time is None:
            # noinspection PyTypeChecker
            x: np.ndarray = self.data[:, -2]  # phase time, last column is time timestamp
            x = x / 1000.0  # convert milliseconds to seconds
            phase_ids = np.sort(np.unique(self.data[:, 0]))
            t = 0
            ret = []
            phase_ends = []
            for p in phase_ids:
                phase_time = x[self.data[:, 0] == p]
                max_val = phase_time[-1]  # the last value is the max of this phase
                if phase_time[0] < 0 or len(phase_time) > 3 and phase_time[1] < 0:
                    # this is a pause phase, only the last entry is correct so assume we are linearly sample the
                    # entire phase
                    phase_time = np.linspace(0.05, max_val, num=len(phase_time))
                phase_time = phase_time + t
                ret = ret + list(phase_time)
                t += max_val
                phase_ends.append(max_val)
            self._phase_time = ret
            self._phase_durations = phase_ends
        return self._phase_time

    def get_air_start_end_time(self) -> (float, float):
        """Get the first time that air volume change and the last time that air volume change, return (-1, -1) if there is no air"""
        df = self.get_df()
        cdf = df[df['patient_line_aircounts'] == 0]
        if len(cdf):
            min_time = cdf['Time(s)'].max()
        else:
            min_time = 0  # start with air already

        cdf = df[df['patient_line_aircounts'] == df['patient_line_aircounts'].max()]
        max_time = cdf['Time(s)'].min()
        if max_time < min_time:
            max_time = min_time = -1
        return min_time, max_time

    def is_phase_bleeding(self, protocol: Protocol, phase_end_data_indices):
        """Detect bleeding"""

        phase_data = protocol.get_phases()
        df = self.get_df()
        bleeding_count = 0
        bleeding_data = []
        for phase_index, data_index in enumerate(phase_end_data_indices):
            if phase_index == len(phase_end_data_indices) - 1:
                continue    # don't check the last phase
            # each phase has (type, mix, vol, flow, delay)
            phase_type = phase_data[phase_index][0]
            programmed_flow = phase_data[phase_index][3]
            s0_flow = df.iloc[data_index]['saline_flowrate_phase']
            c1_flow = df.iloc[data_index]['contrast1_flow_rate_phase']
            c2_flow = df.iloc[data_index]['contrast2_flow_rate_phase']
            if phase_type == 'SALINE':
                if c1_flow <= 0 and c2_flow <= 0:
                    continue
            elif phase_type == 'CONTRAST1':
                if s0_flow <= 0 and c2_flow <= 0:
                    continue
            elif phase_type == 'CONTRAST2':
                if s0_flow <= 0 and c1_flow <= 0:
                    continue
            elif phase_type == 'DUAL1':
                combined_flow = c1_flow + s0_flow
                if combined_flow != programmed_flow:
                    # might be bleeding, what about adaptive flow
                    print("DUAL 1 combined flow", combined_flow, "programmed:", programmed_flow)
                elif c1_flow <= 0 or s0_flow <= 0:
                    print("DUAL 1 early stop", s0_flow, c1_flow, "->", combined_flow, "programmed:", programmed_flow)
                elif c2_flow <= 0:        # @todo more sophisticate detection
                    continue

            elif phase_type == 'DUAL2':
                combined_flow = c2_flow + s0_flow
                if combined_flow != programmed_flow:
                    # might be bleeding
                    print("DUAL 2 combined flow", combined_flow, "programmed:", programmed_flow)
                elif c2_flow <= 0 or s0_flow <= 0:
                    print("DUAL 1 early stop", s0_flow, c2_flow, "->", combined_flow, "programmed:", programmed_flow)
                elif c1_flow <= 0:  # @todo more sophisticate detection
                    continue
            else:
                print(phase_index, phase_data[phase_index], data_index)
                continue
            bleeding_str = "[%d] Programmed phase %s, Actual Flow(S0, C2, C2): %.2f %.02f %.02f Stopcock: %s %s %s" \
                           % (phase_index, str(phase_data[phase_index]), s0_flow, c1_flow, c2_flow,
                              self.stopcock_id_to_name(df.iloc[data_index]['saline_SC_position']),
                              self.stopcock_id_to_name(df.iloc[data_index]['contrast1_SC_position']),
                              self.stopcock_id_to_name(df.iloc[data_index]['contrast2_SC_position'])
                              )
            print("BLEEDING", bleeding_str)
            bleeding_data.append(bleeding_str)
            bleeding_count += 1

        return bleeding_data

    def get_pressure_error_per_phase(self, protocol: Protocol, show_plot=False):
        df = self.get_df()
        # 4 injection_pressure
        # 5 saline_pressure
        # 6 contrast1_pressure
        # 7 contrast2_pressure
        # 27 pin_120
        for phase in sorted(df['phase'].unique()):
            # 40 duration_phase_i
            indices = df['phase'] == phase
            indices = np.bitwise_and(indices, df['duration_phase_i'] > 750)  # 2 seconds before the phase start
            dff = pd.DataFrame(df[indices])
            max_time = dff["duration_phase_i"].max() - 500  # 500ms before the phase end
            dff = dff[dff["duration_phase_i"] < max_time]
            pressure_errors = dff["injection_pressure"] - dff["Pressure_adc"]

            phase_data = protocol.get_phases()[int(phase)]
            print("Pressure errors in psi (name, flow, min, max, avg, std)",
                  phase_data[0],    # name
                  phase_data[3],    # flow
                  np.min(pressure_errors),
                  np.max(pressure_errors),
                  np.average(pressure_errors),
                  np.std(pressure_errors))
            try:
                with open("pressure_error.csv", "a") as fh:
                    arr = [phase_data[0],  # name
                           phase_data[3],  # flow
                           np.min(pressure_errors),
                           np.max(pressure_errors),
                           np.average(pressure_errors),
                           np.std(pressure_errors)]
                    arr = [str(x) for x in arr]
                    fh.write(",".join(arr) + "\n")
            except:
                pass

            if show_plot:
                ax = dff.plot("duration_phase_i", ["injection_pressure", "pin_120"])
                ax.grid()
                plt.show()
                plt.clf()
                plt.close()

    # noinspection LongLine
    def plot(self, protocol: Protocol, **kargs) -> list:
        """
        Generate html plot from the inject data with the given protocols
        to be improved: use pandas only, skip numpy array manipulation
        """
        width = 1200
        height = 300

        if 'sdet_inject_data_df' in kargs:
            sdet_inject_data_df = kargs['sdet_inject_data_df']
        else:
            sdet_inject_data_df = pd.DataFrame()

        # print("phase time", self.get_phase_time())
        x = self.get_phase_time()
        # phase time is still not quite right - it is the timer from
        # x = list(range(len(self.data)))

        self.get_pressure_error_per_phase(protocol)

        all_figures = [
            # 27 air count
            # 26 = air vol in um.

            # @todo convert this to pandas style to avoid number indexing
            self._create_figure(width, height, "Flow rate", x, range(31, 34), y_axis_label="Flow rate(mL/s)"),
            self._plot_motor_speed(width, height, style='line'),
            self._create_figure(width, height // 2, "Adaptive Flows", x, [1, 2, 3], style='step'),
            self._create_figure(width, height, "Pressure", x, [5, 6, 7, 4, 27, 29], style='line',
                                y_axis_label="Pressure(psi)"),
            self._create_figure(width, height, "Motor PID", x, [8, 9, 10]),
            self._create_figure(width, height, "Motor Position", x, [14, 15, 16]),
            self._create_figure(width, height, "Stored Compliance", x, range(20, 23),
                                y_axis_label="Stored compliance (mL)"),
            self._create_figure(width, height, "Phase Compliance", x, range(23, 26),
                                y_axis_label="Phase compliance (mL)"),
            self._create_figure(width, height, "Volume Pushed", x, range(34, 37), y_axis_label="Volume Pushed(mL)"),
            self._create_figure(width, height, "Volume Delivered", x, range(37, 40),
                                y_axis_label="Volume Delivered(mL)"),
            self._create_figure(width, height // 2, "Stopcocks Position (0:'CLOSED', 1:'MOVING', 2:'FILL', 3:'INJECT', 4:'UNKNOWN')", x, [11, 12, 13], style='step'),
            self._create_figure(width, height // 2, "Slow Start Reduction", x, range(17, 20)),
            self._create_figure(width, height, "Air Volume(µl)", x, range(29, 30), style='line'),
            self._create_figure(width, height, "Patient Line Count", x, range(26, 27), style='line'),
            self._create_figure(width, height // 2, "Pin 120-122 ADC", x, range(27, 29)),
            self._create_figure(width, height // 2, "3mm Port", x, range(30, 31)),
        ]

        if len(sdet_inject_data_df):
            sdec_fig = self._create_sdet_figure(sdet_inject_data_df, width, height, "SUDS(SDET) data", line_width=2)
            x_range = all_figures[0].x_range
            all_figures = [sdec_fig] + all_figures
            for fig in all_figures:
                fig.x_range = x_range

        for s in all_figures:
            if not s.legend:
                continue
            s.legend.location = "top_left"
            s.legend.click_policy = "hide"
            s.legend.orientation = "horizontal"
            s.legend.location = "bottom_right"
            s.legend.background_fill_color = None
            s.legend.background_fill_alpha = 0.4

        # annotate phase
        phase_column = self.data[:, 0]
        phase_ids = np.sort(np.unique(phase_column))
        phase_counts = [np.sum(phase_column == a) for a in phase_ids]
        if self.verbose:
            print("phases", phase_ids, "counts", phase_counts)
        start = 0
        expected_durations = protocol.get_phase_durations_in_ms()
        phase_end_data_indices = np.cumsum(phase_counts) - 1

        if self.verbose:
            print("expected_durations", expected_durations)
            print("indices", phase_end_data_indices, [x[i] for i in phase_end_data_indices])

        for fig in all_figures:
            green_box = BoxAnnotation(left=0, right=0.75, fill_color='red', fill_alpha=0.05)
            fig.add_layout(green_box)

        for i, (end,  duration) in enumerate(zip(phase_end_data_indices, expected_durations)):
            duration /= 1000  # convert to seconds
            expect_end_time = x[start] + duration
            if self.verbose:
                print(start, end, "x[start]", x[start], x[end], expect_end_time, duration)
            for fig in all_figures:
                if i & 1:
                    green_box = BoxAnnotation(left=x[start], right=x[end], fill_color='green', fill_alpha=0.1)
                    fig.add_layout(green_box)

                maker = Span(location=expect_end_time,
                             dimension='height', line_color='red' if i & 1 else "green",
                             line_dash='dashed', line_width=1)
                fig.add_layout(maker)

                if len(expected_durations) > 1:
                    # show the end absolute end time
                    total_time = np.sum(expected_durations) / 1000
                    maker = Span(location=total_time,
                                 dimension='height', line_color='orange',
                                 line_dash='dashdot', line_width=1)
                    fig.add_layout(maker)

            start = end

        if 'show_table' in kargs and kargs['show_table']:
            # insert table of all the inject-digest
            source = ColumnDataSource(self.get_df())
            columns = [TableColumn(field=name, title=name) for name in self.headers]
            data_table = DataTable(source=source, columns=columns, width=width, height=len(x) * 16)
            all_figures.append(data_table)

        if 'start_volumes' in kargs:
            start_volumes = kargs['start_volumes']
        else:
            start_volumes = []

        if 'end_volumes' in kargs:
            end_volumes = kargs['end_volumes']
        else:
            end_volumes = []

        if 'filename_list' in kargs:
            filename_list = kargs['filename_list']
        else:
            filename_list = []

        expected_volumes = protocol.get_volumes()
        deliver_volumes_str = ", ".join(["%.1f" % (x - y) for x, y in zip(start_volumes, end_volumes)])

        # relative to the parent directory
        filename_list = [os.path.basename(x) for x in filename_list]
        a_list = ",".join(['<p/><a href="%s">%s</a>' % (x, x) for x in filename_list])
        if 'other_text_lines' in kargs:
            other_text_lines = kargs['other_text_lines']
        else:
            other_text_lines = []

        all_figures = [
            PreText(text=str(x), width=width) for x in other_text_lines
        ] + all_figures

        # phase duration in seconds
        phase_durations = protocol.get_phase_durations_in_ms()
        phase_durations_expected_str = ", ".join(["%0.2f" % (x / 1000, ) for x in phase_durations])
        phase_durations_actual_str = ", ".join(["%0.2f" % (x,) for x in self.get_phase_durations()])

        # volume error per phase
        for phase in phase_ids:
            phase = int(phase)
            actual_volumes = self.get_phase_volumes(phase)
            expected_volumes = protocol.get_phase_volumes(phase)
            vol_errors = [actual - expect for actual, expect in zip(actual_volumes, expected_volumes)]
            vol_errors = [float(round(x, 1)) for x in vol_errors]
            all_figures = [PreText(text='Phase %d volume error: %s - %s = %s' %
                                        (phase, str(actual_volumes), str(expected_volumes), str(vol_errors)))
                           ] + all_figures
        bleeding_data = self.is_phase_bleeding(protocol, phase_end_data_indices)
        print("Bleeding", len(bleeding_data) > 0)
        if len(bleeding_data):
            bleeding_stuff = [
                PreText(text='BLEEDING: %s' % bleeding_str, width=width) for bleeding_str in bleeding_data]
            all_figures = all_figures + bleeding_stuff

        air_vol_ul, air_vol_count = self.get_oad_air_vol()
        air_text = "AIR: %dµl count %d" % (air_vol_ul, air_vol_count)
        print(air_text)

        all_figures = [
                          Div(text='Inject Digest data %s ' % a_list),
                          PreText(text='Digest Start volumes: %s' % str(start_volumes), width=width),
                          PreText(text='Digest End volumes: %s' % str(end_volumes), width=width),
                          PreText(text='Digest Delivery volumes: [%s]' % deliver_volumes_str, width=width),
                          PreText(text='Expected volumes: %s' % expected_volumes, width=width),
                          PreText(text='Actual Phase duration: %s' % phase_durations_actual_str, width=width),
                          PreText(text='Expected phase duration: %s' % phase_durations_expected_str, width=width),
                          PreText(text='Max inject pressure(psi): %.1f' % self.get_df()["injection_pressure"].max(), width=width),
                          PreText(text='At: %s' % self.protocol_extra, width=width),
                          PreText(text=air_text, width=width),
                          PreText(text='Protocol: %s' % protocol, width=width),
                      ] + all_figures

        return all_figures

    # noinspection PyTypeChecker
    def get_oad_air_vol(self):
        air_vol_ul = self.data[-1, 29]
        air_vol_count = self.data[-1, 26]
        return air_vol_ul, air_vol_count


def show_result(**kwargs):
    inject_digest_csv_filename = kwargs['csv_filename']
    name = ".".join(inject_digest_csv_filename.split(".")[:-1])
    title = '%s' % inject_digest_csv_filename
    html_filename = name + ".html"
    print("Create", html_filename)
    output_file(html_filename, title=title)
    dir_name = os.path.dirname(inject_digest_csv_filename)

    dd = InjectDigestData()
    dd.load_file(inject_digest_csv_filename, verbose=False)
    protocol = dd.protocol


    is_showing = 'is_show' in kwargs and kwargs['is_show']
    if dd.get_df() is not None:  # if data frame is available
        all_figures = dd.plot(protocol=protocol, **kwargs)
        # put the results in a row
        if is_showing:
            show(column(children=all_figures))
        else:
            try:
                save(column(children=all_figures))
            except ValueError:
                print("Failed to save", html_filename)
                for fig in all_figures:
                    print("    type", type(fig))

        air_output_filename = os.path.join(dir_name, "all_air_summary.csv")
        first_time = not os.path.exists(air_output_filename)
        air_vol_ul, air_count = dd.get_oad_air_vol()
        air_start, air_end = dd.get_air_start_end_time()
        dir_base_name = os.path.basename(dir_name)
        dir_base_name = os.path.splitext(dir_base_name)[0]

        utc_time = dd.protocol_extra.strip()
        if len(utc_time) == 0:
            val = datetime.now()
            utc_time = val.strftime("%m%d-%H:%M:%S.%f")  # without year

        sydney_time = hcu_time_str_to_sydney_tz_str(utc_time)
        pitts_time = hcu_time_str_to_pittsburgh_tz_str(utc_time)

        row = utc_time, pitts_time, sydney_time, \
            air_vol_ul, air_count, air_start, air_end, dd.protocol, \
            os.path.basename(inject_digest_csv_filename), dir_base_name
        row = [str(x) for x in row]

        with open(air_output_filename, "a") as fh:
            csvwriter = csv.writer(fh, dialect='excel', lineterminator='\n')
            if first_time:  # writing the fields
                csvwriter.writerow("utc_time,Pittsburgh_time,Sydney_time,air(ul),air_count,Ts,Te,protocol,name,base_name".split(","))
            csvwriter.writerow(row)
        png_name = os.path.splitext(inject_digest_csv_filename)[0] + "-air.png"

        new_oad = 'new_oad' in kwargs and kwargs['new_oad']
        df = dd.get_df()
        if "patient_line_air_volume_ul" in df.columns: # new OAD data
            dd.plot_oad(png_name)
        else:
            dd.plot_oad_air_count(png_name)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--csv_filename', default="inject-digest.csv", help='The csv filename contain injection digest')
    parser.add_argument('--show', default=False, help='The csv filename contain injection digest')
    parser.add_argument('--new_oad', action='store_true', help='Data capture with new INJECTDIGEST (has air volume)')
    args = parser.parse_args()

    is_show = not args.show
    show_result(csv_filename=args.csv_filename, is_show=is_show, new_oad=args.new_oad)
