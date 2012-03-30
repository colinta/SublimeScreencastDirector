ScreencastDirectory for Sublime Text 2
======================================

An `ApplicationCommand` that can be used to direct a screencast.  Allows for interactivity, too, so
you can automate some tasks, and manually do others.  Mimics typing, and if you get nitty-gritty,
it can mimic all your ST2 commands.

Installation
------------

1. Using Package Control, install "ScreencastDirectory"

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
* `screencast_director_run`: Run current command and move cursor to the next command.
* `screencast_director_previous`: Moves the "command cursor" backward.
* `screencast_director_next`: Moves the "command cursor" forward.