# PicoLuaFmt

A Lua code formatter for Pico-8 (http://www.pico-8.com/).


## Prerequisites

PicoLuaFmt requires Python 3 and nothing else. It is written as a
single source file to make it easy to keep around. (The additional
files are for automated tests. You only need the `picoluafmt.py`
file.)


## Usage

    python3 picoluafmt.py [ARGS] [FILENAME [FILENAME...]]

This tool reformats the Lua code in a Pico-8 or Lua source file. Its
main function is to adjust spacing and line breaks to make the code
easier to read. Depending on the original code, this may increase the
number of characters.

With the `--minify` option, the tool minimizes the number of
characters used by removing spacing and comments, and renaming
symbols. This may reduce the number of characters, but almost always
makes the code less readable.

In either mode, this does not change the number of Lua tokens.

The file can be a `.p8` file created by Pico-8, or it can be a `.lua`
file. This tool does not support `.p8.png` files.

When given one or more filenames of `.p8` or `.lua` source files, this
tool creates a new file for each with `_fmt` added before the prefix,
and overwrites it if it exists. If you provide the `--overwrite` flag,
this will overwrite the `.p8` or `.lua` source file directly and not
produce a `_fmt` file.

Example:

    python3 picoluafmt.py mygame.p8

This creates a file named `mygame_fmt.p8` with the same content and
formatted Lua source code.

You can also run the tool without filenames to provide Lua source on
standard input. The tool writes the formatted source to standard
output.


## History

v0.0 (2015 Sept 26): Doesn't work yet!
