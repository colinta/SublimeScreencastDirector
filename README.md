ScreencastDirector
==================

An `ApplicationCommand` that can be used to direct a screencast.  Allows for interactivity, too, so
you can automate some tasks, and manually do others.  Mimics typing, and if you get nitty-gritty,
it can mimic all your ST2 commands.

Installation
------------

1. Using Package Control, install "ScreencastDirector"

Or:

1. Open the Sublime Text Packages folder
    - OS X: ~/Library/Application Support/Sublime Text 3/Packages/
    - Windows: %APPDATA%/Sublime Text 3/Packages/
    - Linux: ~/.Sublime Text 3/Packages/ or ~/.config/sublime-text-3/Packages

2. clone this repo
3. Install keymaps for the commands (see Example.sublime-keymap for my preferred keys)

### Sublime Text 2

1. Open the Sublime Text 2 Packages folder
2. clone this repo, but use the `st2` branch

       git clone -b st2 git@github.com:colinta/SublimeScreencastDirector

Commands
--------

* `screencast_bind_source`: Establishes the current window as the "director"
* `screencast_bind_target`: Establishes the current window as the "screencast"
* `screencast_director_run`: Run current command and move "command cursor" to the next command.
* `screencast_director_previous`: Moves the "command cursor" backward.
* `screencast_director_next`: Moves the "command cursor" forward.

Director Commands and Examples
------------------------------

`write(*what_to_write)`: This will write some text with a *slightly* random
delay, to give the appearance of a human typing.  Accepts multiple arguments,
and inserts a newline between each argument.

```yaml
- write: ['line one', 'line two', 'line three']
```

`delay`: Pauses, default is .1 sec.  Used in `write` to simulate typing, but
  also useful in director scripts.

```yaml
- delay: 1500  # pause for 1.5 secs
```

`write_inside`: SublimeText prints matching quotes, and I wanted to simulate
  that in my screencasts.  This command makes it easy:

```yaml
- write_inside: "'string in single quotes'"
- write_inside: ["'", "again, using array", "'"]
- write_inside:
    - \'
    - write: you can nest commands, too!
    - \'
```

`go`: Move the cursor forward or backward by `N` letters.

```yaml
- go: -10  # go back ten
- write: HI!
- go: 10  # return to previous position
```

`select_all`: self-explanatory

```yaml
- select_all
```

`delete`: removes selected text

```yaml
- delete
```

`clear`: `select_all`, `delete`, and `clear_marks`

```yaml
- clear
```

`set_mark`: Sets a mark, so you can return somewhere after some crazy commands.
`goto_mark`: Returns cursor to previous saved position.

a "name" is optional, and defaults to `__tmp__`

```yaml
- set_mark  # same as set_mark: __tmp__
- set_mark: my_mark_name
- goto_mark  # same as goto_mark: __tmp__
- goto_mark: my_mark_name
```

`select_from_mark`: Selects from the mark to the position of the cursor.  Uses
the same names (default: __tmp__) as `set_mark`/`goto_mark`.

```yaml
- set_mark
- write: "this will be deleted in one second"
- delay: 1000
- select_from_mark
- delete
```

`run_command`: Run any SublimeText command!  You can do almost anything using
this one, so if you are tempted to create a new command, consider using this one
instead.

```yaml
- write: "I will fix this mitsake."
- delay: 500
- go: -5
- delay: 500
- run_command: [transpose_character]
```

Writing Director Commands
-------------------------

I am totally open to pull requests that add more director functions!  They are
just a *teensy* bit hard to understand at first if you're just looking at the
source code.  So here goes.

The `ScreencastDirector` class is the class that contains all the commands that
can be used in your `director.yaml` files.  An instance of the
`ScreencastDirector` class is created when the plugin is loaded (`the_director`
if you're following along in the source).

The entries in your YAML source file are "executed" when you run the
`screencast_director_run` command, which pretty much delegates the work to
`ScreencastDirector._run`.  All the entries are "executed" immediately, which is
to say that the command queue is built up at this time.

Let me say this more clearly: ScreencastDirector methods add one or more
functions to the command queue, based on the contents of an entry in your YAML
file.

When you add a command to the queue, you can pass in the `delay` parameter to
control timing.  Here is the `delay` command, which is the simplest of all:

```python
def delay(self, delay=100):
    def _delay(cursor, e):
        pass
    self._append_command(_delay, delay)
```

We don't even need to "sleep" in the command - that's taken care of by passing
the `delay` parameter to `_append_command`.  We did have to accept the `cursor`
and `e` arguments.  If you make a change to the position of the cursor, you must
return that new location (or selection).  The `e` argument is a `sublime.Edit`
object.  Since most commands will need to make a change of some sort, it is
provided for convenience.

Let's look at a simplified version of `write`.  It "types" each letter of input,
with a random delay between each letter to imitate actual typing.  We will need
to call `target_view.replace` to insert the text (if a previous command makes a
selection, this command will overwrite it), and then return our new cursor
location.

```python
def write(self, what_to_write):
    def _write_letter(letter):
        def _write(cursor, e):
            self.target_view.replace(e, cursor, letter)
            return cursor.a + len(letter)
        return _write

    for letter in what_to_write:
        delay = random.randrange(50, 200)
        self._append_command(_write_letter(letter), delay=delay)
```

The actual implementation does much more - it supports multiple arguments, and
if the argument "looks like" a command, it will execute that entry (aka "add
those commands to the queue" - remember, an entry adds commands to the queue).

For your commands, just remember:

- For every edit, create a new function and add it to the queue using
  `_append_command`.  It is common to accept a `delay` argument from the YAML
  source.
- The actual command accepts two arguments: `cursor` (a `sublime.Region`
  object), and `edit` (a `sublime.Edit` object).  Other than that, you
  should use the arguments that were passed in from the source file.

If you're having trouble, create an [issue][issues] and I'll take a look.

Examples
--------

These are all silent films, which is just my preference.  Any screen recording
app can take audio, and you can actually sit back and read your script while
ScreencastDirector does all the typing — typo free!

<http://colinta.com/projects/move_text.html>
<http://colinta.com/projects/transpose_character.html>
<http://colinta.com/projects/bracketeer.html>
<http://colinta.com/projects/quick_find.html>

Even ScreencastDirector itself!

<http://colinta.com/projects/screencast_director.html>

Unfortunately, I didn't save the transcripts for most of these... I usually just
use a scratch document.  I *recommend* that you do as I say and not as I do:
save your transcripts!  It is useful when you realize there was a mistake and
need to rerecord the video.  Here is the director.yaml file for
[ScreencastDirector][]: <https://github.com/colinta/SublimeScreencastDirector/blob/master/director.yaml>

[issues]: https://github.com/colinta/SublimeScreencastDirector/issues
[ScreencastDirector]: http://colinta.com/projects/screencast_director.html
