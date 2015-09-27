#!/usr/bin/env python3

import io
import os
import shutil
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import Mock
from unittest.mock import patch

import picoluafmt


VALID_P8_HEADER = b'''pico-8 cartridge // http://www.pico-8.com
version 4
'''

INVALID_P8_HEADER = b'''INVALID HEADER
INVALID HEADER
'''

VALID_P8_LUA_SECTION_HEADER = b'__lua__\n'

VALID_P8_FOOTER = (
    '\n__gfx__\n' + (('0' * 128) + '\n') * 128 +
    '__gff__\n' + (('0' * 256) + '\n') * 2 +
    '__map__\n' + (('0' * 256) + '\n') * 32 +
    '__sfx__\n' + '0001' + ('0' * 164) + '\n' +
    ('001' + ('0' * 165) + '\n') * 63 +
    '__music__\n' + '00 41424344\n' * 64 + '\n\n').encode()

VALID_LUA = b'''
v1 = nil
v2 = false
v3 = true
v4 = 123
v5 = 123.45
v6 = "string"
v7 = 7 < 10
v8 = -12
v9 = not false

func()
v10 = func(1, v3, "string")

v11 = { "Monday", "Tuesday", "Wednesday",
        "Thursday", "Friday", "Saturday",
        "Sunday" }
v12 = v11[3]

v13 = {}
v13.x = 100
v13.y = 200
v13["z"] = 300

do
 func()
 v2 = not v3
end

-- Comment
-- do
--  func()
--  v2 = not v3

counter = 10  -- end of line comment
while counter > 0 do
 counter -= 1
 if counter % 2 == 0 then
  func()
 end
 if func(counter) > 900 then
  break
 end
end

repeat
 counter += 1
 if counter % 2 == 0 then
  func()
 end
until counter == 10

if v4 > 0 then
 func(1)
elseif v5 and (v4 < 0) then
 func(-2)
elseif v4 < 0 then
 func(-1)
else
 func(0)
end

for x = 1,10,2 do
 func(x)
 if x % 2 == 0 then
  func(x+1)
 end
end

for x,y,z in foobar do
 func(x)
 if x % 2 == 0 then
  func(x+1)
 end
end

function func(x, y, z)
 local foobar = 999
 if x % 2 == 0 then
  func(x+1)
 end
 return 111
end

local function func2(x, y, z)
 if x % 2 == 0 then
  func(x+1)
 end
end

a = {"hello", "blah"}
add(a, "world")
del(a, "blah")
print(count(a)) -- 2

for item in all(a) do print(item) end
foreach(a, print)
foreach(a, function(i) print(i) end)

x = 1 y = 2 print(x+y) -- this line will run ok

-- Pico-8 shorthand
if (not b) i=1 j=2
a += 2
a -= 2
a *= 2
a /= 2
a %= 2
if (a != 2) print("ok") end
if (a ~= 2) print("ok") end

'''


class TestLuaParser(unittest.TestCase):
    # TODO: implement this
    pass


@patch.object(picoluafmt.LuaParser, 'process_line')
@patch.object(picoluafmt.LuaParser, 'write_formatted')
@patch.object(picoluafmt.LuaParser, 'write_minified')
class TestProcessStream(unittest.TestCase):
    def testProcessEmptyLua(self, mock_write_minified, mock_write_formatted, mock_process_line):
        outstr = io.BytesIO()
        (oc, nc) = picoluafmt.process(
            io.BytesIO(b''),
            outstr
        )
        mock_process_line.assert_not_called()
        mock_write_formatted.assert_called_once_with(
            outstr, indent_width=2)
        mock_write_minified.assert_not_called()

    def testProcessLua(self, mock_write_minified, mock_write_formatted, mock_process_line):
        outstr = io.BytesIO()
        (oc, nc) = picoluafmt.process(
            io.BytesIO(VALID_LUA),
            outstr
        )
        self.assertTrue(mock_process_line.called)
        mock_write_formatted.assert_called_once_with(
            outstr, indent_width=2)
        mock_write_minified.assert_not_called()
        
    def testProcessLuaMinify(self, mock_write_minified, mock_write_formatted, mock_process_line):
        outstr = io.BytesIO()
        (oc, nc) = picoluafmt.process(
            io.BytesIO(VALID_LUA),
            outstr,
            minify=True
        )
        self.assertTrue(mock_process_line.called)
        mock_write_minified.assert_called_once_with(
            outstr)
        mock_write_formatted.assert_not_called()
        
    def testProcessLuaIndentWidth(self, mock_write_minified, mock_write_formatted, mock_process_line):
        outstr = io.BytesIO()
        (oc, nc) = picoluafmt.process(
            io.BytesIO(VALID_LUA),
            outstr,
            indent_width=7
        )
        self.assertTrue(mock_process_line.called)
        mock_write_formatted.assert_called_once_with(
            outstr, indent_width=7)
        mock_write_minified.assert_not_called()
        
    def testProcessP8EmptyLua(self, mock_write_minified, mock_write_formatted, mock_process_line):
        outstr = io.BytesIO()
        (oc, nc) = picoluafmt.process(
            io.BytesIO(VALID_P8_HEADER +
                        VALID_P8_LUA_SECTION_HEADER +
                        VALID_P8_FOOTER),
            outstr,
            expect_p8=True
        )
        mock_write_formatted.assert_called_once_with(
            outstr, indent_width=2)
        mock_write_minified.assert_not_called()
        self.assertIn(b'__gfx__\n', outstr.getvalue())

    def testProcessP8(self, mock_write_minified, mock_write_formatted, mock_process_line):
        outstr = io.BytesIO()
        (oc, nc) = picoluafmt.process(
            io.BytesIO(VALID_P8_HEADER +
                        VALID_P8_LUA_SECTION_HEADER +
                        VALID_LUA +
                        VALID_P8_FOOTER),
            outstr,
            expect_p8=True
        )
        mock_write_formatted.assert_called_once_with(
            outstr, indent_width=2)
        mock_write_minified.assert_not_called()
        self.assertIn(b'__gfx__\n', outstr.getvalue())
        
    def testErrorP8InvalidHeader(self, mock_write_minified, mock_write_formatted, mock_process_line):
        outstr = io.BytesIO()
        self.assertRaises(
            picoluafmt.BadP8Error,
            picoluafmt.process,
            io.BytesIO(INVALID_P8_HEADER +
                        VALID_P8_LUA_SECTION_HEADER +
                        VALID_LUA +
                        VALID_P8_FOOTER),
            outstr,
            expect_p8=True
        )
        
    def testErrorP8MissingLua(self, mock_write_minified, mock_write_formatted, mock_process_line):
        outstr = io.BytesIO()
        self.assertRaises(
            picoluafmt.BadP8Error,
            picoluafmt.process,
            io.BytesIO(VALID_P8_HEADER +
                        VALID_P8_FOOTER),
            outstr,
            expect_p8=True
        )

class BufferStreamWrapper():
    def __init__(self):
        self.buffer = io.BytesIO()

@patch('picoluafmt.process', return_value=(111, 222))
@patch('picoluafmt.write')
@patch('picoluafmt.error')
class TestMain(unittest.TestCase):
    def setUp(self):
        testdata_path = os.path.join(os.path.dirname(__file__), 'testdata')
        self.tempdir = tempfile.mkdtemp()
        shutil.copytree(testdata_path, os.path.join(self.tempdir, 'testdata'))
        self.cwd = os.getcwd()
        
    def tearDown(self):
        shutil.rmtree(self.tempdir)
        os.chdir(self.cwd)

    @patch('sys.stdout', new_callable=io.StringIO)
    def testMainDisplaysHelp(
            self, mock_stdout, mock_error, mock_write, mock_process):
        try:
            picoluafmt.main(['-h'])
        except SystemExit:
            pass
        picoluafmt.process.assert_not_called()
        self.assertIn('Usage:', mock_stdout.getvalue())
    
    @patch('sys.stdin', new_callable=BufferStreamWrapper)
    @patch('sys.stdout', new_callable=BufferStreamWrapper)
    def testMainProcessesStdin(
            self, mock_stdout, mock_stdin,
            mock_error, mock_write, mock_process):
        status = picoluafmt.main([])
        self.assertEqual(0, status)
        mock_process.assert_called_once_with(
            mock_stdin.buffer, mock_stdout.buffer,
            expect_p8=True, minify=False,
            indent_width=2)

    def testMainProcessesOneP8File(
            self, mock_error, mock_write, mock_process):
        status = picoluafmt.main(
            [os.path.join(self.tempdir, 'testdata', 't1.p8')])
        self.assertEqual(0, status)
        self.assertTrue(os.path.exists(
            os.path.join(self.tempdir, 'testdata', 't1_fmt.p8')))
        self.assertTrue(mock_process.call_args[1]['expect_p8'])

    def testMainProcessesOneLuaFile(
            self, mock_error, mock_write, mock_process):
        status = picoluafmt.main(
            [os.path.join(self.tempdir, 'testdata', 't1.lua')])
        self.assertEqual(0, status)
        self.assertTrue(os.path.exists(
            os.path.join(self.tempdir, 'testdata', 't1_fmt.lua')))
        self.assertFalse(mock_process.call_args[1]['expect_p8'])

    def testMainProcessesMultipleFiles(
            self, mock_error, mock_write, mock_process):
        status = picoluafmt.main([
            os.path.join(self.tempdir, 'testdata', 't1.p8'),
            os.path.join(self.tempdir, 'testdata', 't1.lua'),
            os.path.join(self.tempdir, 'testdata', 't2.p8'),
            os.path.join(self.tempdir, 'testdata', 't3.p8')
        ])
        self.assertEqual(0, status)
        self.assertTrue(os.path.exists(
            os.path.join(self.tempdir, 'testdata', 't1_fmt.p8')))
        self.assertTrue(os.path.exists(
            os.path.join(self.tempdir, 'testdata', 't1_fmt.lua')))
        self.assertTrue(os.path.exists(
            os.path.join(self.tempdir, 'testdata', 't2_fmt.p8')))
        self.assertTrue(os.path.exists(
            os.path.join(self.tempdir, 'testdata', 't3_fmt.p8')))
        self.assertEqual(4, mock_process.call_count)

    def testMainProcessesOneFileQuietly(
            self, mock_error, mock_write, mock_process):
        status = picoluafmt.main([
            '-q',
            os.path.join(self.tempdir, 'testdata', 't1.p8')])
        self.assertEqual(0, status)
        self.assertTrue(os.path.exists(
            os.path.join(self.tempdir, 'testdata', 't1_fmt.p8')))
        self.assertTrue(picoluafmt.quiet)

    def testMainProcessesOneFileWithIndentWidth(
            self, mock_error, mock_write, mock_process):
        status = picoluafmt.main([
            '--indentwidth', '7',
            os.path.join(self.tempdir, 'testdata', 't1.p8')])
        self.assertEqual(0, status)
        self.assertTrue(os.path.exists(
            os.path.join(self.tempdir, 'testdata', 't1_fmt.p8')))
        self.assertEqual(7, mock_process.call_args[1]['indent_width'])

    def testMainProcessesOneFileWithOverwrite(
            self, mock_error, mock_write, mock_process):
        status = picoluafmt.main([
            '--overwrite',
            os.path.join(self.tempdir, 'testdata', 't1.p8')])
        self.assertEqual(0, status)
        self.assertFalse(os.path.exists(
            os.path.join(self.tempdir, 'testdata', 't1_fmt.p8')))

    def testMainErrorsBadP8File(
            self, mock_error, mock_write, mock_process):
        mock_process.side_effect = picoluafmt.BadP8Error('test error')
        status = picoluafmt.main([
            os.path.join(self.tempdir, 'testdata', 'bad_p8.p8')])
        self.assertEqual(1, status)


if __name__ == '__main__':
    unittest.main()
