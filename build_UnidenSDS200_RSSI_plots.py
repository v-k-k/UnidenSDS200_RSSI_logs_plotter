"""
    Simple script to compare RSSI values for 2 Unidens SDS200
"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import configparser
import subprocess
import time
import csv
import os
from collections import namedtuple
from itertools import groupby
from datetime import datetime

CONFIG = configparser.ConfigParser()
CONFIG.read('plotting_src.ini')

HEADER_LINE = "Talk Group, Frequency, Tone, RSSI, UID, Mod, Hits, Duration, Start Date / Time, System / Site, " \
              "Department, Channel, System Type, Digital Status, Service Type, Number Tune"
CMD = 'type "{}"'
CORRESPONDING = {
    'host_1': ['host_path_1'],
    'host_2': ['host_path_2']
}


class HistoryLogParser:
    _p_holder = "{}\\History Log.txt"

    @staticmethod
    def retrieve_hist_log_content(command):
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout.splitlines()

    def __init__(self, host):
        self.host = host
        self._do_iteration = True

    def __enter__(self):
        command = CMD.format(self._p_holder.format(CONFIG['HOSTS'][self.host]))
        lines = HistoryLogParser.retrieve_hist_log_content(command)

        # Identify the start of the CSV data (look for the header line)
        header_line_index = None
        for i, line in enumerate(lines):
            if line.startswith(HEADER_LINE):
                header_line_index = i
                break

        if header_line_index is not None:
            # Parse the CSV data from the identified lines
            self._reader = csv.reader(lines[header_line_index:], delimiter=',')
            headers = map(lambda x: x.replace(' ', '').replace('/', ''),
                          next(self._reader))
            self._nt = namedtuple('CustomCsvRow', headers)
            return self
        else:
            raise Exception("SOMETHING WRONG WITH 'History Log.txt' CONTENT!\n Check the headers...")

    def __exit__(self, exc_type, exc_value, exc_tb):
        self._do_iteration = False
        return False

    def __iter__(self):
        return self

    def __next__(self):
        if not self._do_iteration:
            raise StopIteration
        else:
            return self._nt(*(val.strip() for val in next(self._reader)))

    def sort(self, k):
        res = list(self)
        res.sort(key=k)
        return res

    def group(self, k):
        return {k: list(g) for k, g in groupby(self.sort(k), key=k)}


def execute_cmd_and_parse_csv(command):
    lines = HistoryLogParser.retrieve_hist_log_content(command)

    # Identify the start of the CSV data (look for the header line)
    header_line_index = None
    csv_data = []
    for i, line in enumerate(lines):
        if line.startswith(HEADER_LINE):
            header_line_index = i
            break

    if header_line_index is not None:
        # Parse the CSV data from the identified lines
        reader = csv.DictReader(lines[header_line_index:], delimiter=',')
        csv_data = [{k.replace(' ', '').replace('/', ''): v.strip()
                     for k, v in row.items()} for row in reader]

    return csv_data


DIR = str(int(time.time()))
os.mkdir(DIR)

for h, c in {'host_1': 'blue', 'host_2': 'red'}.items():
    with HistoryLogParser(h) as data:
        grouped_data = data.group(lambda x: x.Frequency)

        target = '475.360000'  # '435.437500'  #

        sorted_data = grouped_data[target]
        x_values = [datetime.strptime(row.StartDateTime, '%m/%d/%y %H:%M:%S')
                    for row in sorted_data if row.Frequency == target]
        y_values = [int(row.RSSI) for row in sorted_data if row.Frequency == target]

        # Create the plot
        figure = plt.figure(figsize=(10, 6))
        plt.plot(x_values, y_values, marker='o', linestyle='-', color=c)

        # Format x-axis with date and time
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plt.gcf().autofmt_xdate()

        # Set labels and title
        plt.xlabel('Start Date/Time')
        plt.ylabel('RSSI')
        plt.title(target)

        # Show the plot
        plt.grid(True)
        # plt.show()
        figure.savefig(f"{DIR}{os.sep}{h}.png")
