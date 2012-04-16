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
        self._mark_offsets = {}

    def _refresh_source(self):
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
            self._execute(entry)
        region = self.target_view.sel()[0]
        self.target_view.add_regions('screencast_director', [region], 'source', '', sublime.HIDDEN)
        self._start_timer()

    def _execute(self, entry):
        """
        Parses the "entry", which could be a `dict`, a `list`, or a `string`.
        A `dict` entry is the most common:

            - write: "a string"

        A list command has the command as the first arg:

            - [write, 'a string']

         and, finally, just a bare command, where `args` defaults to `[]`:

            - delay
        """
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
        except AssertionError as e:
            sublime.status_message('ScreencastDirector compile error: %s' % e.message)
            raise

    def _append_command(self, command, delay=None):
        if delay is None:
            delay = 100
        self.commands.append((command, delay))

    def _start_timer(self):
        """
        Pops an item off the command queue and runs it.  The command should
        accept one argument: a cursor object, of type sublime.Region, and
        it should return `None` (no changes) or a new cursor region.

        The cursors are cleared and restored between each command.
        """
        if self.commands:
            cmd, delay = self.commands.pop(0)
            cursor = self.target_view.get_regions('screencast_director')[0]
            if cursor in self.target_view.sel():
                self.target_view.sel().subtract(cursor)

            e = self.target_view.begin_edit('screencast_director')
            new_cursor = cmd(cursor, e)
            self.target_view.end_edit(e)

            if new_cursor is None:
                new_cursor = cursor
            elif isinstance(new_cursor, long) or isinstance(new_cursor, int):
                new_cursor = sublime.Region(new_cursor, new_cursor)
            elif isinstance(new_cursor, tuple):
                new_cursor = sublime.Region(new_cursor[0], new_cursor[1])

            self.target_view.sel().add(new_cursor)
            self.target_view.add_regions('screencast_director', [new_cursor], 'source', '', sublime.HIDDEN)
            sublime.set_timeout(self._start_timer, delay)

    def write(self, *what_to_write):
        def _write_letter(letter):
            def _write(cursor, e):
                self.target_view.replace(e, cursor, letter)
                return cursor.a + len(letter)
            return _write

        is_first = True
        for entry in what_to_write:
            if not is_first:
                self._append_command(_write_letter("\n"))
            previous_letter = None
            if isinstance(entry, basestring):
                for letter in entry:
                    delay_min = 50
                    delay_max = 200
                    if previous_letter == letter:
                        delay_max = 100
                    delay = random.randrange(delay_min, delay_max)
                    self._append_command(_write_letter(letter), delay=delay)
                    previous_letter = letter
            else:
                self._execute(entry)
            is_first = False

    def write_inside(self, left, middle=None, right=None, *others):
        """
        You can use this one of three ways:

            - write_inside: "'The first and last character will be used'"
            - write_inside: ["'", "explicitly state left and right", "'"]
            - write_inside:
                - \"
                - write: Nest commands inside
                - \"
        """
        if others:
            # write_inside(a, b, c, d, e)
            #  => left: a, middle: b, right: c, others: [d, e]
            middle = [middle, right]
            right = others[-1]
            middle.extend(others[:-1])
            #  => left: a, middle: [b, c, d], right: e
        elif middle is None and right is None:
            left, middle, right = left[0], left[1:-1], left[-1]

        assert len(left) == len(right), \
            'len({left}) ({len_left}) != '\
            'len({right}) ({len_right})'.format(left=left, len_left=len(left),
                right=right, len_right=len(right))

        def _write_letters(a, b):
            def _write(cursor, e):
                self.target_view.replace(e, cursor, a + b)
                return cursor.a + len(a)
            return _write

        index = len(right)
        for a in left:
            index -= 1
            b = right[index]
            self._append_command(_write_letters(a, b))

        if isinstance(middle, basestring):
            self.write(middle)
        elif isinstance(middle, list):
            for entry in middle:
                self._execute(entry)
        else:
            self._execute(middle)

        for a in left:
            self.go(len(a))

    def insert(self, what_to_write, delay=None):
        def _insert(cursor, e):
            self.target_view.replace(e, cursor, what_to_write)
            return cursor.a + len(what_to_write)
        self._append_command(_insert, delay)

    def delay(self, delay=100):
        def _delay(cursor, e):
            return cursor
        self._append_command(_delay, delay)

    def go(self, where, delay=None):
        def _go(cursor, e):
            cursor = cursor.a + where
            self.target_view.sel().clear()
            self.target_view.sel().add(sublime.Region(cursor, cursor))
            return cursor
        self._append_command(_go, delay)

    def select_all(self, delay=None):
        def _select_all(cursor, e):
            allofit = sublime.Region(0, self.target_view.size())
            self.target_view.sel().clear()
            self.target_view.sel().add(allofit)
            return allofit
        self._append_command(_select_all, delay)

    def delete(self, delay=None):
        def _delete(cursor, e):
            self.target_view.replace(e, cursor, '')
            return cursor.a
        self._append_command(_delete, delay)

    def clear(self):
        self.select_all()
        self.delete()
        self.clear_marks()

    def set_mark(self, name=None, delay=None):
        if not name:
            name = '__tmp__'

        def _set_mark(cursor, e):
            cursor_0 = self.target_view.line(cursor.a).a
            self._mark_offsets[name] = cursor.a - cursor_0
            if self._mark_offsets[name] == 0:
                self._mark_offsets[name] = 1
                cursor_0 -= 1
            self.target_view.add_regions('screencast_director_%s' % name, [sublime.Region(cursor_0, cursor_0)], 'source', '', sublime.HIDDEN)
            return cursor
        self._append_command(_set_mark, delay)

    def goto_mark(self, name=None, delay=None):
        if not name:
            name = '__tmp__'

        def _goto_mark(cursor, e):
            cursors = self.target_view.get_regions('screencast_director_%s' % name)
            return cursors[0].a + self._mark_offsets[name]
        self._append_command(_goto_mark, delay)

    def select_from_mark(self, name=None, delay=None):
        if not self._mark_offsets:
            return

        if not name:
            name = '__tmp__'

        def _select_from_mark(cursor, e):
            cursors = self.target_view.get_regions('screencast_director_%s' % name)
            a = cursors[0].a + self._mark_offsets[name]
            b = cursor.b
            return a, b
        self._append_command(_select_from_mark, delay)

    def clear_marks(self, delay=None):
        def _clear_marks(cursor, e):
            for name in self._mark_offsets:
                self.target_view.erase_regions('screencast_director_%s' % name)
            self._mark_offsets = {}
            return cursor
        self._append_command(_clear_marks, delay)

    def run_command(self, command, args=None):
        def _run_command(cursor, e):
            self.target_view.sel().add(cursor)
            if args is None:
                self.target_view.run_command(command)
            else:
                self.target_view.run_command(command, args)
            cursor = self.target_view.sel()[0]
            return cursor
        self._append_command(_run_command)

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
            the_director._refresh_source()


class ScreencastDirectorBindTargetCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        window = sublime.active_window()
        the_director.target_view = window.active_view()
        sublime.status_message('Bound target view')
        the_director._refresh_source()


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
        the_director._refresh_source()


class ScreencastDirectorNextCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        if the_director.source_view is None:
            window = sublime.active_window()
            window.run_command('screencast_director_bind_source')
        else:
            the_director.index += 1
        the_director._refresh_source()


class ScreencastDirectorPreviousCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        if the_director.source_view is None:
            window = sublime.active_window()
            window.run_command('screencast_director_bind_source')
        else:
            the_director.index -= 1
        the_director._refresh_source()
