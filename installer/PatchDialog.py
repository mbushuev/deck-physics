"""Desktop setup window for per-game launch options and patches."""

from html import escape
from pathlib import Path
from subprocess import SubprocessError

from PatchPackages import discover_patches, validate_selection


ALICE_FRAME_RATES = {
    'default': 'Game default',
    '60': '60 FPS',
    '90': '90 FPS',
    'uncapped': 'Uncapped',
}


def manual_executable(value):
    path = Path(value.strip()).expanduser()
    if not path.is_absolute() or path.suffix.lower() != '.exe' or not path.is_file():
        raise ValueError('Choose an existing .exe using its full path.')
    return path.resolve()


class PatchDialog:
    def __init__(self, gtk, games, folder, launch_options, saved, package_version,
                 check_package, download_package):
        self.gtk = gtk
        self.games = games
        self.folder = folder
        self.patches = {}
        self.selected = set()
        self.active_game = None
        self.focused_patches = {}
        self.check_package = check_package
        self.download_package = download_package
        self.game_rows = {}

        saved_games = saved.get('games', {})
        self.manual_paths = {app_id: game['exe'] for app_id, game in saved_games.items()
                             if app_id in games and game.get('source') == 'manual' and 'exe' in game}
        self.steam_icon = ('steam' if gtk.IconTheme.get_default().has_icon('steam')
                           else 'emblem-default-symbolic')
        saved_options = saved.get('launch_options', {})
        self.game_options = {}
        for app_id in games:
            previous = saved_games.get(app_id, {}).get('launch_options', {})
            self.game_options[app_id] = {
                key: previous.get(key, saved_options.get(key, default)) is True
                for key, (default, _, _) in launch_options.items()
            }
            if app_id == '19680':
                legacy = 'uncapped' if previous.get('unlock_fps') is True else 'default'
                rate = previous.get('frame_rate', legacy)
                self.game_options[app_id]['frame_rate'] = rate if rate in ALICE_FRAME_RATES else 'default'

        self.dialog = gtk.Dialog(title='Deck Physics Setup')
        self.dialog.set_default_size(1060, 620)
        self.dialog.set_border_width(8)
        body = self.dialog.get_content_area()
        body.set_spacing(10)
        body.set_border_width(12)
        body.pack_start(self.package_bar(package_version), False, False, 0)
        main = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=16)
        body.pack_start(main, True, True, 0)
        main.pack_start(self.game_navigation(), False, False, 0)
        main.pack_start(gtk.Separator(orientation=gtk.Orientation.VERTICAL), False, False, 0)

        self.content = gtk.Stack()
        self.content.add_named(self.label('Choose a game to view its settings and patches.'), 'empty')
        self.content.add_named(self.game_page(launch_options), 'game')
        main.pack_start(self.content, True, True, 0)

        self.issues = gtk.Expander(label='Skipped patch files')
        self.issues.set_no_show_all(True)
        self.issue_text = self.label()
        issue_area = self.scrolled(self.issue_text)
        issue_area.set_max_content_height(120)
        issue_area.set_propagate_natural_height(True)
        self.issues.add(issue_area)
        issue_area.show_all()
        body.pack_start(self.issues, False, False, 0)
        self.error = self.label()
        self.error.get_style_context().add_class('error')
        self.error.set_no_show_all(True)
        body.pack_start(self.error, False, False, 0)
        self.status = self.label()
        self.status.get_style_context().add_class('dim-label')
        self.status.set_no_show_all(True)
        body.pack_start(self.status, False, False, 0)

        self.refresh_button = gtk.Button(label='Refresh patches')
        self.refresh_button.set_tooltip_text('Scan the patches folder beside Install.sh again.')
        self.refresh_button.connect('clicked', self.refresh_clicked)
        actions = self.dialog.get_action_area()
        actions.add(self.refresh_button)
        actions.set_child_secondary(self.refresh_button, True)
        self.dialog.add_button('Cancel', gtk.ResponseType.CANCEL)
        self.continue_button = self.dialog.add_button('Set Up Game', gtk.ResponseType.OK)
        self.continue_button.get_style_context().add_class('suggested-action')
        self.dialog.set_default_response(gtk.ResponseType.OK)

        remembered = {f'{app_id}:{patch["id"]}': patch['sha256']
                      for app_id, game in saved_games.items()
                      for patch in game.get('patches', ())}
        self.scan(remembered)
        self.content.show_all()
        self.game_list.connect('row-selected', self.select_game)
        self.game_list.select_row(self.game_list.get_row_at_index(0))

    def label(self, text=''):
        label = self.gtk.Label(label=text, xalign=0)
        label.set_line_wrap(True)
        return label

    def heading(self, text):
        label = self.label()
        label.set_markup(f'<b>{escape(text)}</b>')
        return label

    def scrolled(self, child):
        gtk = self.gtk
        area = gtk.ScrolledWindow()
        area.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
        area.set_overlay_scrolling(False)
        area.add(child)
        return area

    def package_bar(self, version):
        gtk = self.gtk
        panel = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=4)
        bar = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=10)
        panel.pack_start(bar, False, False, 0)
        bar.pack_start(self.heading(f'NVIDIA PhysX {version}'), False, False, 0)
        self.package_status = self.label()
        bar.pack_start(self.package_status, True, True, 0)
        check = gtk.Button(label='Check package')
        check.connect('clicked', self.update_package_status)
        bar.pack_start(check, False, False, 0)
        self.package_download = gtk.Button(label='Download package')
        self.package_download.set_no_show_all(True)
        self.package_download.connect('clicked', self.download_package_clicked)
        bar.pack_start(self.package_download, False, False, 0)
        self.package_path = gtk.Entry()
        self.package_path.set_editable(False)
        self.package_path.set_no_show_all(True)
        self.package_path.get_accessible().set_name('Verified package location')
        panel.pack_start(self.package_path, False, False, 0)
        self.update_package_status()
        return panel

    def update_package_status(self, _button=None):
        try:
            package = self.check_package()
        except OSError as error:
            self.package_status.set_text(f'Could not check package. {error}')
            self.package_download.show()
            self.package_path.hide()
            return
        self.package_status.set_text('Verified (SHA-256)' if package else 'No verified package found')
        self.package_download.set_visible(package is None)
        self.package_path.set_text(str(package) if package else '')
        self.package_path.set_visible(package is not None)

    def download_package_clicked(self, _button):
        try:
            self.download_package()
        except (OSError, ValueError, RuntimeError, SubprocessError) as error:
            self.package_status.set_text(f'Could not download package. {error}')
        else:
            self.update_package_status()

    def game_navigation(self):
        gtk = self.gtk
        panel = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=8)
        panel.set_size_request(220, -1)
        panel.pack_start(self.heading('Supported games'), False, False, 0)
        self.search = gtk.SearchEntry()
        self.search.set_placeholder_text('Search games')
        panel.pack_start(self.search, False, False, 0)

        self.game_list = gtk.ListBox()
        self.game_list.set_selection_mode(gtk.SelectionMode.SINGLE)
        self.game_list.set_activate_on_single_click(False)
        for app_id, game in self.games.items():
            row = gtk.ListBoxRow()
            row.app_id = app_id
            content = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=4)
            content.set_border_width(9)
            title = self.label(game['name'])
            content.pack_start(title, False, False, 0)
            source = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=5)
            row.source_icon = gtk.Image()
            row.source_label = self.label()
            row.source_label.get_style_context().add_class('dim-label')
            source.pack_start(row.source_icon, False, False, 0)
            source.pack_start(row.source_label, False, False, 0)
            content.pack_start(source, False, False, 0)
            row.add(content)
            self.game_list.add(row)
            self.game_rows[app_id] = row
            self.update_source_badge(app_id)
        empty = self.label('No matching games.')
        empty.show()
        self.game_list.set_placeholder(empty)
        self.game_list.set_filter_func(self.game_matches)
        self.search.connect('search-changed', self.filter_games)
        navigation = self.scrolled(self.game_list)
        navigation.set_shadow_type(gtk.ShadowType.IN)
        panel.pack_start(navigation, True, True, 0)
        return panel

    def selected_executable(self, app_id):
        value = self.manual_paths.get(app_id)
        if value:
            try:
                return str(manual_executable(value))
            except (OSError, RuntimeError, ValueError):
                return None
        return self.games[app_id].get('exe')

    def update_source_badge(self, app_id):
        row = self.game_rows[app_id]
        exe = self.selected_executable(app_id)
        if exe and exe == self.games[app_id].get('exe'):
            label, icon = 'Steam', self.steam_icon
        elif exe:
            label, icon = 'Manual', 'document-open-symbolic'
        elif self.manual_paths.get(app_id):
            label, icon = 'Invalid executable', 'dialog-warning-symbolic'
        else:
            label, icon = 'No executable selected', 'list-add-symbolic'
        row.source_icon.set_from_icon_name(icon, self.gtk.IconSize.MENU)
        row.source_label.set_text(label)

    def game_matches(self, row):
        return self.search.get_text().strip().casefold() in self.games[row.app_id]['name'].casefold()

    def filter_games(self, _search):
        self.game_list.invalidate_filter()
        active = self.game_list.get_selected_row()
        if active is None or not self.game_matches(active):
            first = next((row for row in self.game_list.get_children() if self.game_matches(row)), None)
            self.game_list.select_row(first)

    def game_page(self, launch_options):
        gtk = self.gtk
        page = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=10)
        self.game_title = self.label()
        page.pack_start(self.game_title, False, False, 0)
        page.pack_start(self.heading('Game executable'), False, False, 0)
        path_row = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=8)
        self.executable_path = gtk.Entry()
        self.executable_path.set_placeholder_text('Enter the full path to an .exe')
        self.path_handler = self.executable_path.connect('changed', self.executable_changed)
        path_row.pack_start(self.executable_path, True, True, 0)
        browse = gtk.Button(label='Browse…')
        browse.connect('clicked', self.browse_executable)
        path_row.pack_start(browse, False, False, 0)
        self.clear_executable = gtk.Button()
        self.clear_executable.connect('clicked', lambda _button: self.executable_path.set_text(''))
        path_row.pack_start(self.clear_executable, False, False, 0)
        page.pack_start(path_row, False, False, 0)
        self.executable_hint = self.label()
        self.executable_hint.get_style_context().add_class('dim-label')
        page.pack_start(self.executable_hint, False, False, 0)

        page.pack_start(self.heading('Launch options'), False, False, 0)
        self.launch_controls = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=20)
        self.options = {}
        for key, (_, title, description) in launch_options.items():
            control = gtk.CheckButton(label=title)
            control.set_tooltip_text(description)
            self.launch_controls.pack_start(control, False, False, 0)
            self.options[key] = control

        self.frame_rate_row = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=6)
        label = gtk.Label.new_with_mnemonic('Frame _rate')
        self.frame_rate = gtk.ComboBoxText()
        label.set_mnemonic_widget(self.frame_rate)
        for rate, title in ALICE_FRAME_RATES.items():
            self.frame_rate.append(rate, title)
        self.frame_rate.set_tooltip_text('Choose the game default, a frame rate limit, or Uncapped.')
        self.frame_rate_row.pack_start(label, False, False, 0)
        self.frame_rate_row.pack_start(self.frame_rate, False, False, 0)
        self.frame_rate_row.show_all()
        self.frame_rate_row.set_no_show_all(True)
        self.frame_rate_row.hide()
        self.launch_controls.pack_start(self.frame_rate_row, False, False, 0)
        page.pack_start(self.launch_controls, False, False, 0)

        page.pack_start(gtk.Separator(orientation=gtk.Orientation.HORIZONTAL), False, False, 0)
        page.pack_start(self.heading('Patches'), False, False, 0)
        patches = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=14)
        self.patch_rows = gtk.ListBox()
        self.patch_rows.set_selection_mode(gtk.SelectionMode.SINGLE)
        self.patch_rows.set_activate_on_single_click(False)
        self.patch_rows.connect('row-selected', self.show_details)
        empty = self.label('Copy patch archives into patches/<game>/ and select Refresh patches.')
        empty.set_margin_start(12)
        empty.set_margin_end(12)
        empty.get_style_context().add_class('dim-label')
        empty.show()
        self.patch_rows.set_placeholder(empty)
        listing = self.scrolled(self.patch_rows)
        listing.set_shadow_type(gtk.ShadowType.IN)
        listing.set_min_content_height(220)
        patches.pack_start(listing, True, True, 0)

        details = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=8)
        details.set_border_width(6)
        self.detail_title = self.label()
        self.detail_text = self.label()
        self.detail_text.set_max_width_chars(32)
        self.detail_text.set_selectable(True)
        details.pack_start(self.detail_title, False, False, 0)
        details.pack_start(self.detail_text, False, False, 0)
        sidebar = self.scrolled(details)
        sidebar.set_size_request(295, -1)
        patches.pack_start(sidebar, False, False, 0)
        page.pack_start(patches, True, True, 0)
        return page

    def refresh_executable(self):
        app_id = self.active_game
        game = self.games[app_id]
        manual = self.manual_paths.get(app_id)
        exe = self.selected_executable(app_id)
        available = exe is not None
        self.clear_executable.set_label('Use Steam copy' if 'exe' in game else 'Clear path')
        self.clear_executable.set_sensitive(bool(manual))
        self.executable_path.set_placeholder_text(game.get('exe', 'Enter the full path to an .exe'))
        if exe and exe == game.get('exe'):
            hint = 'Steam found this game. Enter a different path to use another copy.'
        else:
            hint = 'Choose the executable for this game from a copy you trust. Manual copies use a separate Proton prefix.'
        self.executable_hint.set_text(hint)
        self.launch_controls.set_sensitive(available)
        for row in self.patch_rows.get_children():
            row.checkbox.set_sensitive(available)

    def executable_changed(self, entry):
        app_id = self.active_game
        if app_id is None:
            return
        self.manual_paths[app_id] = entry.get_text().strip()
        self.update_source_badge(app_id)
        self.refresh_executable()
        self.check_selection()

    def browse_executable(self, _button):
        gtk = self.gtk
        chooser = gtk.FileChooserNative.new('Choose a game executable', self.dialog,
                                            gtk.FileChooserAction.OPEN, 'Choose', 'Cancel')
        exe_filter = gtk.FileFilter()
        exe_filter.set_name('Windows executables')
        exe_filter.add_pattern('*.exe')
        exe_filter.add_pattern('*.EXE')
        chooser.add_filter(exe_filter)
        if selected := self.selected_executable(self.active_game):
            chooser.set_filename(selected)
        try:
            if chooser.run() == gtk.ResponseType.ACCEPT and (filename := chooser.get_filename()):
                self.executable_path.set_text(filename)
        finally:
            chooser.destroy()

    def store_options(self):
        if self.active_game is not None:
            options = self.game_options[self.active_game]
            options.update({key: control.get_active() for key, control in self.options.items()})
            if self.active_game == '19680':
                options['frame_rate'] = self.frame_rate.get_active_id()

    def select_game(self, _list, row):
        self.store_options()
        self.active_game = row.app_id if row is not None else None
        if self.active_game is None:
            self.content.set_visible_child_name('empty')
            self.check_selection()
            return
        name = escape(self.games[self.active_game]['name'])
        self.game_title.set_markup(f'<span size="large"><b>{name}</b></span>')
        self.executable_path.handler_block(self.path_handler)
        self.executable_path.set_text(self.manual_paths.get(self.active_game, ''))
        self.executable_path.handler_unblock(self.path_handler)
        options = self.game_options[self.active_game]
        for key, control in self.options.items():
            control.set_active(options[key])
        self.frame_rate_row.set_visible(self.active_game == '19680')
        if self.active_game == '19680':
            self.frame_rate.set_active_id(options['frame_rate'])
        self.show_patches()
        self.refresh_executable()
        self.content.set_visible_child_name('game')
        self.check_selection()

    def add_patch(self, patch):
        gtk = self.gtk
        row = gtk.ListBoxRow()
        row.patch = patch
        content = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=8)
        content.set_border_width(8)
        checkbox = gtk.CheckButton()
        checkbox.set_size_request(32, 32)
        checkbox.set_active(patch.key in self.selected)
        checkbox.set_sensitive(self.selected_executable(patch.app_id) is not None)
        checkbox.get_accessible().set_name(f'Enable {patch.title}')
        row.checkbox = checkbox
        checkbox.connect('toggled', self.toggle_patch, row)
        content.pack_start(checkbox, False, False, 0)
        text = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=3)
        title = self.label(patch.title)
        description = self.label(patch.description)
        description.get_style_context().add_class('dim-label')
        text.pack_start(title, False, False, 0)
        text.pack_start(description, False, False, 0)
        content.pack_start(text, True, True, 0)
        row.add(content)
        self.patch_rows.add(row)
        return row

    def show_patches(self):
        focused = self.focused_patches.get(self.active_game)
        for row in self.patch_rows.get_children():
            self.patch_rows.remove(row)
        active = None
        visible = (patch for patch in self.patches.values() if patch.app_id == self.active_game)
        for patch in sorted(visible, key=lambda item: (bool(item.requires), item.title.casefold())):
            row = self.add_patch(patch)
            if patch.key == focused:
                active = row
        self.patch_rows.show_all()
        self.patch_rows.select_row(active or self.patch_rows.get_row_at_index(0))
        if not self.patch_rows.get_selected_row():
            self.show_details(self.patch_rows, None)

    def show_details(self, _rows, row):
        if row is None:
            self.detail_title.set_text('Patch details')
            self.detail_text.set_text('Select a patch to see its details.')
            return
        patch = row.patch
        self.focused_patches[patch.app_id] = patch.key
        self.detail_title.set_markup(f'<b>{escape(patch.title)}</b>')
        sections = [patch.details or patch.description]
        if patch.requires_nvidia_physx:
            sections.append('Uses the official NVIDIA PhysX package.')
        if patch.requires:
            names = []
            for name in patch.requires:
                dependency = self.patches.get(f'{patch.app_id}:{name}')
                names.append(dependency.title if dependency else f'{name} (file missing)')
            sections.append('Requires\n' + '\n'.join(names))
        changes = [f'{key}={value}' for key, value in patch.environment.items()]
        changes.extend(f'{key} → {path}' for key, path in patch.file_environment.items())
        if patch.preload:
            changes.append(f'Loads {patch.preload} at launch.')
        if patch.prepare:
            changes.append(f'Runs {patch.prepare} on this Deck during setup.')
        if changes:
            sections.append('Changes\n' + '\n'.join(changes))
        sections.append(f'Package\n{patch.path.relative_to(self.folder).as_posix()}')
        self.detail_text.set_text('\n\n'.join(sections))

    def toggle_patch(self, checkbox, row):
        key = row.patch.key
        if checkbox.get_active():
            self.selected.add(key)
        else:
            self.selected.discard(key)
        self.patch_rows.select_row(row)
        self.check_selection()

    def scan(self, remembered):
        self.patches, issues = discover_patches(self.folder, self.games)
        self.selected = {key for key, patch in self.patches.items()
                         if remembered.get(key) == patch.sha256}
        self.show_patches()
        self.issue_text.set_text('\n'.join(issues))
        self.issues.set_visible(bool(issues))
        self.check_selection()

    def refresh_clicked(self, _button):
        remembered = {key: self.patches[key].sha256 for key in self.selected}
        self.scan(remembered)
        count = len(self.patches)
        self.status.set_text(f'{count} patch found.' if count == 1 else f'{count} patches found.')
        self.status.show()

    def active_patch_keys(self):
        return {key for key in self.selected if self.patches[key].app_id == self.active_game}

    def check_selection(self):
        app_id = self.active_game
        ready = app_id is not None and self.selected_executable(app_id) is not None
        error = ''
        try:
            if ready:
                validate_selection(self.patches, self.active_patch_keys())
            elif self.manual_paths.get(app_id):
                raise ValueError(f'Choose an existing .exe for {self.games[app_id]["name"]}.')
        except ValueError as issue:
            error = str(issue)
        self.error.set_text(error)
        self.error.set_visible(bool(error))
        self.continue_button.set_sensitive(ready and not error)
        return ready and not error

    def run(self):
        self.dialog.show_all()
        try:
            if self.dialog.run() == self.gtk.ResponseType.OK and self.check_selection():
                app_id = self.active_game
                self.store_options()
                choices = {app_id: {'launch_options': self.game_options[app_id],
                                    'manual_exe': self.manual_paths.get(app_id)}}
                selected = self.active_patch_keys()
                return choices, [patch for key, patch in self.patches.items() if key in selected]
            return None
        finally:
            self.dialog.destroy()


def choose_launch_options(saved, games, folder, launch_options, package_version, check_package,
                          download_package):
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk
    except (ImportError, ValueError) as error:
        raise RuntimeError('The setup window requires SteamOS Desktop Mode with GTK 3 and PyGObject.') from error
    if not Gtk.init_check()[0]:
        raise RuntimeError('Open the installer in SteamOS Desktop Mode.')
    return PatchDialog(Gtk, games, folder, launch_options, saved, package_version,
                       check_package, download_package).run()
