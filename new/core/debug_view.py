import tkinter as tk
import json

def show_results_window(results):
    root = tk.Tk()
    root.title("Resultados dos Cardápios")
    text = tk.Text(root, wrap=tk.WORD, width=100, height=40)
    text.pack(fill=tk.BOTH, expand=True)
    for ru, data in results.items():
        text.insert(tk.END, f"RU: {ru}\n")
        text.insert(tk.END, json.dumps(data, ensure_ascii=False, indent=2))
        text.insert(tk.END, "\n\n")
    text.config(state=tk.DISABLED)
    root.mainloop()
