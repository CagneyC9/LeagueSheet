
import os
import sys
import shutil
import tkinter as tk
from tkinter import ttk
import requests
import concurrent.futures
from functools import lru_cache
from PIL import Image, ImageTk
import io
import ctypes
from ctypes import wintypes
import threading




def main():
	def resource_path(relative_path):
		"""Get absolute path to resource, works for dev and PyInstaller."""
		try:
			base_path = sys._MEIPASS
		except Exception:
			base_path = os.path.abspath(".")
		return os.path.join(base_path, relative_path)
    	
	root = tk.Tk()
	root.title('LeagueSheet - 5 Inputs Demo')
 
	sw = root.winfo_screenwidth()
	sh = root.winfo_screenheight()
	size_by_rows = {1: 0.72, 2: 0.66, 3: 0.6, 4: 0.56, 5: 0.52}
	perc_w = 0.6
	min_w, min_h = 500, 420
	hk_input_var = tk.StringVar(value='Ctrl+Shift+L')
	hotkey_event_binding = None
	hotkey_status = tk.StringVar(value='Hotkey: Ctrl+Shift+L')
	global_hotkey_registered = False
	hotkey_thread = None
	hotkey_thread_stop = None
	hotkey_thread_id = None
	HOTKEY_ID = 1
	auto_geometry = True   # stop auto-sizing once the user manually resizes
	applying_geometry = False
	root.minsize(min_w, min_h)
 
	def set_hotkey_status(text):
		try:
			root.after(0, lambda t=text: hotkey_status.set(t))
		except Exception:
			pass
 
	def parse_hotkey(text):
		# Parse strings like "Ctrl+Shift+L" -> (tk_event, mod_mask, vk_code)
		parts = [p.strip() for p in (text or '').replace('-', '+').split('+') if p.strip()]
		if not parts:
			return None
		mod_map = {
			'ctrl': 0x0002,
			'control': 0x0002,
			'shift': 0x0004,
			'alt': 0x0001,
			'win': 0x0008,
			'windows': 0x0008,
		}
		mods = []
		mod_mask = 0
		key = None
		for p in parts:
			lp = p.lower()
			if lp in mod_map:
				if mod_map[lp] not in mods:
					mods.append(mod_map[lp])
					mod_mask |= mod_map[lp]
			else:
				key = p
		if not key:
			return None
		key_upper = key.upper()
		event_mods = []
		if 0x0002 in mods:
			event_mods.append('Control')
		if 0x0004 in mods:
			event_mods.append('Shift')
		if 0x0001 in mods:
			event_mods.append('Alt')
		if 0x0008 in mods:
			event_mods.append('Win')
		event_key = key_upper
		if len(event_key) == 1:
			vk_code = ord(event_key)
		elif key_upper.startswith('F') and key_upper[1:].isdigit():
			num = int(key_upper[1:])
			if 1 <= num <= 24:
				vk_code = 0x70 + (num - 1)
			else:
				return None
			event_key = f'F{num}'
		else:
			return None
		tk_event = f"<{'-'.join(event_mods + [event_key])}>"
		return tk_event, mod_mask, vk_code
 
	def toggle_window(event=None):
		# Toggle between minimized and restored, lifting to the front when shown.
		try:
			if root.state() in ('normal', 'zoomed'):
				root.iconify()
			else:
				root.deiconify()
				root.lift()
				root.focus_force()
				root.attributes('-topmost', True)
				root.after(50, lambda: root.attributes('-topmost', False))
		except Exception:
			pass
		return "break"
 
	def stop_hotkey_thread():
		nonlocal hotkey_thread, hotkey_thread_stop, hotkey_thread_id, global_hotkey_registered
		if hotkey_thread and hotkey_thread.is_alive():
			try:
				if hotkey_thread_id:
					ctypes.windll.user32.PostThreadMessageW(hotkey_thread_id, 0x0012, 0, 0)  # WM_QUIT
			except Exception:
				pass
			if hotkey_thread_stop:
				hotkey_thread_stop.set()
			hotkey_thread.join(timeout=1)
		hotkey_thread = None
		hotkey_thread_stop = None
		hotkey_thread_id = None
		global_hotkey_registered = False
		set_hotkey_status('Hotkey: unregistered')
 
	def register_global_hotkey(mod_mask, vk_code):
		# Windows-only global hotkey so toggle works even when minimized/unfocused.
		nonlocal global_hotkey_registered, hotkey_thread, hotkey_thread_stop, hotkey_thread_id
		if os.name != 'nt':
			return
		stop_hotkey_thread()
		hotkey_thread_stop = threading.Event()
 
		def message_loop():
			nonlocal global_hotkey_registered, hotkey_thread_id
			user32 = ctypes.windll.user32
			kernel32 = ctypes.windll.kernel32
			hotkey_thread_id = kernel32.GetCurrentThreadId()
			try:
				if not user32.RegisterHotKey(None, HOTKEY_ID, mod_mask, vk_code):
					set_hotkey_status('Hotkey: failed to register')
					global_hotkey_registered = False
					return
				global_hotkey_registered = True
				set_hotkey_status('Hotkey: registered')
				msg = wintypes.MSG()
				while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
					if hotkey_thread_stop.is_set():
						break
					if msg.message == 0x0312 and msg.wParam == HOTKEY_ID:
						try:
							root.after(0, toggle_window)
						except Exception:
							pass
					user32.TranslateMessage(ctypes.byref(msg))
					user32.DispatchMessageW(ctypes.byref(msg))
			finally:
				try:
					user32.UnregisterHotKey(None, HOTKEY_ID)
				except Exception:
					pass
				global_hotkey_registered = False
				set_hotkey_status('Hotkey: unregistered')
 
		hotkey_thread = threading.Thread(target=message_loop, daemon=True)
		hotkey_thread.start()
 
	def unregister_global_hotkey():
		stop_hotkey_thread()
 
	def apply_hotkey(text):
		nonlocal hotkey_event_binding
		parsed = parse_hotkey(text)
		if not parsed:
			set_hotkey_status('Hotkey: invalid')
			return
		tk_event, mod_mask, vk_code = parsed
		if hotkey_event_binding:
			try:
				root.unbind(hotkey_event_binding)
			except Exception:
				pass
		try:
			root.bind(tk_event, toggle_window)
			hotkey_event_binding = tk_event
		except Exception:
			set_hotkey_status('Hotkey: failed to bind')
			return
		unregister_global_hotkey()
		register_global_hotkey(mod_mask, vk_code)
		set_hotkey_status(f'Hotkey: {text}')
		hk_input_var.set(text)
 
	def on_close():
		unregister_global_hotkey()
		try:
			root.destroy()
		except Exception:
			pass
 

	root.protocol("WM_DELETE_WINDOW", on_close)
	apply_hotkey(hk_input_var.get())

	def set_geometry_for_rows(n_rows):
		nonlocal auto_geometry, applying_geometry
		if not auto_geometry:
			return
		perc_h = size_by_rows.get(n_rows, size_by_rows.get(max(size_by_rows), 0.6))
		w = max(min_w, int(sw * perc_w))
		h = max(min_h, int(sh * perc_h))
		x = (sw - w) // 2
		y = (sh - h) // 2
		applying_geometry = True
		root.geometry(f"{w}x{h}+{x}+{y}")
		applying_geometry = False

	def on_root_configure(event):
		# When the user manually resizes the window, stop auto geometry changes.
		nonlocal auto_geometry, applying_geometry
		if applying_geometry:
			return
		auto_geometry = False

	root.bind('<Configure>', on_root_configure)

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
 
	# Set up the main frame to fill the window
	frame = ttk.Frame(root, padding=12)
	frame.pack(fill='both', expand=True)

	# Prepare a list of champion display names for autocomplete.
	data_dir = get_user_data_dir()
	local_list_path = os.path.join(data_dir, 'champions.txt')
	champion_list = []

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

	frame['padding'] = 12
	if os.path.exists(local_list_path):
		try:
			with open(local_list_path, encoding='utf-8') as f:
				champion_list = [line.strip() for line in f if line.strip()]
		except Exception:
			champion_list = []
	if not champion_list:
		try:
			mapping, dd_version, display_names = load_champion_key_map()
			champion_list = display_names
		except Exception:
			champion_list = []

	# status for champion updater (shows local/online update state)
	status_var = tk.StringVar(value='Champion list: local (cached)')
	# Thread pool for background fetches (create before any submit)
	executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

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

	# Shared autocomplete Listbox with scrollbar (one visible at a time)
	autocomplete_frame = tk.Frame(root, bd=1, relief='solid')
	autocomplete_box = tk.Listbox(autocomplete_frame, height=6)
	scrollbar = ttk.Scrollbar(autocomplete_frame, orient='vertical', command=autocomplete_box.yview)
	autocomplete_box.configure(exportselection=False, yscrollcommand=scrollbar.set)
	autocomplete_box.grid(row=0, column=0, sticky='nsew')
	scrollbar.grid(row=0, column=1, sticky='ns')
	autocomplete_frame.grid_rowconfigure(0, weight=1)
	autocomplete_frame.grid_columnconfigure(0, weight=1)

	# active entry holder so listbox callbacks know which Entry to fill
	active = {'entry': None}

	def show_autocomplete(entry, items):
		if not items:
			autocomplete_frame.place_forget()
			return
		autocomplete_box.delete(0, tk.END)
		for it in items:
			autocomplete_box.insert(tk.END, it)
		# position the listbox directly under the entry
		x = entry.winfo_rootx() - root.winfo_rootx()
		y = entry.winfo_rooty() - root.winfo_rooty() + entry.winfo_height()
		w = entry.winfo_width()
		autocomplete_frame.place(x=x, y=y, width=w + 18)  # add space for scrollbar
		autocomplete_frame.lift()

	def hide_autocomplete():
		autocomplete_frame.place_forget()

	def pick_current(event=None):
		sel = autocomplete_box.curselection()
		if not sel:
			return
		val = autocomplete_box.get(sel[0])
		ent = active.get('entry')
		if ent:
			ent.delete(0, tk.END)
			ent.insert(0, val)
		hide_autocomplete()

	autocomplete_box.bind('<ButtonRelease-1>', pick_current)
	autocomplete_box.bind('<Return>', pick_current)
	autocomplete_box.bind('<Escape>', lambda e: hide_autocomplete())

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
					hide_autocomplete()
				return
			text = entry.get().strip().lower()
			if not text:
				matches = champion_list
			else:
				matches = [c for c in champion_list if c.lower().startswith(text)]
			if matches:
				active['entry'] = entry
				show_autocomplete(entry, matches)
			else:
				hide_autocomplete()

		entry.bind('<KeyRelease>', on_keyrelease)
		# small delay to allow clicks into the listbox to register
		entry.bind('<FocusOut>', lambda e: root.after(150, hide_autocomplete))
		entry.bind('<FocusIn>', lambda e, ent=entry: (clear_placeholder(ent), active.update({'entry': ent}), show_autocomplete(ent, champion_list)))

	# No CSV lookups: DDragon is the authoritative source for champion data.

	PLACEHOLDER_TEXT = 'Select champion'

	def put_placeholder(entry):
		entry.delete(0, tk.END)
		entry.insert(0, PLACEHOLDER_TEXT)
		entry._placeholder = True

	def clear_placeholder(entry):
		if getattr(entry, '_placeholder', False):
			entry.delete(0, tk.END)
			entry._placeholder = False

	def ensure_placeholder(entry):
		if not entry.get().strip():
			put_placeholder(entry)

	# Returned fields (we use DDragon cooldowns: Q/W/E/R)
	returned_fields = ['Q', 'W', 'E', 'R']

	# Header labels for the spell columns (Q/W/E/R)
	# Place headers on row 1 so the controls_frame (row 0) does not overlap them
	for i, fld in enumerate(returned_fields):
		tk.Label(frame, text=fld).grid(row=1, column=3 + i, sticky='w', padx=(0, 6), pady=(0, 6))

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
	# Hotkey controls: allow user to set the toggle shortcut
	ttk.Label(controls_frame, text='Hotkey:').pack(side='left', padx=(4, 0))
	hotkey_entry = ttk.Entry(controls_frame, textvariable=hk_input_var, width=14)
	hotkey_entry.pack(side='left', padx=(4, 4))
	ttk.Button(controls_frame, text='Set', command=lambda: apply_hotkey(hk_input_var.get())).pack(side='left', padx=(2, 6))
	tk.Label(controls_frame, textvariable=hotkey_status).pack(side='left')

	# DDragon is the default source; no CSV toggle required.

	def make_row(index):
		# index is 0-based logical row index; grid row will be base_row + index
		grid_row = base_row + index
		# per-row 'Name:' label and champion entry
		lbl_name = ttk.Label(frame, text='Name:')
		lbl_name.grid(row=grid_row, column=0, sticky='w', padx=(0, 6), pady=6)
		e = ttk.Entry(frame, width=36)
		e.grid(row=grid_row, column=1, padx=(0, 6), pady=6)
		put_placeholder(e)
		e.bind('<FocusIn>', lambda ev, ent=e: clear_placeholder(ent))
		e.bind('<FocusOut>', lambda ev, ent=e: ensure_placeholder(ent))
		champ_icon = ttk.Label(frame)
		champ_icon.grid(row=grid_row, column=2, padx=(0, 6), pady=6)

		# attach autocomplete behavior to this entry
		attach_autocomplete(e)

		rv = tk.StringVar(value='')

		# create one label per returned field so headers align with values
		val_labels = []
		rvs = []
		for i in range(len(returned_fields)):
			v = tk.StringVar(value='')
			# allow wider labels to accommodate descriptions
			lbl = ttk.Label(frame, textvariable=v, width=40, anchor='w', compound='left')
			lbl.grid(row=grid_row, column=3 + i, sticky='w')
			val_labels.append(lbl)
			rvs.append(v)

		rows.append({'label': lbl_name, 'entry': e, 'icon': champ_icon, 'icon_img': None, 'val_labels': val_labels, 'rvs': rvs, 'rv_imgs': [None]*len(returned_fields)})

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
				r['icon'].grid()
				for lbl in r['val_labels']:
					lbl.grid()
			else:
				# hide
				r['label'].grid_remove()
				r['entry'].grid_remove()
				r['icon'].configure(image='')
				r['icon'].grid_remove()
				for lbl in r['val_labels']:
					lbl.grid_remove()
				# show/hide per-row label, entry, and value labels
		set_geometry_for_rows(n)

	rows_combo.bind('<<ComboboxSelected>>', update_rows)

	def return_all(event=None):
		try:
			n = int(rows_combo.get())
		except Exception:
			n = max_rows

		# gather only non-placeholder names
		names = []
		for r in rows:
			name = r['entry'].get().strip()
			if name and not getattr(r['entry'], '_placeholder', False):
				names.append(name)

		# rewrite entries so filled names are packed at the top, placeholders below
		for i, r in enumerate(rows):
			r['entry'].delete(0, tk.END)
			if i < len(names):
				r['entry'].insert(0, names[i])
				r['entry']._placeholder = False
			else:
				put_placeholder(r['entry'])
				for v in r['rvs']:
					v.set('')
		n = len(names) if names else 1
		rows_combo.set(str(n))
		update_rows()

		# Always use Data Dragon in background threads
	        # Always use Data Dragon in background threads
		# Always use Data Dragon in background threads
		def make_task(index, name):
			def task():
				mode = view_mode_var.get()
				icon_image = None
				result_icons = {slot: None for slot in returned_fields}
				result = None
				try:
					print(f"[lookup] row={index} name={name} mode={mode}")
					# resolve champ key
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
						# champion icon
						champ_img = (data.get('image') or {}).get('full')
						if champ_img:
							try:
								url = f"{DD_BASE}/{version}/img/champion/{champ_img}"
								resp = requests.get(url, timeout=5)
								resp.raise_for_status()
								im = Image.open(io.BytesIO(resp.content))
								im = im.resize((48, 48), Image.LANCZOS)
								icon_image = ImageTk.PhotoImage(im)
							except Exception:
								icon_image = None
						# spells
						spells = data.get('spells', [])
						result = {}
						slots = ['Q', 'W', 'E', 'R']
						for i, slot in enumerate(slots):
							val = '-'
							try:
								spell = spells[i]
								if mode == 'Cooldown':
									val = spell.get('cooldownBurn', '-')
								else:
									val = spell.get('tooltip') or spell.get('description') or '-'
								img_full = (spell.get('image') or {}).get('full')
								if img_full:
									try:
										url = f"{DD_BASE}/{version}/img/spell/{img_full}"
										resp = requests.get(url, timeout=5)
										resp.raise_for_status()
										im = Image.open(io.BytesIO(resp.content))
										im = im.resize((32, 32), Image.LANCZOS)
										result_icons[slot] = ImageTk.PhotoImage(im)
									except Exception:
										result_icons[slot] = None
							except Exception:
								val = '-'
							result[slot] = val
					print(f"[lookup] row={index} result={result}")
				except Exception as exc:
					result = None
					print(f"[lookup:error] row={index} name={name} -> {exc}")

				def apply_result():
					if not root.winfo_exists():
						return
					try:
						print(f"[apply] row={index} result={result}")
						if result:
							for i, fld in enumerate(returned_fields):
								key = fld[0].upper()
								rows[index]['rvs'][i].set(result.get(key, '-'))
								img = result_icons.get(key)
								rows[index]['rv_imgs'][i] = img
								rows[index]['val_labels'][i].configure(image=img or '')
						else:
							for v in rows[index]['rvs']:
								v.set('Champion not found')
						if icon_image:
							rows[index]['icon_img'] = icon_image
							rows[index]['icon'].configure(image=icon_image)
						else:
							rows[index]['icon'].configure(image='')
					except Exception:
						# If the UI is already torn down, ignore update
						pass

				if root.winfo_exists():
					try:
						root.after(0, apply_result)
					except Exception:
						pass
			return task

		for idx in range(n):
			name = rows[idx]['entry'].get().strip()
			if name and not getattr(rows[idx]['entry'], '_placeholder', False):
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
			put_placeholder(rows[idx]['entry'])
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
