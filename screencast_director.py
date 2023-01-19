import random
import sublime
import sublime_plugin
from . import pyyaml
from functools import reduce


def parse(str, check_nl=True):
    if check_nl and "\n" in str:
        return "\n".join(map(lambda line: parse(line, False), str.split("\n")))
    if len(str) > 1 and str[0] == '"' and str[-1] == '"':
        str = eval(str)
    return str


class ScreencastDirector(object):
    the_director = None

    def __init__(self):
        self.source_view = None
        self.target_view = None
        self.index = 0
        self.commands = []  # stores a list of commands to perform on the target_view.
        self._mark_offsets = {}

    def _refresh_source(self):
        if self.source_view is None:
            return

        active_view = sublime.active_window().active_view()
        regions = self.source_view.get_regions('screencast_director')
        if self.index < 0:
            self.index = len(regions) - 1
        elif self.index >= len(regions):
            self.index = 0

        self.source_view.sel().clear()
        self.source_view.sel().add(regions[ScreencastDirector.the_director.index])
        pos = self.source_view.viewport_position()
        self.source_view.show_at_center(regions[ScreencastDirector.the_director.index])
        new_pos = self.source_view.viewport_position()
        if abs(new_pos[0] - pos[0]) <= 1.0 and abs(new_pos[1] - pos[1]) <= 1.0:
            self.source_view.set_viewport_position((new_pos[0], new_pos[1] + 1))
            self.source_view.set_viewport_position((new_pos[0], new_pos[1]))
        window = self.source_view.window()
        if not window:
            window = self.target_view.window()
        if not window:
            sublime.status_message('I can\'t find a `window`')
            return

        window.focus_view(self.source_view)
        window.focus_view(active_view)

    def _run(self):
        regions = self.source_view.get_regions('screencast_director')
        region = regions[self.index]
        content = self.source_view.substr(region)
        commands = pyyaml.load(content)
        for entry in commands:
            self._execute(entry)
        if len(self.target_view.sel()):
            region = self.target_view.sel()[0]
        else:
            region = sublime.Region(0, 0)
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
            for item in entry.items():
                command, args = item
                break
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
            delay = random.randint(50, 150)
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

            info = {}
            def what_to_do(cls, edit):
                info['new_cursor'] = cmd(cursor, edit)
            ScreencastDirectorCmdCommand.what_to_do = what_to_do
            ScreencastDirector.the_director.target_view.run_command('screencast_director_cmd')

            new_cursor = info['new_cursor']
            if new_cursor is None:
                new_cursor = cursor
            elif isinstance(new_cursor, int):
                new_cursor = sublime.Region(new_cursor, new_cursor)
            elif isinstance(new_cursor, tuple):
                new_cursor = sublime.Region(new_cursor[0], new_cursor[1])

            self.target_view.sel().add(new_cursor)
            self.target_view.add_regions('screencast_director', [new_cursor], 'source', '', sublime.HIDDEN)
            sublime.set_timeout(self._start_timer, delay)

    def set_syntax(self, syntax):
        def _set_syntax(cursor, edit):
            self.target_view.set_syntax_file(syntax)
            return cursor
        self._append_command(_set_syntax)

    def write_parallel(self, *lines):
        max_len = max([len(text) for (_, _, text) in lines])
        for offset in range(0, max_len):
            for (row, col, text) in lines:
                if len(text) < offset:
                    continue
                self.goto(row, col + offset)
                self.write(text[offset], delay_min=20, delay_max=40)

    def write_at(self, row, col, text):
        self.goto(row, col)
        self.write(text)

    def write(self, *what_to_write, **options):
        if len(what_to_write) == 1 and isinstance(what_to_write[0], dict):
            return self.write(what_to_write[0]['write'], **what_to_write[0])

        if options.get('write'):
            what_to_write = options['write']
        if isinstance(what_to_write, str):
            what_to_write = [what_to_write]
        delay_min = options.get('delay_min', 40)
        delay_max = options.get('delay_max', 70)

        def _write_letter(letter):
            def _write(cursor, edit):
                self.target_view.replace(edit, cursor, letter)
                return cursor.begin() + len(letter)
            return _write

        if len(what_to_write) > 1:
            def _add_newline(line):
                if not isinstance(line, str):
                    return line
                if not line or line[-1] != "\n":
                    return line + "\n"
                return line
            what_to_write = map(_add_newline, what_to_write)

        for entry in what_to_write:
            previous_letter = None
            if isinstance(entry, str):
                entry = parse(entry)
                for letter in entry:
                    if delay_min == delay_max:
                        delay = delay_min
                    elif previous_letter == letter:
                        delay = delay_min
                    else:
                        delay = random.randrange(delay_min, delay_max)
                    self._append_command(_write_letter(letter), delay=delay)
                    previous_letter = letter
            else:
                self._execute(entry)

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
            def _write(cursor, edit):
                self.target_view.replace(edit, cursor, a + b)
                return cursor.begin() + len(a)
            return _write

        index = len(right)
        for a in left:
            index -= 1
            b = right[index]
            self._append_command(_write_letters(a, b))

        if isinstance(middle, str):
            self.write(middle)
        elif isinstance(middle, list):
            for entry in middle:
                self._execute(entry)
        else:
            self._execute(middle)

        for a in left:
            self.go(len(a))

    def insert(self, what_to_write, delay=None):
        def _insert(cursor, edit):
            self.target_view.replace(edit, cursor, what_to_write)
            return cursor.begin() + len(what_to_write)
        self._append_command(_insert, delay)

    def _write_at(self, edit, row, col, text):
        # support multiple lines
        if "\n" in text:
            lines = text.splitlines()
            for i, line in enumerate(lines):
                self._write_at(edit, row + i, col, line)
            return

        # fix number of rows
        actual_row, _ = self.target_view.rowcol(self.target_view.text_point(row, 0))
        nl = max(0, row - actual_row)
        if nl:
            point = self.target_view.text_point(actual_row, 0)
            eol_point = self.target_view.line(point).end()
            self.target_view.insert(edit, eol_point, "\n" * nl)
        # fix column
        line = self.target_view.line(self.target_view.text_point(row, 0))
        spaces = max(0, col + len(text) - len(line))
        if spaces:
            point = line.end()
            self.target_view.insert(edit, point, ' ' * spaces)
        # k, we should be good to go now
        point = self.target_view.text_point(row, col)
        self.target_view.replace(edit, sublime.Region(point, point + len(text)), text)
        return point + len(text)

    def write_lines(self, *lines, **options):
        if len(lines) == 1 and isinstance(lines[0], dict):
            return self.write_lines(*lines[0]['lines'], **lines[0])
        delay = options.get('delay', 20)

        def func_maker(char, line_index, char_index):
            def _write_char(cursor, edit):
                row, col = self.target_view.rowcol(cursor.begin())
                line_row = row + line_index
                line_col = col + char_index
                self._write_at(edit, line_row, line_col, char)
                return cursor.begin()
            return _write_char

        info = {'index': 0}
        longest_line_len = reduce(lambda a, b: max(a, len(b)), lines, 0)
        while info['index'] < longest_line_len:
            for line_index, line in enumerate(lines):
                try:
                    char = line[info['index']]
                    char_index = info['index']
                    fn = func_maker(char, line_index, char_index)
                    self._append_command(fn, 0)
                except IndexError:
                    pass
            info['index'] += 1
            self.delay(delay)

    def nl(self, delay=None):
        def _nl(cursor, edit):
            self.target_view.replace(edit, cursor, "\n")
            return cursor.begin() + 1
        self._append_command(_nl, delay)

    def delay(self, delay=100):
        def _delay(cursor, edit):
            return cursor
        self._append_command(_delay, delay)

    def go(self, where, delay=None):
        def _go(cursor, edit):
            cursor = cursor.begin() + where
            self.target_view.sel().clear()
            self.target_view.sel().add(sublime.Region(cursor, cursor))
            return cursor
        self._append_command(_go, delay)

    def select_all(self, delay=None):
        def _select_all(cursor, edit):
            allofit = sublime.Region(0, self.target_view.size())
            self.target_view.sel().clear()
            self.target_view.sel().add(allofit)
            return allofit
        self._append_command(_select_all, delay)

    def select_delta(self, delta, delay=None):
        def _select_delta(cursor, edit):
            selection = sublime.Region(cursor.begin(), cursor.end() + delta)
            self.target_view.sel().clear()
            self.target_view.sel().add(selection)
            return selection
        self._append_command(_select_delta, delay)

    def select_eol(self, delay=None):
        def _select_eol(cursor, edit):
            selection = sublime.Region(cursor.begin(), self.target_view.line(cursor.a).end())
            self.target_view.sel().clear()
            self.target_view.sel().add(selection)
            return selection
        self._append_command(_select_eol, delay)

    def select_next(self, find_next, delay=None):
        def _select_delta(cursor, edit):
            selection = self.target_view.find(find_next, cursor.begin(), sublime.LITERAL)
            self.target_view.sel().clear()
            self.target_view.sel().add(selection)
            return selection
        self._append_command(_select_delta, delay)

    def delete(self, delay=None):
        def _delete(cursor, edit):
            self.target_view.replace(edit, cursor, '')
            return cursor.begin()
        self._append_command(_delete, delay)

    def clear(self, delay=None):
        self.select_all(delay)
        self.delete(delay)
        self.clear_marks(delay)

    def select_lines(self, line_a, line_b, delay=None):
        def _select_lines(cursor, edit):
            last_row = self.target_view.rowcol(len(self.target_view))[0] + 1
            row_a = line_a
            row_b = line_b
            if row_a < 0:
                row_a = last_row + row_a
            if row_b < 0:
                row_b = last_row + row_b
            point_a = self.target_view.text_point(row_a, 0)
            point_b = self.target_view.text_point(row_b, 0)
            # return if the lines are unreachable
            if self.target_view.rowcol(point_a)[0] != line_a:
                return cursor.a
            start = self.target_view.full_line(point_a).begin()
            stop = self.target_view.full_line(point_b).end()
            selection = sublime.Region(start, stop)
            self.target_view.sel().clear()
            self.target_view.sel().add(selection)
            return selection
        self._append_command(_select_lines, delay)

    def clear_lines(self, line_a, line_b, delay=None):
        self.select_lines(line_a, line_b, delay)
        self.delete(delay)

    def insert_at(self, row, col, text):
        def _insert(cursor, edit):
            return self._write_at(edit, row, col, text)
        self._append_command(_insert, 0)

    def goto_eol(self):
        def _goto_eol(cursor, edit):
            cursor = sublime.Region(self.target_view.line(cursor.a).end())
            self.target_view.sel().clear()
            self.target_view.sel().add(cursor)
            return cursor
        self._append_command(_goto_eol, 0)

    def goto(self, row, col):
        self.insert_at(row, col, '')

    def add_cursor(self, row, col):
        def _add_cursor(cursor, edit):
            return cursor
        self.insert_at(row, col, '')

    def set_mark(self, name=None, delay=None):
        if not name:
            name = '__tmp__'

        def _set_mark(cursor, edit):
            cursor_0 = self.target_view.line(cursor.begin()).a
            self._mark_offsets[name] = cursor.begin() - cursor_0
            if self._mark_offsets[name] == 0:
                self._mark_offsets[name] = 1
                cursor_0 -= 1
            self.target_view.add_regions('screencast_director_%s' % name, [sublime.Region(cursor_0, cursor_0)], 'source', '', sublime.HIDDEN)
            return cursor
        self._append_command(_set_mark, delay)

    def goto_mark(self, name=None, delay=None):
        if not name:
            name = '__tmp__'

        def _goto_mark(cursor, edit):
            cursors = self.target_view.get_regions('screencast_director_%s' % name)
            return cursors[0].a + self._mark_offsets[name]
        self._append_command(_goto_mark, delay)

    def select_from_mark(self, name=None, delay=None):
        if not self._mark_offsets:
            return

        if not name:
            name = '__tmp__'

        def _select_from_mark(cursor, edit):
            cursors = self.target_view.get_regions('screencast_director_%s' % name)
            a = cursors[0].a + self._mark_offsets[name]
            b = cursor.b
            return a, b
        self._append_command(_select_from_mark, delay)

    def clear_marks(self, delay=None):
        def _clear_marks(cursor, edit):
            for name in self._mark_offsets:
                self.target_view.erase_regions('screencast_director_%s' % name)
            self._mark_offsets = {}
            return cursor
        self._append_command(_clear_marks, delay)

    def run_command(self, command, args=None):
        def _run_command(cursor, edit):
            self.target_view.sel().add(cursor)
            if args is None:
                self.target_view.run_command(command)
            else:
                self.target_view.run_command(command, args)
            cursor = self.target_view.sel()[0]
            return cursor
        self._append_command(_run_command)

ScreencastDirector.the_director = ScreencastDirector()


class ScreencastDirectorBindSourceCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        window = sublime.active_window()
        source_view = ScreencastDirector.the_director.source_view = window.active_view()
        if source_view is not None:
            ScreencastDirector.the_director.index = 0

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
            if not blocks:
                sublime.status_message('ScreencastDirector could not parse commands.')
                return
            source_view.add_regions(
                'screencast_director',
                blocks,
                'source',
                '',
                sublime.DRAW_OUTLINED
                )

            sublime.status_message('Bound source view and set index to 0')
            ScreencastDirector.the_director._refresh_source()


class ScreencastDirectorCmdCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.what_to_do(edit)


class ScreencastDirectorBindTargetCommand(sublime_plugin.WindowCommand):
    def run(self):
        window = sublime.active_window()
        ScreencastDirector.the_director.target_view = window.active_view()
        sublime.status_message('Bound target view')
        ScreencastDirector.the_director._refresh_source()


class ScreencastDirectorPasteCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        target_view = self.view
        ScreencastDirector.the_director.target_view = target_view
        ScreencastDirector.the_director.write(sublime.get_clipboard(),
            delay_min=10,
            delay_max=20,
            )
        region = self.view.sel()[0]
        target_view.add_regions('screencast_director', [region], 'source', '', sublime.HIDDEN)
        ScreencastDirector.the_director._start_timer()


class ScreencastDirectorRunCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        window = sublime.active_window()
        source_view = ScreencastDirector.the_director.source_view
        target_view = ScreencastDirector.the_director.target_view
        if target_view is None:
            window.run_command('screencast_director_bind_target')
            target_view = ScreencastDirector.the_director.target_view

        if source_view is None:
            sublime.status_message('Choose your source view')
            return

        if target_view.id() == source_view.id():
            ScreencastDirector.the_director.target_view = None
            sublime.status_message('Choose your target view')
            return

        ScreencastDirector.the_director.command = self
        ScreencastDirector.the_director._run()
        ScreencastDirector.the_director.index += 1
        ScreencastDirector.the_director._refresh_source()
        sublime.status_message('Index is at {index}'.format(index=ScreencastDirector.the_director.index))


class ScreencastDirectorNextCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        if ScreencastDirector.the_director.source_view is None:
            window = sublime.active_window()
            window.run_command('screencast_director_bind_source')
        else:
            ScreencastDirector.the_director.index += 1
        ScreencastDirector.the_director._refresh_source()
        sublime.status_message('Index is at {index}'.format(index=ScreencastDirector.the_director.index))


class ScreencastDirectorPreviousCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        if ScreencastDirector.the_director.source_view is None:
            window = sublime.active_window()
            window.run_command('screencast_director_bind_source')
        else:
            ScreencastDirector.the_director.index -= 1
        ScreencastDirector.the_director._refresh_source()
        sublime.status_message('Index is at {index}'.format(index=ScreencastDirector.the_director.index))
