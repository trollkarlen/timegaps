# -*- coding: utf-8 -*-
# Copyright 2014 Jan-Philip Gehrcke. See LICENSE file for details.

from __future__ import unicode_literals
import os
import sys
import logging
from py.test import raises, mark
from clitest import CmdlineInterfaceTest, CmdlineTestError, WrongExitCode

sys.path.insert(0, os.path.abspath('..'))
from timegaps import __version__


RUNDIRTOP = "./cmdline-test"
TIMEGAPS_NAME = "../../../timegaps.py"
PYTHON_EXE = "python"
WINDOWS = sys.platform == "win32"


class CmdlineInterfaceTestUnix(CmdlineInterfaceTest):
    rundirtop = RUNDIRTOP
    # Set PYTHONIOENCODING. When connected to pipes (as in the context of
    # py.test, sys.stdout.encoding is None otherwise.)
    preamble = 'export PYTHONIOENCODING="utf-8"\n'


class CmdlineInterfaceTestWindows(CmdlineInterfaceTest):
    shellpath = "cmd.exe"
    # Execute command (/C) and turn off echo (prompt etc, /Q).
    shellargs = ["/Q", "/C"]
    rundirtop = RUNDIRTOP
    shellscript_ext = ".bat"
    # Use PYTHONIOENCODING for enforcing stdout encoding UTF-8 on
    # Windows. I also set console code page via @chcp 65001, but
    # according to Stinner this is buggy (not fully analogue to utf-8,
    # http://bugs.python.org/issue1602). Good news: independent of the
    # console code page set, the stdout of the console is the unmodified
    # Python stdout bytestream, which is forced to be UTF-8 via
    # environment variable anyway. Nevertheless, @chcp 65001 is required
    # for special char command line arguments to be properly passed to Python
    # (with the Win 32 sys.argv hack on the receiving end, sys.argv becomes
    # populated with unicode objects).
    preamble = "@chcp 65001 > nul\n@set PYTHONIOENCODING=utf-8\n"


CLITest = CmdlineInterfaceTestUnix
if WINDOWS:
    CLITest = CmdlineInterfaceTestWindows


logging.basicConfig(
    format='%(asctime)s,%(msecs)-6.1f %(funcName)s# %(message)s',
    datefmt='%H:%M:%S')
log = logging.getLogger()
log.setLevel(logging.DEBUG)


class Base(object):
    """Implement methods shared by all test classes.
    """

    def setup_method(self, method):
        testname = "%s_%s" % (type(self).__name__, method.__name__)
        print("\n\n%s" % testname)
        self.cmdlinetest = CLITest(testname)

    def teardown_method(self, method):
        pass
        #self.cmdlinetest.clear()

    def run(self, arguments_unicode, rc=0):
        cmd = "%s %s %s" % (PYTHON_EXE, TIMEGAPS_NAME, arguments_unicode)
        log.info("Test command:\n%s" % cmd)
        self.cmdlinetest.run(cmd_unicode=cmd, expect_rc=rc)
        return self.cmdlinetest


class TestSimpleErrors(Base):
    """Test for basic error detection and proper error messages.
    """

    def test_too_few_args(self):
        # argparse ArgumentParser.error() makes program exit with code 2
        # on Unix. On Windows, it seems to be 1.
        t = self.run("", rc=2)
        t.assert_in_stderr("too few arguments")

    def test_valid_rules_missing_item_cmdline(self):
        # TODO: also test missing item / valid rules for stdin mode.
        t = self.run("days5", rc=1)
        t.assert_in_stderr("one item must be provided (if --stdin not set")

    def test_invalid_rulesstring_missing_item(self):
        # Rules are checked first, error must indicate invalid rules.
        t = self.run("bar", rc=1)
        t.assert_in_stderr(["Invalid", "token", "bar"])

    def test_empty_rulesstring(self):
        # Rules are checked first, error must indicate invalid rules.
        t = self.run('""', rc=1)
        t.assert_in_stderr("Token is empty")

    def test_invalid_rulesstring_category(self):
        # Rules are checked first, error must indicate invalid rules.
        t = self.run('peter5', rc=1)
        t.assert_in_stderr(["Time category", "invalid"])

    def test_invalid_rulesstring_wrong_item(self):
        # Rules are checked first, error must indicate invalid rules.
        t = self.run("foo nofile", rc=1)
        t.assert_in_stderr(["Invalid", "token", "foo"])

    def test_invalid_itempath_1(self):
        t = self.run("days5 nofile", rc=1)
        t.assert_in_stderr(["nofile", "Cannot access"])

    def test_invalid_itempath_2(self):
        t = self.run("days5 . nofile", rc=1)
        t.assert_in_stderr(["nofile", "Cannot access"])

    def test_move_missingarg(self):
        t = self.run("--move", rc=2)
        t.assert_no_stdout()
        t.assert_in_stderr(["--move", "expected", "argument"])

    def test_excl_delete_move(self):
        t = self.run("--delete --move DIR", rc=2)
        t.assert_no_stdout()
        t.assert_in_stderr(["--move", "--delete", "not allowed with"])


class TestSimplestFilterFeatures(Base):
    """Test minimal working invocation signature that filters files.
    """
    def test_accept_cwd(self):
        # Test CWD should *just* have been created, so it's recent-accepted.
        # All accepted means no stdout. No verbosity means no stderr.
        t = self.run("recent10 .")
        t.assert_no_stdout()
        t.assert_no_stderr()

    def test_reject_cwd(self):
        # Test CWD should *just* have been created, so it's years-rejected.
        t = self.run("years1 .")
        t.assert_is_stdout(".\n")
        t.assert_no_stderr()


class TestArgparseLogic(Base):
    """Make sure that argparse is set up properly (and works as exepected).
    """
    def test_version(self):
        t = self.run("--version")
        # argparse makes this go to stderr, weird, help goes to stdout.
        t.assert_no_stdout()
        t.assert_is_stderr("%s\n" % __version__)

    def test_help(self):
        t = self.run("--help")
        t.assert_in_stdout(["usage","RULES","ITEM"])
        t.assert_no_stderr()


class TestSpecialChars(Base):
    """Tests of all classes, involving Unicode challenges.
    """
    def test_invalid_rulesstring_smiley(self):
        t = self.run("☺", rc=1)
        t.assert_in_stderr(["Invalid", "token", "☺"])

