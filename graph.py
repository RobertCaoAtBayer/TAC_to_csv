"""
This file contains the graphing functions
"""
import pandas as pd
import matplotlib.pyplot as plt
import os.path
import numpy as np
from matplotlib.ticker import PercentFormatter


def plot_time_span(ax, range_list: list):
    """
    ax: is the axis from matplotlib
    range_list: the list contains a list of tuple of 3 entries (ts, te, value)
    the odd value will be darker than the light value
    """
    for ts, te, val in range_list:
        if val & 1 == 1:
            ax.axvspan(ts, te, facecolor='xkcd:sky blue', alpha=0.2)
        else:
            pass


# noinspection DuplicatedCode
def plot_a_b_time_series(ax, df: pd.DataFrame, a_name, b_name,
                         a_y_axis_name=None,
                         b_y_axis_name=None,
                         highlight_list=None,
                         combine_legends=False):
    """
    Plot a and b on a primary and secondary axis
    :param ax:
    :param df:
    :param a_name: a column name or a list of column names
    :param b_name: a column name or a list of column names
    :param a_y_axis_name:
    :param b_y_axis_name:
    :param highlight_list:
    :param combine_legends:
    :return:
    """
    a_colors = ["blue", "lime", "aqua", "orange", "olive", "#bc13fe"]   # "#bc13fe" neon purple
    b_colors = ["brown", "cyan", "red", "purple", "indigo", "#fe019a"]  # "#fe019a" neon pink
    if a_y_axis_name is None:
        a_y_axis_name = a_name
    if b_y_axis_name is None:
        b_y_axis_name = b_name

    if isinstance(a_name, str):
        a_name = [a_name]

    if isinstance(b_name, str):
        b_name = [b_name]

    x_name = "T"
    if x_name not in df.columns:
        x_name = "Time(s)"
        if x_name not in df.columns:
            raise ValueError("No time column found. Expect either 'T' or 'Time(s)' column")
    df.plot(x=x_name, y=a_name, ax=ax, color=a_colors, label=a_name)

    ax.set_ylabel(a_y_axis_name, color=a_colors[0])
    ax.tick_params(axis='y', color=a_colors[0])

    ax.set_xlabel("Time(s)")
    h1, l1 = ax.get_legend_handles_labels()
    if len(b_name) > 0 and len(df) > 0:
        print("b_name", b_name)
        ax2 = ax.twinx()
        df.plot(x=x_name, y=b_name, ax=ax2, color=b_colors, label=b_name)

        ax2.tick_params(axis='y', color=b_colors[0])
        ax2.set_ylabel(b_y_axis_name, color=b_colors[0])

        h2, l2 = ax2.get_legend_handles_labels()
        if combine_legends:
            ax.get_legend().set_visible(False)
            ax2.get_legend().set_visible(False)
            if len(l1) > 0 and len(l2) > 0:
                l1 = [x + "(left)" for x in l1]
                l2 = [x + "(right)" for x in l2]
            ax.legend(h1 + h2, l1 + l2)
        else:
            ax.legend(loc=2)    # 2 = top left
            ax2.legend(loc=1)  # 1 = top right
            # ax2.legend(loc=1)   # 1 = top right
            # 5,7 = y-center-right
            # 6 = y-center-left

    ax.grid()

    if highlight_list is not None:
        plot_time_span(ax, highlight_list)


def plot_pareto_chart(df: pd.DataFrame, df_key: str, color1='blue', color2='green', png_name=None, remove_zeros=False, top_n_entries=None):
    if remove_zeros:
        df = df[df[df_key] != 0]
        out = df[df_key].value_counts()
    else:
        out = df[df_key].value_counts()
    if len(df) < 1:
        return  # empty

    keys = [str(x) for x in out.index.tolist()]
    df = pd.DataFrame({'count': out})
    df.index = keys
    plot_pareto_from_count_df(df, df_key, color1, color2, png_name, top_n_entries)


def plot_pareto_from_count_df(df, name, color1='blue', color2='green', png_name=None, top_n_entries=None):
    df = df.sort_values(by='count', ascending=False)
    total = df['count'].sum()    # sum of all counts before filtering

    keys = [str(x) for x in df.index.tolist()]
    df.index = keys
    print("df", df)
    df['cum_perc'] = df['count'].cumsum() / df['count'].sum() * 100
    org_df_len = len(df)
    if top_n_entries is not None:
        df = df[:top_n_entries]
    # create basic bar plot
    fig, ax = plt.subplots(figsize=(15, 8), tight_layout=True)
    # ax.bar(df.index, df['count'], color=color1)
    ax.bar(df.index, df['count'], color=color1)
    ax.set_ylabel("Counts", color=color1)
    ax.set_xlabel("Unique '%s' (sorted by number of occurrences)" % name)
    ax.tick_params(axis='x', labelrotation=90)
    ax.grid()
    # add cumulative percentage line to plot
    ax2 = ax.twinx()
    ax2.plot(df.index, df['cum_perc'], color=color2, marker="D")
    ax2.yaxis.set_major_formatter(PercentFormatter())
    ax2.set_ylabel("Cumulative percentage", color=color2)
    ax2.set_ylim([0, 100])
    # specify axis colors
    ax.tick_params(axis='y', colors=color1)
    ax2.tick_params(axis='y', colors=color2)
    print(df)
    title = "Pareto plot for '%s' (N=%s)" % (name, f'{total:,}')
    if org_df_len != len(df):
        title = title + "\n(remove %d entries)" % (org_df_len - len(df))
    ax.set_title(title)
    if png_name is not None:
        plt.savefig(png_name, dpi=150)
        print("Generated", png_name)
        csv_name = os.path.splitext(png_name)[0] + ".csv"
        df.to_csv(csv_name, index=True)  # index is the key. Need to save it
        print("Generated", csv_name)
    else:
        plt.show()
    plt.close()
    plt.clf()


def main():
    data = [(4, 4634),
            (1, 189875),
            (2, 307859),
            (3, 26162),
            (5, 1085),
            (6, 304),
            (9, 15),
            (93, 1),
            (7, 103),
            (8, 43),
            (10, 3)]
    df = pd.DataFrame(data, columns=['index', 'count'])
    df.set_index('index', inplace=True)
    plot_pareto_from_count_df(df, "Number of Injections in Exams")


if __name__ == '__main__':
    main()
