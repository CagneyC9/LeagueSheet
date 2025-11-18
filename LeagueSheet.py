
import os
import sys
import shutil
import tkinter as tk
from tkinter import ttk
import requests
import concurrent.futures
from functools import lru_cache


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

	# We use Data Dragon as the authoritative source for champions/cooldowns.
	# No CSV dependency is required.

	# Prepare a list of champion display names for autocomplete.
	# Use a per-user writable data directory so packaged exes can update the cache.

	def get_user_data_dir():
		if os.name == 'nt':
			base = os.getenv('LOCALAPPDATA') or os.path.expanduser('~\\AppData\\Local')
		else:
			base = os.getenv('XDG_DATA_HOME') or os.path.expanduser('~/.local/share')
		path = os.path.join(base, 'LeagueSheet')
		try:
			os.makedirs(path, exist_ok=True)
		except Exception:
			pass
		return path

	def resource_path(rel_path):
		# When packaged by PyInstaller, resources are in sys._MEIPASS
		if getattr(sys, 'frozen', False):
			base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
		else:
			base = os.path.dirname(os.path.abspath(__file__))
		return os.path.join(base, rel_path)

	data_dir = get_user_data_dir()
	local_list_path = os.path.join(data_dir, 'champions.txt')

	# If the per-user champions cache is missing, try copying a bundled bootstrap.
	# Look in the bundle root for either `champions.txt` (repo root) or `data/champions.txt`.
	bundled_champs = resource_path('champions.txt')
	if not os.path.exists(bundled_champs):
		bundled_champs = resource_path(os.path.join('data', 'champions.txt'))
	if not os.path.exists(local_list_path) and os.path.exists(bundled_champs):
		try:
			shutil.copyfile(bundled_champs, local_list_path)
		except Exception:
			pass

	champion_list = []
	if os.path.exists(local_list_path):
		try:
			with open(local_list_path, encoding='utf-8') as f:
				champion_list = [line.strip() for line in f if line.strip()]
		except Exception:
			champion_list = []

	if not champion_list:
		# fallback: try to read from DDragon now
		try:
			mapping, dd_version, display_names = load_champion_key_map()
			champion_list = display_names
		except Exception:
			champion_list = []

	# status for champion updater (shows local/online update state)
	status_var = tk.StringVar(value='Champion list: local (cached)')

	# Thread pool for background fetches (create before any submit)
	executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

	# Start a background task to refresh the local champions file from DDragon
	def background_update_champion_file():
		try:
			# indicate update start in the UI
			root.after(0, lambda: status_var.set('Updating champion list...'))
			mapping, version, display_names = load_champion_key_map()
			# write to local file
			dirpath = os.path.dirname(local_list_path)
			os.makedirs(dirpath, exist_ok=True)
			with open(local_list_path, 'w', encoding='utf-8') as f:
				for name in display_names:
					f.write(name + '\n')
			# update in-memory list on the main thread
			def apply_update():
				champion_list[:] = display_names
				# mark success with version
				status_var.set(f'Champion list: updated ({version})')
			root.after(0, apply_update)
		except Exception:
			# show failure briefly
			try:
				root.after(0, lambda: status_var.set('Champion list: update failed'))
			except Exception:
				pass

	# submit the updater but don't block startup
	executor.submit(background_update_champion_file)

	# --- Data Dragon integration ---
	# Cache and helper functions to fetch champion cooldowns from ddragon
	DDRAGON_VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
	DD_BASE = "https://ddragon.leagueoflegends.com/cdn"

	def get_latest_dd_version(timeout=5):
		r = requests.get(DDRAGON_VERSIONS_URL, timeout=timeout)
		r.raise_for_status()
		return r.json()[0]

	@lru_cache(maxsize=1)
	def load_champion_key_map(version=None, timeout=5):
		if not version:
			version = get_latest_dd_version(timeout=timeout)
		url = f"{DD_BASE}/{version}/data/en_US/champion.json"
		r = requests.get(url, timeout=timeout)
		r.raise_for_status()
		data = r.json().get("data", {})
		mapping = {}
		display_names = set()
		for key, info in data.items():
			name = info.get('id', key)
			display_names.add(name)
			mapping[name.lower()] = key
			mapping[key.lower()] = key
			mapping[name.replace(' ', '').lower()] = key
		# return mapping, version, and a sorted list of display names
		return mapping, version, sorted(display_names, key=lambda s: s.lower())

	@lru_cache(maxsize=256)
	def fetch_champion_data(key, version, timeout=5):
		url = f"{DD_BASE}/{version}/data/en_US/champion/{key}.json"
		r = requests.get(url, timeout=timeout)
		r.raise_for_status()
		return r.json()["data"][key]

	def get_champion_cooldowns_dd(champ_input_name, timeout=5):
		name = (champ_input_name or '').strip()
		if not name:
			return None
		mapping, version, _ = load_champion_key_map()
		lookup_keys = [name.lower(), name.replace(' ', '').lower()]
		for k in lookup_keys:
			if k in mapping:
				champ_key = mapping[k]
				data = fetch_champion_data(champ_key, version, timeout=timeout)
				spells = data.get('spells', [])
				slots = ["Q", "W", "E", "R"]
				return {slot: spells[i].get('cooldownBurn', '-') for i, slot in enumerate(slots)}
		# fallback startswith
		for kname, key in mapping.items():
			if kname.startswith(name.lower()):
				data = fetch_champion_data(key, version, timeout=timeout)
				spells = data.get('spells', [])
				slots = ["Q", "W", "E", "R"]
				return {slot: spells[i].get('cooldownBurn', '-') for i, slot in enumerate(slots)}
		return None

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

	# No CSV lookups: DDragon is the authoritative source for champion data.

	frame = ttk.Frame(root, padding=12)
	frame.pack(fill='both', expand=True)

	# Returned fields (we use DDragon cooldowns: Q/W/E/R)
	returned_fields = ['Q', 'W', 'E', 'R']

	# Header labels for the spell columns (Q/W/E/R)
	# Place headers on row 1 so the controls_frame (row 0) does not overlap them
	for i, fld in enumerate(returned_fields):
		tk.Label(frame, text=fld).grid(row=1, column=2 + i, sticky='w', padx=(0, 6), pady=(0, 6))

	# Rows controller: allow selecting 1-5 visible rows
	rows = []
	max_rows = 5
	base_row = 2  # header is at row 1

	# Controls row: Champions label + number-of-inputs selector
	controls_frame = ttk.Frame(frame)
	controls_frame.grid(row=0, column=0, columnspan=5, sticky='w', pady=(0, 6))
	tk.Label(controls_frame, text='Champions:').pack(side='left')
	row_count_var = tk.IntVar(value=max_rows)
	row_options = [str(i) for i in range(1, max_rows + 1)]
	rows_combo = ttk.Combobox(controls_frame, values=row_options, width=3, state='readonly')
	rows_combo.set(str(max_rows))
	rows_combo.pack(side='left', padx=(6, 12))

	# Status label for champion updater
	tk.Label(controls_frame, textvariable=status_var).pack(side='left', padx=(8, 0))

	# View selector: choose whether spell columns show Cooldown or Description
	view_mode_var = tk.StringVar(value='Cooldown')
	view_options = ['Cooldown', 'Description']
	ttk.Label(controls_frame, text='View:').pack(side='left', padx=(8, 0))
	view_combo = ttk.Combobox(controls_frame, values=view_options, textvariable=view_mode_var, width=12, state='readonly')
	view_combo.pack(side='left', padx=(4, 12))

	# DDragon is the default source; no CSV toggle required.

	def make_row(index):
		# index is 0-based logical row index; grid row will be base_row + index
		grid_row = base_row + index
		# per-row 'Name:' label and champion entry
		lbl_name = ttk.Label(frame, text='Name:')
		lbl_name.grid(row=grid_row, column=0, sticky='w', padx=(0, 6), pady=6)
		e = ttk.Entry(frame, width=36)
		e.grid(row=grid_row, column=1, padx=(0, 6), pady=6)

		# attach autocomplete behavior to this entry
		attach_autocomplete(e)

		rv = tk.StringVar(value='')

		# create one label per returned field so headers align with values
		val_labels = []
		rvs = []
		for i in range(len(returned_fields)):
			v = tk.StringVar(value='')
			# allow wider labels to accommodate descriptions
			lbl = ttk.Label(frame, textvariable=v, width=40, anchor='w')
			lbl.grid(row=grid_row, column=2 + i, sticky='w')
			val_labels.append(lbl)
			rvs.append(v)

		rows.append({'label': lbl_name, 'entry': e, 'val_labels': val_labels, 'rvs': rvs})

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
				for lbl in r['val_labels']:
					lbl.grid()
			else:
				# hide
				r['label'].grid_remove()
				r['entry'].grid_remove()
				for lbl in r['val_labels']:
					lbl.grid_remove()
				# show/hide per-row label, entry, and value labels

	rows_combo.bind('<<ComboboxSelected>>', update_rows)

	def return_all(event=None):
		try:
			n = int(rows_combo.get())
		except Exception:
			n = max_rows
		# Always use Data Dragon in background threads
		def make_task(index, name):
			def task():
				mode = view_mode_var.get()
				try:
					if mode == 'Cooldown':
						result = get_champion_cooldowns_dd(name)
					else:
						# fetch the champion spells and return descriptions/tooltips
						result = None
						mapping, version, _ = load_champion_key_map()
						lookup_keys = [name.lower(), name.replace(' ', '').lower()]
						champ_key = None
						for k in lookup_keys:
							if k in mapping:
								champ_key = mapping[k]
								break
						if not champ_key:
							for kname, key in mapping.items():
								if kname.startswith(name.lower()):
									champ_key = key
									break
						if champ_key:
							data = fetch_champion_data(champ_key, version)
							spells = data.get('spells', [])
							result = {}
							slots = ['Q', 'W', 'E', 'R']
							for i, slot in enumerate(slots):
								try:
									spell = spells[i]
									val = spell.get('tooltip') or spell.get('description') or '-'
								except Exception:
									val = '-'
								result[slot] = val
				except Exception:
					result = None
				def apply_result():
					if result:
						for i, fld in enumerate(returned_fields):
							key = fld[0].upper()
							rows[index]['rvs'][i].set(result.get(key, '-'))
					else:
						for v in rows[index]['rvs']:
							v.set('Champion not found')
				root.after(0, apply_result)
			return task

		for idx in range(n):
			name = rows[idx]['entry'].get().strip()
			executor.submit(make_task(idx, name))


	# Global buttons
	btn_all = ttk.Button(frame, text='Lookup', command=return_all)
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

	btn_clear = ttk.Button(frame, text='Clear', command=clear_all)
	btn_clear.grid(row=base_row + max_rows + 1, column=3, sticky='e', pady=(12, 0))

	# Ensure initial visibility matches combobox
	update_rows()

	# Bind Enter to trigger the global return_all action
	root.bind('<Return>', return_all)

	root.mainloop()


if __name__ == '__main__':
	main()