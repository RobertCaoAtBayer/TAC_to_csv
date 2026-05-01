import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys

# Ensure the parse_mcu_sdet.py is importable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from parse_mcu_sdet import parse_mcu_sdet

def browse_file(entry):
    filename = filedialog.askopenfilename(title="Select QML_DebugTool log file or directory")
    if filename:
        entry.delete(0, tk.END)
        entry.insert(0, filename)

def run_parse(entry, status_label):
    filepath = entry.get().strip()
    if not filepath:
        messagebox.showerror("Error", "Please select or enter a file path.")
        return
    output_dir = os.path.dirname(filepath)
    try:
        df = parse_mcu_sdet(filepath, output_dir)
        if len(df) == 0:
            status_label.config(text=f"No SDET logs found in {filepath}")
        else:
            status_label.config(text=f"Parsed SDET logs from {filepath}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to parse: {e}")
        status_label.config(text="Error during parsing.")

def main():
    root = tk.Tk()
    root.title("SDET Log Parser")
    root.geometry("600x150")

    tk.Label(root, text="QML_DebugTool log file or directory:").pack(pady=5)
    entry = tk.Entry(root, width=60)
    entry.pack(side=tk.LEFT, padx=10, pady=5, expand=True)
    browse_btn = tk.Button(root, text="Browse", command=lambda: browse_file(entry))
    browse_btn.pack(side=tk.LEFT, padx=5)

    frame = tk.Frame(root)
    frame.pack(fill=tk.X, pady=10)
    parse_btn = tk.Button(frame, text="Parse", command=lambda: run_parse(entry, status_label))
    parse_btn.pack(side=tk.LEFT, padx=10)
    status_label = tk.Label(frame, text="")
    status_label.pack(side=tk.LEFT, padx=10)

    root.mainloop()

if __name__ == "__main__":
    main()

