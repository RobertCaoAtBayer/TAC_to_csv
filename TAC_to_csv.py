import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import os.path
from parse_mcu_log import main as parse_mcu_main
from FRA_analyse import analyse_compressed_tac_directory


class TacConversionToolApp:
    base_title = "TAC conversion Tool V1.0"

    def __init__(self):
        # font = ("default", 16)
        self.root = root = tk.Tk()
        root.title(self.base_title)
        root.geometry('800x400')  # Set the window size to be square
        self.file_path = tk.StringVar()  # Create a StringVar to store the file path
        root.minsize(600, 300)  # Set minimum height to 300 pixels, minimum width to 100 pixels as an example
        root.maxsize(1024, 500)  # Set maximum height to 300 pixels, maximum width to 1920 pixels as an example

        style = ttk.Style()

        entry_frame = tk.Frame(root)
        entry_frame.pack(fill='x', expand=True, pady=5)
        entry = ttk.Entry(entry_frame,textvariable=self.file_path)
        entry.grid(row=0, column=0, sticky='ew', padx=5)  # Use grid and make it expand horizontally

        button = ttk.Button(entry_frame, text="...", command=self.open_file_dialog)
        button.grid(row=0, column=1, padx=2)
        entry_frame.columnconfigure(0, weight=1)  # Make the entry column expandable
        # --------------------------
        button_frame = tk.Frame(root)
        button_frame.pack(fill='both', expand=True, pady=5)
        # Create and style the button
        # Adjust the style to ensure the button is visually appealing
        style.configure("Yellow.TButton", background="red", font=('Helvetica', 16), padding=20)

        yellow_button = ttk.Button(button_frame, text="Convert", style="Yellow.TButton", command=self.on_convert_tac)
        # Configure the button_frame to expand in both directions and center its contents
        button_frame.columnconfigure(0, weight=1)  # Make the left column expandable
        button_frame.columnconfigure(2, weight=1)  # Make the right column expandable
        button_frame.rowconfigure(0, weight=1)  # Make the top row expandable
        button_frame.rowconfigure(2, weight=1)  # Make the bottom row expandable

        # Place the yellow button in the center
        yellow_button.grid(row=1, column=1, sticky='nsew')  # Center the button and allow it to expand

        # New frame for progress bar and label
        progress_frame = tk.Frame(root)
        progress_frame.pack(fill='x', expand=True, pady=5)

    def open_file_dialog(self):
        filename = filedialog.askopenfilename(filetypes=[("TAC files", "*.zip")])
        print(f"Selected file: {filename}")
        self.root.title(self.base_title + " - Selected file: " + os.path.basename(filename))
        self.file_path.set(filename)  # Update the file_path StringVar with the selected file path

    def on_convert_tac(self):
        filename = self.file_path.get()
        if os.path.exists(filename):
            print("Converting", filename)
            output_dir = os.path.splitext(filename)[0]
            if not os.path.exists(output_dir):
                os.mkdir(output_dir)

            analyse_compressed_tac_directory(tac_file=filename, output_dir=output_dir, want_all_data=True)
            parse_mcu_main(filename,output_dir=output_dir, new_oad=True)


    def run(self):
        self.root.mainloop()

def main():
    tool = TacConversionToolApp()
    tool.run()


if __name__ == '__main__':
    main()

