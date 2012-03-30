import random
import sublime
import sublime_plugin
import yaml


class ScreencastDirector(object):
    def __init__(self):
        self.source_view = None
        self.target_view = None
        self.index = 0
        self.commands = []  # stores a list of commands to perform on the target_view.
        self._marks = {}

    def refresh_source(self):
        if self.source_view is None:
            return

        window = self.source_view.window()
        active_view = sublime.active_window().active_view()
        regions = self.source_view.get_regions('screencast_director')
        if self.index < 0:
            self.index = len(regions) - 1
        elif self.index >= len(regions):
            self.index = 0

        self.source_view.sel().clear()
        self.source_view.sel().add(regions[the_director.index])
        pos = self.source_view.viewport_position()
        self.source_view.show_at_center(regions[the_director.index])
        new_pos = self.source_view.viewport_position()
        if abs(new_pos[0] - pos[0]) <= 1.0 and abs(new_pos[1] - pos[1]) <= 1.0:
            self.source_view.set_viewport_position((new_pos[0], new_pos[1] + 1))
            self.source_view.set_viewport_position((new_pos[0], new_pos[1]))
        window.focus_view(self.source_view)
        window.focus_view(active_view)

    def _run(self):
        regions = self.source_view.get_regions('screencast_director')
        region = regions[self.index]
        content = self.source_view.substr(region)
        commands = yaml.load(content)
        for entry in commands:
            self.execute(entry)
        region = self.target_view.sel()[0]
        self.target_view.add_regions('screencast_director', [region], 'source', '', sublime.HIDDEN)
        self.start_timer()

    def execute(self, entry):
        if isinstance(entry, dict):
            command, args = entry.items()[0]
        elif isinstance(entry, list):
            command, args = entry[0], entry[1:]
        else:
            command, args = entry, []
        if not isinstance(args, list):
            args = [args]
        cmd = getattr(self, command)
        try:
            cmd(*args)
        except TypeError:
            if args == [{}]:
                cmd()
            else:
                raise

    def append_command(self, command, delay=None, delay_min=50, delay_max=200):
        if delay is None:
            if delay_min is None:
                delay_min = 50
            if delay_max is None:
                delay_max = 200
            delay = random.randrange(delay_min, delay_max)
        self.commands.append((command, delay))

    def start_timer(self):
        if self.commands:
            cmd, delay = self.commands.pop(0)
            cursor = self.target_view.get_regions('screencast_director')[0]
            if cursor in self.target_view.sel():
                self.target_view.sel().subtract(cursor)
            new_cursor = cmd(cursor)
            if isinstance(new_cursor, long) or isinstance(new_cursor, int):
                new_cursor = sublime.Region(new_cursor, new_cursor)
            elif isinstance(new_cursor, tuple):
                new_cursor = sublime.Region(new_cursor[0], new_cursor[1])

            self.target_view.sel().add(new_cursor)
            self.target_view.add_regions('screencast_director', [new_cursor], 'source', '', sublime.HIDDEN)
            sublime.set_timeout(self.start_timer, delay)

    def write(self, *what_to_write, **kwargs):
        def _write_letter(letter):
            def _write(cursor):
                e = self.target_view.begin_edit('screencast_director')
                self.target_view.replace(e, cursor, letter)
                self.target_view.end_edit(e)
                return cursor.a + len(letter)
            return _write

        for entry in what_to_write:
            previous_letter = None
            if isinstance(entry, basestring):
                for letter in entry:
                    if previous_letter == letter:
                        delay_max = 100
                    else:
                        delay_max = None
                    self.append_command(_write_letter(letter), delay_max=delay_max)
                    previous_letter = letter
            else:
                self.execute(entry)

    def write_inside(self, left, middle, right, *others):
        if others:
            middle = [middle, right]
            right = others[-1]
            middle.extend(others[:-1])

        assert len(left) == len(right), '%i != %i' % (len(left), len(right))

        def _write_letters(a, b):
            def _write(cursor):
                e = self.target_view.begin_edit('screencast_director')
                self.target_view.replace(e, cursor, a + b)
                self.target_view.end_edit(e)
                return cursor.a + len(a)
            return _write

        index = len(right)
        for a in left:
            index -= 1
            b = right[index]
            self.append_command(_write_letters(a, b))

        if isinstance(middle, basestring):
            self.write(middle)
        elif isinstance(middle, list):
            for entry in middle:
                self.execute(entry)
        else:
            self.execute(middle)

        for a in left:
            self.go(len(a))

    def insert(self, what_to_write, delay=None):
        def _insert(cursor):
            e = self.target_view.begin_edit('screencast_director')
            self.target_view.replace(e, cursor, what_to_write)
            self.target_view.end_edit(e)
            return cursor.a + len(what_to_write)
        self.append_command(_insert, delay)

    def delay(self, delay=100):
        def _delay(cursor):
            return cursor
        self.append_command(_delay, delay)

    def go(self, where, delay=None):
        def _go(cursor):
            cursor = cursor.a + where
            self.target_view.sel().clear()
            self.target_view.sel().add(sublime.Region(cursor, cursor))
            return cursor
        self.append_command(_go, delay)

    def select_all(self, delay=None):
        def _select_all(cursor):
            allofit = sublime.Region(0, self.target_view.size())
            self.target_view.sel().clear()
            self.target_view.sel().add(allofit)
            return allofit
        self.append_command(_select_all, delay)

    def delete(self, delay=None):
        def _delete(cursor):
            e = self.target_view.begin_edit('screencast_director')
            self.target_view.replace(e, cursor, '')
            self.target_view.end_edit(e)
            return cursor.a
        self.append_command(_delete, delay)

    def clear(self):
        self.select_all()
        self.delete()
        self.clear_marks()

    def set_mark(self, name=None, delay=None):
        if not name:
            name = '__tmp__'

        def _set_mark(cursor):
            self._marks[name] = cursor
            return cursor
        self.append_command(_set_mark, delay)

    def goto_mark(self, name=None, delay=None):
        if not name:
            name = '__tmp__'

        def _goto_mark(cursor):
            cursor = self._marks.get(name, cursor)
            return cursor
        self.append_command(_goto_mark, delay)

    def select_from_mark(self, name=None, delay=None):
        if not self._marks:
            return

        if not name:
            name = '__tmp__'

        def _select_from_mark(cursor):
            a = self._marks.get(name, cursor).a
            b = cursor.b
            return a, b
        self.append_command(_select_from_mark, delay)

    def clear_marks(self, delay=None):
        def _clear_marks(cursor):
            self._marks = {}
            return cursor
        self.append_command(_clear_marks, delay)

    def run_command(self, command, args):
        def _run_command(cursor):
            self.target_view.run_command(command, args)
            # cursor = self.target_view.sel()[0]
            return cursor
        self.append_command(_run_command)

the_director = ScreencastDirector()


class ScreencastDirectorBindSourceCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        window = sublime.active_window()
        source_view = the_director.source_view = window.active_view()
        if source_view is not None:
            the_director.index = 0

            source_view.sel().clear()
            allofit = sublime.Region(0, source_view.size())
            source = source_view.substr(allofit)
            search = "\n\n-"
            parts = source.split(search)
            blocks = []

            skip = parts.pop(0)
            if len(skip) and skip[0] == "-":
                blocks.append(sublime.Region(0, len(skip.rstrip())))

            offset = len(skip)

            for part in parts:
                offset += len(search) - 1
                start = offset
                offset += 1
                end = offset + len(part.rstrip())
                offset += len(part)
                region = sublime.Region(start, end)
                blocks.append(region)
            source_view.add_regions(
                'screencast_director',
                blocks,
                'source',
                '',
                sublime.DRAW_OUTLINED
                )

            sublime.status_message('Bound source view and set index to 0')
            the_director.refresh_source()


class ScreencastDirectorBindTargetCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        window = sublime.active_window()
        the_director.target_view = window.active_view()
        sublime.status_message('Bound target view')
        the_director.refresh_source()


class ScreencastDirectorRunCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        window = sublime.active_window()
        source_view = the_director.source_view
        if the_director.target_view is None:
            window.run_command('screencast_director_bind_target')
        target_view = the_director.target_view

        if source_view is None:
            sublime.status_message('Choose your source view')
            return

        if target_view.id() == source_view.id():
            the_director.target_view = None
            sublime.status_message('Choose your target view')
            return

        the_director._run()
        the_director.index += 1
        the_director.refresh_source()


class ScreencastDirectorNextCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        if the_director.source_view is None:
            window = sublime.active_window()
            window.run_command('screencast_director_bind_source')
        else:
            the_director.index += 1
        the_director.refresh_source()


class ScreencastDirectorPreviousCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        if the_director.source_view is None:
            window = sublime.active_window()
            window.run_command('screencast_director_bind_source')
        else:
            the_director.index -= 1
        the_director.refresh_source()
