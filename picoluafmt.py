#!/usr/bin/env python3
"""

Limitations:

* Does not support Lua long strings.

To do:

* Confirm Lua and Pico-8 behavior on multi-line strings.
* Implement formatted output.
* Implement minified output.
* Line length limiting and smart wrapping.
"""


import argparse
import os
import re
import sys
import tempfile
import textwrap


class Error(Exception):
    """Base class for local exceptions."""
    pass


class LexerError(Exception):
    """A lexer error."""
    def __init__(self, msg, lineno, charno):
        self.msg = msg
        self.lineno = lineno
        self.charno = charno
        
    def __str__(self):
        return '{} at line {} char {}'.format(
            self.msg, self.lineno, self.charno)

    
STRING_ESCAPES = {
    '\n': '\n', 'a': '\a', 'b': '\b', 'f': '\f', 'n': '\n',
    'r': '\r', 't': '\t', 'v': '\v', '\\': '\\', '"': '"',
    "'": "'"
}


class Token():
    """A token."""
    def __init__(self, data, lineno=None, charno=None):
        self.data = data
        self.lineno = lineno
        self.charno = charno

    def __repr__(self):
        return '{}<"{}" line {} char {}>'.format(
            self.__class__.__name__, self.data, self.lineno, self.charno)

    def __eq__(self, other):
        return ((self.__class__ == other.__class__) and
                (self.data == other.data))

    
class TokString(Token):
    """A string literal."""
    pass


class TokNumber(Token):
    """A string literal."""
    pass


class TokComment(Token):
    """A comment."""
    pass


class TokName(Token):
    """A name."""
    pass


class TokKeyword(Token):
    """A name."""
    pass


# A list of single-line token matching patterns and corresponding token
# classes. A token class of None causes the lexer to consume the pattern
# without emitting a token. The patterns are matched in order, and must
# appear in order of preference.
TOKEN_MATCHERS = []
TOKEN_MATCHERS.extend([
    (re.compile(r'--.*'), TokComment),
    (re.compile(r'\s+'), None)
])
TOKEN_MATCHERS.extend([
    (re.compile(r'\b'+keyword+r'\b'), TokKeyword) for keyword in [
    'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for',
    'function', 'if', 'in', 'local', 'nil', 'not', 'or', 'repeat', 'return',
    'then', 'true', 'until', 'while']])
TOKEN_MATCHERS.extend([
    (re.compile(symbol), TokKeyword) for symbol in [
    r'\+', '-', r'\*', '/', '%', r'\^', '#',
    '==', '~=', '!=', '<=', '>=', '<', '>', '=',
    r'\(', r'\)', '{', '}', r'\[', r'\]', ';', ':', ',',
    r'\.\.\.', r'\.\.', r'\.']])
TOKEN_MATCHERS.extend([
    (re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*'), TokName),
    (re.compile(r'0[xX][0-9a-fA-F]+'), TokNumber),
    (re.compile(r'[0-9]+(\.[0-9]+)?([eE]-?[0-9]+)?'), TokNumber)])

    
class LuaParser():
    """The Lua parser and formatter.

    To use, construct the parser, then call the process_line() method
    for each line of Lua source. Once a complete Lua source file has
    been processed, you can call one of the write_*() methods to
    generate formatted output. Calling a write_*() method when the
    lines that have been processed do not represent a complete and
    valid Lua code unit is an error.
    """

    def __init__(self):
        """The initializer."""
        self._tokens = []
        self._cur_lineno = 0
        self._cur_charno = 0

        # If in a string literal, the pos of the start of the string.
        self._in_string_lineno = None
        self._in_string_charno = None
        # If in a string literal, a list of chars. Else None.
        self._in_string = None
        # If in a string literal, the starting delimiter, either " or '.
        # Else None.
        self._in_string_delim = None
        
    def _process_token(self, s):
        """Process a token's worth of chars from a string, if possible.

        If a token is found, it is added to self._tokens. A call might
        process characters but not emit a token.

        Args:
          s: The string to process.

        Returns:
          The number of characters processed from the beginning of the string.
        """
        i = 0
        
        if self._in_string is not None:
            # Continue string literal.
            while i < len(s):
                c = s[i]

                if c == self._in_string_delim:
                    # End string literal.
                    self._tokens.append(
                        TokString(str(''.join(self._in_string)),
                                  self._in_string_lineno,
                                  self._in_string_charno))
                    self._in_string_delim = None
                    self._in_string_lineno = None
                    self._in_string_charno = None
                    self._in_string = None
                    i += 1
                    break
                
                if c == '\\':
                    # Escape character.
                    num_m = re.match(r'\d{1,3}', s[i+1:])
                    if num_m:
                        c = chr(int(num_m.group(0)))
                        i += len(num_m.group(0))
                    else:
                        next_c = s[i+1]
                        if next_c in STRING_ESCAPES:
                            c = STRING_ESCAPES[next_c]
                            i += 1
                            
                self._in_string.append(c)
                i += 1

        elif s.startswith("'") or s.startswith('"'):
            # Begin string literal.
            self._in_string_delim = s[0]
            self._in_string_lineno = self._cur_lineno
            self._in_string_charno = self._cur_charno
            self._in_string = []
            i = 1

        else:
            # Match one-line patterns.
            for (pat, tok_class) in TOKEN_MATCHERS:
                m = pat.match(s)
                if m:
                    if tok_class is not None:
                        token = tok_class(m.group(0),
                                          self._cur_lineno,
                                          self._cur_charno)
                        self._tokens.append(token)
                    i = len(m.group(0))
                    break

        for c in s[:i]:
            if c == '\n':
                self._cur_lineno += 1
                self._cur_charno = 0
            else:
                self._cur_charno += 1
        return i

    def process_line(self, line):
        """Processes a line of Lua source code.

        The line does not have to be a complete Lua statement or
        block. However, complete and valid code must have been
        processed before you can call a write_*() method.

        Args:
          line: The line of Lua source.
        """
        i = -1
        while i != 0:
            i = self._process_token(line)
            line = line[i:]
        if line:
            raise LexerError('Syntax error (remaining:%r)' % (line,),
                             self._cur_lineno + 1,
                             self._cur_charno + 1)

    def write_minified(self, outstr):
        """Writes a minified version of the processed Lua source to an output
        stream.

        Args:
          outstr: The output stream to which the minified source code is
            written.

        Returns:
          The number of characters written to outstr.
        """
        # TODO: implement this
        for tok in self._tokens:
            outstr.write(str(tok))
        return len(self._tokens)

    def write_formatted(self, outstr, indent_width=2):
        """Writes a formatted version of the processed Lua source to an output
        stream.

        Args:
          outstr: The output stream to which the formatted source code is
            written.
          indent_width: The indent width to use for the formatted output, as
            a number of spaces.

        Returns:
          The number of characters written to outstr.
        """
        # TODO: implement this
        for tok in self._tokens:
            outstr.write(str(tok))
        return len(self._tokens)

    
class BadP8Error(Error):
    """Exception for invalid .p8 file input."""
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return 'Invalid .p8: ' + self.msg

    
def process(instr, outstr,
            expect_p8=False, minify=False,
            indent_width=2):
    """Process a Pico-8 or Lua source file.

    Args:
      instr: The input byte stream containing the file to process.
      outstr: The output byte stream to write the processed file.
      expect_p8: If True, instr is expected to contain a complete .p8
        source file, including Lua source and other game data. The game
        data will be written verbatim to outstr, with the Lua section
        processed. If False, instr is expected to contain only Lua code,
        and only the processed Lus will be written to outstr.
      minify: If True, minified Lua is written to outstr. Otherwise,
        formatted Lua is written to outstr.
      indent_width: The indent width to use for formatted Lua, as a
        number of spaces. (Ignored when minifying.)

    Returns:
      A tuple containing the character counts of the original source
      and the new (formatted or minified) source.

    Raises:
      BadP8Error: expect_p8 was True and instr contained data that was not
        recognized as a valid .p8 file.
    """
    # TODO: Pico-8 source files are small enough to load into
    # memory. Maybe skip all this line reading garbage and just
    # pattern match on the entire string.
    # TODO: Consider a generator-based approach to lines->lexer->parser.
    
    if expect_p8:
        # Validate header.
        header = [instr.readline(), instr.readline()]
        first_m = re.match(
            r'pico-8 cartridge // http://www.pico-8.com\n',
            header[0])
        if not first_m:
            raise BadP8Error('invalid header')
        version_m = re.match(
            r'version (.*)\n',
            header[1])
        if not version_m:
            raise BadP8Error('invalid header')
        p8_version = version_m.group(1)
        outstr.write(header[0])
        outstr.write(header[1])

        # Copy up to __lua__ section.
        while True:
            line = instr.readline()
            outstr.write(line)
            if not line or re.match(r'__lua__\n', line):
                break
        if not line:
            raise BadP8Error('no __lua__ section')

    lua_parser = LuaParser()
    orig_char_count = 0
    while True:
        line = instr.readline()
        if not line or (expect_p8 and re.match(r'__\w+__\n', line)):
            break
        lua_parser.process_line(line)
        orig_char_count += len(line)
    if minify:
        new_char_count = lua_parser.write_minified(
            outstr)
    else:
        new_char_count = lua_parser.write_formatted(
            outstr, indent_width=indent_width)

    if expect_p8:
        # Write first post-__lua__ section line, if any.
        outstr.write(line)
        
        # Copy to end of .p8 file.
        while line:
            line = instr.readline()
            outstr.write(line)

    return (orig_char_count, new_char_count)


quiet = False
write_stream = sys.stdout
error_stream = sys.stderr


def write(msg):
    """Writes a message to the user.

    Messages written with this function can be suppressed by the user
    with the --quiet argument.

    When working with named files, this function writes to
    stdout. When working with stdin, file output goes to stdout and
    messages go to stderr.

    Args:
      msg: The message to write.

    """
    if not quiet:
        write_stream.write(msg)


def error(msg):
    """Writes an error message to the user.

    All error messages are written to stderr.

    Args:
      msg: The error message to write.
    """
    error_stream.write(msg)


def get_argparser():
    """Builds and returns the argument parser."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''
        Formats Pico-8 Lua code.

        Usage:
          python3 picoluafmt.py [ARGS] [FILENAME [FILENAME...]]

        This tool reformats the Lua code in a Pico-8 or Lua source
        file. Its main function is to adjust spacing and line breaks
        to make the code easier to read. Depending on the original
        code, this may increase the number of characters.

        With the --minify option, the tool minimizes the number of
        characters used by removing spacing and comments, and renaming
        symbols. This may reduce the number of characters, but almost
        always makes the code less readable.

        In either mode, this does not change the number of Lua tokens.

        The file can be a .p8 file created by Pico-8, or it can be a
        .lua file. This tool does not support .p8.png files.

        When given one or more filenames of .p8 or .lua source files,
        this tool creates a new file for each with "_fmt" added before
        the prefix, and overwrites it if it exists. If you provide the
        --overwrite flag, this will overwrite the .p8 or .lua source
        file directly and not produce a _fmt file.

        Example:
          python3 picoluafmt.py mygame.p8

        This creates a file named "mygame_fmt.p8" with the same
        content and formatted Lua source code.

        You can also run the tool without filenames to provide Lua
        source on standard input. The tool writes the formatted source
        to standard output.
        '''))
    parser.add_argument(
        'filename', type=str, nargs='*',
        help='the names of files to process')
    parser.add_argument(
        '--indentwidth', type=int, action='store', default=2,
        help='the indent width as a number of spaces')
    parser.add_argument(
        '--overwrite', action='store_true',
        help='given a filename, overwrites the original file instead of '
        'creating a separate *_fmt.p8 file')
    parser.add_argument(
        '--minify', action='store_true',
        help='minifies the code instead of formatting it')
    parser.add_argument(
        '-q', '--quiet', action='store_true',
        help='suppresses inessential messages')

    return parser


def main(orig_args):
    """The main routine.

    Args:
      orig_args: The unprocessed command line arguments, not including the
        program name.
    """
    global quiet, write_stream
    
    args = get_argparser().parse_args(args=orig_args)
    quiet = args.quiet

    has_errors = False

    if not args.filename:
        # Use stdin for input, stdout for output, and stderr for all messages.

        write_stream = sys.stderr
        (oc, nc) = process(
            sys.stdin, sys.stdout,
            expect_p8=True,
            minify=args.minify,
            indent_width=args.indentwidth)
        
        # Pico-8 does not count the final newline as a character, so we
        # subtract 1 from char count reports.
        write('Done. {} chars -> {} chars\n'.format(oc-1, nc-1))

    else:
        # Read named files for input, write to named files for output.
        
        for filename in args.filename:
            if not filename.endswith('.p8') and not filename.endswith('.lua'):
                error('{}: file must be a .p8 or .lua file\n'.format(filename))
                has_errors = True
                continue
            
            expect_p8 = True
            if args.overwrite:
                new_fname = filename
            elif filename.endswith('.p8'):
                new_fname = filename[:-3] + '_fmt.p8'
            elif filename.endswith('.lua'):
                new_fname = filename[:-4] + '_fmt.lua'
                expect_p8 = False
            try:
                tempname = None
                with tempfile.NamedTemporaryFile(
                        mode='wt', delete=False) as out_file:
                    tempname = out_file.name
                    with open(filename) as orig_file:
                        (oc, nc) = process(
                            orig_file, out_file,
                            expect_p8=expect_p8,
                            minify=args.minify,
                            indent_width=args.indentwidth)
                if os.path.exists(new_fname):
                    write('{}: overwriting {}\n'.format(filename, new_fname))
                os.replace(tempname, new_fname)

                # Pico-8 does not count the final newline as a character, so we
                # subtract 1 from char count reports.
                write('{} ({} chars) -> {} ({} chars)\n'.format(
                    filename, oc-1, new_fname, nc-1))

            except Error as e:
                has_errors = True
                error('{}: {}'.format(filename, str(e)))

    if has_errors:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
