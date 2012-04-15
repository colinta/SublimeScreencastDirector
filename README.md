ScreencastDirector for Sublime Text 2
======================================

An `ApplicationCommand` that can be used to direct a screencast.  Allows for interactivity, too, so
you can automate some tasks, and manually do others.  Mimics typing, and if you get nitty-gritty,
it can mimic all your ST2 commands.

Installation
------------

1. Using Package Control, install "ScreencastDirector"

Or:

1. Open the Sublime Text 2 Packages folder

    - OS X: ~/Library/Application Support/Sublime Text 2/Packages/
    - Windows: %APPDATA%/Sublime Text 2/Packages/
    - Linux: ~/.Sublime Text 2/Packages/

2. clone this repo

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
