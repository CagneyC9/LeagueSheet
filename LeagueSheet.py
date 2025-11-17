
import os
import csv
import tkinter as tk
from tkinter import ttk


def main():
	root = tk.Tk()
	root.title('LeagueSheet - 5 Inputs Demo')

	# Set window size as percentage of the screen (60% width x 60% height)
	sw = root.winfo_screenwidth()
	sh = root.winfo_screenheight()
	w = int(sw * 0.60)
	h = int(sh * 0.60)
	# Center the window on the screen
	x = (sw - w) // 2
	y = (sh - h) // 2
	root.geometry(f"{w}x{h}+{x}+{y}")

	# Read CSV headers (first row) from local CSV if present
	def default_csv_path():
		base = os.path.dirname(os.path.abspath(__file__))
		return os.path.join(base, 'LeagueChampSheet - Sheet1.csv')

	def read_headers(path):
		try:
			with open(path, newline='', encoding='utf-8') as f:
				reader = csv.reader(f)
				return next(reader)
		except Exception:
			return []

	headers = read_headers(default_csv_path())

	# Load CSV rows into a dict for lookup by champion_id (lowercased)
	def load_csv_rows(path):
		rows = {}
		try:
			with open(path, newline='', encoding='utf-8') as f:
				reader = csv.DictReader(f)
				for r in reader:
					key = r.get('champion_id', '').strip().lower()
					rows[key] = r
		except Exception:
			pass
		return rows

	csv_rows = load_csv_rows(default_csv_path())

	# Prepare a list of champion display names for autocomplete
	champion_list = sorted({v.get('champion_id', '').strip() for v in csv_rows.values() if v.get('champion_id')}, key=lambda s: s.lower())

	# Shared autocomplete Listbox (one visible at a time)
	autocomplete_box = tk.Listbox(root, height=6)
	autocomplete_box.configure(exportselection=False)

	# active entry holder so listbox callbacks know which Entry to fill
	active = {'entry': None}

	def show_autocomplete(entry, items):
		if not items:
			autocomplete_box.place_forget()
			return
		autocomplete_box.delete(0, tk.END)
		for it in items:
			autocomplete_box.insert(tk.END, it)
		# position the listbox directly under the entry
		x = entry.winfo_rootx() - root.winfo_rootx()
		y = entry.winfo_rooty() - root.winfo_rooty() + entry.winfo_height()
		w = entry.winfo_width()
		autocomplete_box.place(x=x, y=y, width=w)
		autocomplete_box.lift()

	def pick_current(event=None):
		sel = autocomplete_box.curselection()
		if not sel:
			return
		val = autocomplete_box.get(sel[0])
		ent = active.get('entry')
		if ent:
			ent.delete(0, tk.END)
			ent.insert(0, val)
		autocomplete_box.place_forget()

	autocomplete_box.bind('<ButtonRelease-1>', pick_current)
	autocomplete_box.bind('<Return>', pick_current)
	autocomplete_box.bind('<Escape>', lambda e: autocomplete_box.place_forget())

	def attach_autocomplete(entry):
		def on_keyrelease(event):
			key = event.keysym
			# if user navigates down, focus listbox
			if key in ('Down', 'Up') and autocomplete_box.winfo_ismapped():
				autocomplete_box.focus_set()
				if autocomplete_box.size() > 0:
					autocomplete_box.selection_clear(0, tk.END)
					autocomplete_box.selection_set(0)
					autocomplete_box.activate(0)
				return
			if key in ('Return', 'Escape'):
				if key == 'Escape':
					autocomplete_box.place_forget()
				return
			text = entry.get().strip().lower()
			if not text:
				matches = champion_list[:50]
			else:
				matches = [c for c in champion_list if c.lower().startswith(text)]
			if matches:
				active['entry'] = entry
				show_autocomplete(entry, matches[:20])
			else:
				autocomplete_box.place_forget()

		entry.bind('<KeyRelease>', on_keyrelease)
		# small delay to allow clicks into the listbox to register
		entry.bind('<FocusOut>', lambda e: root.after(150, lambda: autocomplete_box.place_forget()))

	def find_champion(name):
		if not name:
			return None
		key = name.strip().lower()
		if key in csv_rows:
			return csv_rows[key]
		# fallback: startswith
		for k, v in csv_rows.items():
			if k.startswith(key):
				return v
		return None

	def format_row_for_display(row):
		# return a readable string of the row excluding champion_id
		if not row:
			return ''
		fields = []
		for h in headers or []:
			if h == 'champion_id':
				continue
			fields.append(str(row.get(h, '-')))
		return ' | '.join(fields)

	frame = ttk.Frame(root, padding=12)
	frame.pack(fill='both', expand=True)

	# Place header labels above the returned-values columns (one label per CSV column)
	if headers and len(headers) > 1:
		returned_fields = [h for h in headers if h != 'champion_id']
	else:
		# fallback headers if CSV not found or malformed
		returned_fields = ['Passive_CD', 'Q_CD', 'W_CD', 'E_CD', 'R_CD']

	ttk.Label(frame, text='Returned:').grid(row=0, column=2, sticky='w', padx=(0, 6), pady=(0, 6))
	for i, fld in enumerate(returned_fields):
		tk.Label(frame, text=fld).grid(row=0, column=3 + i, sticky='w', padx=(0, 6), pady=(0, 6))

	# Rows controller: allow selecting 1-5 visible rows
	rows = []
	max_rows = 5
	base_row = 1  # header is at row 0

	# Rows selector combobox
	controls_frame = ttk.Frame(frame)
	controls_frame.grid(row=0, column=0, columnspan=5, sticky='w', pady=(0, 6))
	ttk.Label(controls_frame, text='Rows:').pack(side='left')
	row_count_var = tk.IntVar(value=max_rows)
	row_options = [str(i) for i in range(1, max_rows + 1)]
	rows_combo = ttk.Combobox(controls_frame, values=row_options, width=3, state='readonly')
	rows_combo.set(str(max_rows))
	rows_combo.pack(side='left', padx=(6, 12))

	def make_row(index):
		# index is 0-based logical row index; grid row will be base_row + index
		grid_row = base_row + index
		lbl_in = ttk.Label(frame, text=f'Input {index+1}:')
		lbl_in.grid(row=grid_row, column=0, sticky='w', padx=(0, 6), pady=6)
		e = ttk.Entry(frame, width=36)
		e.grid(row=grid_row, column=1, padx=(0, 6), pady=6)

		# attach autocomplete behavior to this entry
		attach_autocomplete(e)

		rv = tk.StringVar(value='')

		lbl_out = ttk.Label(frame, text='Returned:')
		lbl_out.grid(row=grid_row, column=2, sticky='w')

		# create one label per returned field so headers align with values
		val_labels = []
		rvs = []
		for i in range(len(returned_fields)):
			v = tk.StringVar(value='')
			lbl = ttk.Label(frame, textvariable=v, width=18)
			lbl.grid(row=grid_row, column=3 + i, sticky='w')
			val_labels.append(lbl)
			rvs.append(v)

		rows.append({'label': lbl_in, 'entry': e, 'out_label': lbl_out, 'val_labels': val_labels, 'rvs': rvs})

	# create all rows (they will be shown/hidden by update_rows)
	for i in range(max_rows):
		make_row(i)

	def update_rows(event=None):
		try:
			n = int(rows_combo.get())
		except Exception:
			n = max_rows
		for idx, r in enumerate(rows):
			if idx < n:
				# show
				r['label'].grid()
				r['entry'].grid()
				r['out_label'].grid()
				for lbl in r['val_labels']:
					lbl.grid()
			else:
				# hide
				r['label'].grid_remove()
				r['entry'].grid_remove()
				r['out_label'].grid_remove()
				for lbl in r['val_labels']:
					lbl.grid_remove()

	rows_combo.bind('<<ComboboxSelected>>', update_rows)

	def return_all(event=None):
		try:
			n = int(rows_combo.get())
		except Exception:
			n = max_rows
		for idx in range(n):
			val = rows[idx]['entry'].get().strip()
			row = find_champion(val)
			if row:
				# set each returned field into its own label
				for i, fld in enumerate(returned_fields):
					v = row.get(fld, '-')
					rows[idx]['rvs'][i].set(v)
			else:
				for v in rows[idx]['rvs']:
					v.set('Champion not found')


	# Global buttons
	btn_all = ttk.Button(frame, text='Return All', command=return_all)
	btn_all.grid(row=base_row + max_rows + 1, column=4, sticky='e', pady=(12, 0))

	def clear_all():
		try:
			n = int(rows_combo.get())
		except Exception:
			n = max_rows
		for idx in range(n):
			rows[idx]['entry'].delete(0, tk.END)
			for v in rows[idx]['rvs']:
				v.set('')

	btn_clear = ttk.Button(frame, text='Clear All', command=clear_all)
	btn_clear.grid(row=base_row + max_rows + 1, column=3, sticky='e', pady=(12, 0))

	# Ensure initial visibility matches combobox
	update_rows()

	# Bind Enter to trigger the global return_all action
	root.bind('<Return>', return_all)

	root.mainloop()


if __name__ == '__main__':
	main()