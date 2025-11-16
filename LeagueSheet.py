
import os
import csv
import tkinter as tk
from tkinter import ttk


def main():
	root = tk.Tk()
	root.title('LeagueSheet - 5 Inputs Demo')

	# Set window size as percentage of the screen (50% width x 70% height)
	sw = root.winfo_screenwidth()
	sh = root.winfo_screenheight()
	w = int(sw * 0.60)   # 50% of screen width
	h = int(sh * 0.60)   # 70% of screen height
 
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

	# Place header labels above the returned-values columns (columns 3-4)
	header_text = ', '.join(headers[1:]) if headers and len(headers) > 1 else 'CSV headers not found'
	ttk.Label(frame, text='CSV first row (returned columns):').grid(row=0, column=3, sticky='w', padx=(0, 6), pady=(0, 6))
	ttk.Label(frame, text=header_text).grid(row=0, column=4, sticky='w', padx=(0, 6), pady=(0, 6))

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

		rv = tk.StringVar(value='')


		def on_row_return(idx=index):
			val = rows[idx]['entry'].get().strip()
			row = find_champion(val)
			if row:
				disp = format_row_for_display(row)
			else:
				disp = 'Champion not found'
			rows[idx]['rv'].set(disp)

		btn = ttk.Button(frame, text='Return', command=on_row_return)
		btn.grid(row=grid_row, column=2, padx=(0, 12))

		lbl_out = ttk.Label(frame, text='Returned:')
		lbl_out.grid(row=grid_row, column=3, sticky='w')
		lbl_val = ttk.Label(frame, textvariable=rv, width=30)
		lbl_val.grid(row=grid_row, column=4, sticky='w')

		rows.append({'label': lbl_in, 'entry': e, 'button': btn, 'out_label': lbl_out, 'val_label': lbl_val, 'rv': rv})

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
				r['button'].grid()
				r['out_label'].grid()
				r['val_label'].grid()
			else:
				# hide
				r['label'].grid_remove()
				r['entry'].grid_remove()
				r['button'].grid_remove()
				r['out_label'].grid_remove()
				r['val_label'].grid_remove()

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
				disp = format_row_for_display(row)
			else:
				disp = 'Champion not found'
			rows[idx]['rv'].set(disp)


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
			rows[idx]['rv'].set('')

	btn_clear = ttk.Button(frame, text='Clear All', command=clear_all)
	btn_clear.grid(row=base_row + max_rows + 1, column=3, sticky='e', pady=(12, 0))

	# Ensure initial visibility matches combobox
	update_rows()

	# Bind Enter to trigger the global return_all action
	root.bind('<Return>', return_all)

	root.mainloop()


if __name__ == '__main__':
	main()