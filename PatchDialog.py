"""Desktop setup window for per-game launch options and patches."""

from html import escape
import json

from PatchPackages import discover_patches, validate_selection


class PatchDialog:
    def __init__(self, gtk, games, folder, launch_options, saved):
        self.gtk = gtk
        self.games = games
        self.folder = folder
        self.patches = {}
        self.selected = set()
        self.active_game = None
        self.focused_patches = {}

        saved_games = saved.get('games', {})
        saved_options = saved.get('launch_options', {})
        self.game_options = {}
        for app_id in games:
            previous = saved_games.get(app_id, {}).get('launch_options', {})
            self.game_options[app_id] = {
                key: previous.get(key, saved_options.get(key, default)) is True
                for key, (default, _, _) in launch_options.items()
            }

        self.dialog = gtk.Dialog(title='Deck PhysX Setup')
        self.dialog.set_default_size(1060, 620)
        self.dialog.set_border_width(8)
        body = self.dialog.get_content_area()
        body.set_spacing(10)
        body.set_border_width(12)
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
        self.continue_button = self.dialog.add_button('Continue', gtk.ResponseType.OK)
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

    def game_navigation(self):
        gtk = self.gtk
        panel = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=8)
        panel.set_size_request(220, -1)
        panel.pack_start(self.heading('Games'), False, False, 0)
        self.search = gtk.SearchEntry()
        self.search.set_placeholder_text('Search games')
        panel.pack_start(self.search, False, False, 0)

        self.game_list = gtk.ListBox()
        self.game_list.set_selection_mode(gtk.SelectionMode.SINGLE)
        self.game_list.set_activate_on_single_click(False)
        for app_id, game in self.games.items():
            row = gtk.ListBoxRow()
            row.app_id = app_id
            title = self.label(game['name'])
            title.set_margin_start(10)
            title.set_margin_end(10)
            title.set_margin_top(12)
            title.set_margin_bottom(12)
            row.add(title)
            self.game_list.add(row)
        empty = self.label('No matching games.')
        empty.show()
        self.game_list.set_placeholder(empty)
        self.game_list.set_filter_func(self.game_matches)
        self.search.connect('search-changed', self.filter_games)
        navigation = self.scrolled(self.game_list)
        navigation.set_shadow_type(gtk.ShadowType.IN)
        panel.pack_start(navigation, True, True, 0)
        return panel

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

        page.pack_start(self.heading('Launch options'), False, False, 0)
        options = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=20)
        self.options = {}
        for key, (_, title, description) in launch_options.items():
            control = gtk.CheckButton(label=title)
            control.set_tooltip_text(description)
            options.pack_start(control, False, False, 0)
            self.options[key] = control
        page.pack_start(options, False, False, 0)

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
        listing.set_min_content_height(300)
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

    def store_options(self):
        if self.active_game is not None:
            self.game_options[self.active_game] = {
                key: control.get_active() for key, control in self.options.items()
            }

    def select_game(self, _list, row):
        self.store_options()
        self.active_game = row.app_id if row is not None else None
        if self.active_game is None:
            self.content.set_visible_child_name('empty')
            return
        name = escape(self.games[self.active_game]['name'])
        self.game_title.set_markup(f'<span size="large"><b>{name}</b></span>')
        for key, control in self.options.items():
            control.set_active(self.game_options[self.active_game][key])
        self.show_patches()
        self.content.set_visible_child_name('game')

    def add_patch(self, patch):
        gtk = self.gtk
        row = gtk.ListBoxRow()
        row.patch = patch
        content = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=8)
        content.set_border_width(8)
        checkbox = gtk.CheckButton()
        checkbox.set_size_request(32, 32)
        checkbox.set_active(patch.key in self.selected)
        checkbox.get_accessible().set_name(f'Enable {patch.title}')
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

    def check_selection(self):
        error = ''
        try:
            validate_selection(self.patches, self.selected)
        except ValueError as issue:
            error = str(issue)
        self.error.set_text(error)
        self.error.set_visible(bool(error))
        self.continue_button.set_sensitive(not error)

    def run(self):
        self.dialog.show_all()
        try:
            if self.dialog.run() == self.gtk.ResponseType.OK:
                self.store_options()
                return self.game_options, [patch for key, patch in self.patches.items() if key in self.selected]
            return None
        finally:
            self.dialog.destroy()


def choose_launch_options(config, games, folder, launch_options):
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk
    except (ImportError, ValueError) as error:
        raise RuntimeError('The setup window requires SteamOS Desktop Mode with GTK 3 and PyGObject.') from error
    if not Gtk.init_check()[0]:
        raise RuntimeError('Open the installer in SteamOS Desktop Mode.')
    try:
        saved = json.loads(config.read_text())
    except (OSError, ValueError):
        saved = {}
    return PatchDialog(Gtk, games, folder, launch_options, saved).run()
