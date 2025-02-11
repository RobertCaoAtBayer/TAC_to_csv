import tkinter
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import os.path
import subprocess
from parse_mcu_log import main as parse_mcu_main
from FRA_analyse import analyse_compressed_tac_directory
# from tkinterdnd2 import DND_FILES, TkinterDnD
from FRA_adb_injection import generate_injection_plots_from_injection_csv


class TacConversionToolApp:
    base_title = "TAC Conversion Tool V1.2"

    def __init__(self):
        self.root = tkinter.Tk()
        root = self.root
        root.title(self.base_title)
        root.geometry('800x400')
        self.tac_file_path = tk.StringVar()
        self.adb_file_path = tk.StringVar()
        self.output_file_name = tk.StringVar(value="./output")
        self.checkbox_var = tk.BooleanVar()
        self.selected_dropdown = tk.IntVar(value=100)
        root.minsize(600, 300)
        root.maxsize(1024, 500)

        style = ttk.Style()

        # TAC File Selection
        tac_frame = tk.Frame(root)
        tac_frame.pack(fill='x', expand=True, pady=5)
        tac_entry = ttk.Entry(tac_frame, textvariable=self.tac_file_path)
        tac_entry.grid(row=0, column=0, sticky='ew', padx=5)
        tac_button = ttk.Button(tac_frame, text="Select TAC File", command=self.open_tac_file_dialog)
        tac_button.grid(row=0, column=1, padx=2)
        tac_frame.columnconfigure(0, weight=1)

        # noinspection PyUnresolvedReferences
        # tac_entry.drop_target_register(DND_FILES)
        # noinspection PyUnresolvedReferences
        # tac_entry.dnd_bind('<<Drop>>', self.on_drop_tac)

        # ADB File Selection
        adb_frame = tk.Frame(root)
        adb_frame.pack(fill='x', expand=True, pady=5)
        adb_entry = ttk.Entry(adb_frame, textvariable=self.adb_file_path)
        adb_entry.grid(row=0, column=0, sticky='ew', padx=5)
        adb_button = ttk.Button(adb_frame, text="Select ADB File", command=self.open_adb_file_dialog)
        adb_button.grid(row=0, column=1, padx=2)
        adb_frame.columnconfigure(0, weight=1)

        # noinspection PyUnresolvedReferences
        # adb_entry.drop_target_register(DND_FILES)
        # noinspection PyUnresolvedReferences
        # adb_entry.dnd_bind('<<Drop>>', self.on_drop_adb)

        # Output File Name
        output_frame = tk.Frame(root)
        output_frame.pack(fill='x', expand=True, pady=5)
        output_entry = ttk.Entry(output_frame, textvariable=self.output_file_name)
        output_entry.grid(row=0, column=0, sticky='ew', padx=5)
        output_frame.columnconfigure(0, weight=1)

        select_output_button = ttk.Button(output_frame, text="Select Output Folder", command=self.select_output_folder)
        select_output_button.grid(row=0, column=1, padx=5)

        # Checkbox to call plotting function in FRA_adb_injection.py
        checkbox_frame = tk.Frame(root)
        checkbox_frame.pack(pady=3)

        checkbox = ttk.Checkbutton(checkbox_frame, text="Generate Injection Plots", command=self.toggle_plot,
                                   variable=self.checkbox_var, onvalue=1, offvalue=0)
        checkbox.grid(row=0, column=0, sticky='w')

        # Dropdown showing options for number of plots
        options = [50, 100, 200, 500, 1000, 2000, 5000]
        # noinspection PyTypeChecker
        self.dropdown = ttk.OptionMenu(checkbox_frame, self.selected_dropdown, *options)
        self.dropdown.grid(row=0, column=1, padx=(5, 0))
        self.dropdown.grid_remove()

        # Convert Button
        button_frame = tk.Frame(root)
        button_frame.pack(fill='both', expand=True, pady=5, padx=200)
        style.configure("Yellow.TButton", background="red", font=('Helvetica', 16), padding=20)
        convert_button = ttk.Button(button_frame, text="Convert", style="Yellow.TButton", command=self.on_convert_tac)
        convert_button.grid(row=0, column=0, sticky='nsew')
        button_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ttk.Progressbar(root, mode='determinate')
        self.progress_bar.pack(fill='x', expand=True, pady=10)

    def open_tac_file_dialog(self):
        filename = filedialog.askopenfilename(filetypes=[("TAC files", "*.zip")])
        if filename:
            self.tac_file_path.set(filename)

    def open_adb_file_dialog(self):
        filename = filedialog.askopenfilename(filetypes=[("ADB files", "*.zip"), ("Backup files", "*.backup")])
        if filename:
            self.adb_file_path.set(filename)

    def select_output_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_file_name.get())
        if folder:
            output_folder_path = os.path.join(folder, "output")
            if not os.path.exists(output_folder_path):
                os.mkdir(output_folder_path)
                print(f"Created new folder: {output_folder_path}")
            else:
                print(f"Folder already exists: {output_folder_path}")
            self.output_file_name.set(output_folder_path)  # Update the output folder variable

    def toggle_plot(self):
        if self.checkbox_var.get():
            self.dropdown.grid()
        else:
            self.dropdown.grid_remove()

    def on_drop_tac(self, event):
        dropped_path = event.data.strip('{}')  # Clean the path
        if os.path.exists(dropped_path):
            self.tac_file_path.set(dropped_path)
        print("Dropped TAC event:", event, dropped_path)

    def on_drop_adb(self, event):
        dropped_path = event.data.strip('{}')  # Clean the path
        if os.path.exists(dropped_path):
            self.adb_file_path.set(dropped_path)
        print("Dropped adb event:", event, dropped_path)

    def on_convert_tac(self):
        tac_filename = self.tac_file_path.get()
        adb_filename = self.adb_file_path.get()
        output_dir = self.output_file_name.get()
        output_dir = os.path.abspath(output_dir)
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        command_list = ['python', 'FRA_adb_conversion.py', '--output_dir', output_dir]
        if os.path.exists(tac_filename):
            print("Converting TAC file:", tac_filename)

            self.progress_bar['value'] = 0
            self.progress_bar['maximum'] = 100

            # Perform TAC conversion
            analyse_compressed_tac_directory(tac_file=tac_filename, output_dir=output_dir, want_all_data=True)
            parse_mcu_main(tac_filename, output_dir=output_dir, new_oad=True)
            self.progress_bar['value'] = 50
            command_list.extend(['--tac', tac_filename])

        if adb_filename:
            print("Converting ADB file:", adb_filename)
            command_list.extend(['--adb', adb_filename])

        subprocess.run(command_list)

        if self.checkbox_var.get():
            plots_dir = os.path.join(output_dir, "injection_plots")
            os.makedirs(plots_dir, exist_ok=True)
            print(f"Injection plots will be saved to: {plots_dir}")

            selected_injections = self.selected_dropdown.get()
            output_dir = "./output"
            last_n_injections = selected_injections
            csv_file = os.path.join(output_dir, "injection.csv")  # Adjust this path as needed
            output_prefix = "PLOT_INJ"
            generate_injection_plots_from_injection_csv(csv_file, plots_dir, output_prefix, last_n_injections)

        self.progress_bar['value'] = 100
        print("Conversion completed.")

    def run(self):
        self.root.mainloop()


def main():
    tool = TacConversionToolApp()
    tool.run()


if __name__ == '__main__':
    main()