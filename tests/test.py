# To run the tests:
#    1. Install Sublime Text plugin: https://sublime.wbond.net/packages/UnitTesting
#    2. Open the Command Palette and run "UnitTesting: Run any project test suite"
#    3. Enter "SassBeautify"

import sublime, sys, textwrap
from unittest import TestCase

# st2
if sublime.version() < '3000':
   SassBeautifyCommand = sys.modules["SassBeautify"].SassBeautifyCommand;
# st3
else:
   SassBeautifyCommand = sys.modules["SassBeautify.SassBeautify"].SassBeautifyCommand;

SassBeautifyCommandInstance = SassBeautifyCommand(None);


class test_internal_function_restore_end_of_line_comments(TestCase):

    # Check that inline comments starting with ---end-of-line-comment---
    # (which are inserted to "mark" those comments before running sass-convert)
    # are moved back to the previous line and restored to the original comment
    def test_inline_comment(self):
        beautified = SassBeautifyCommandInstance.restore_end_of_line_comments(textwrap.dedent("""\

            h1 {}
            //---end-of-line-comment--- test

            """))

        self.assertEqual(beautified, textwrap.dedent("""\

            h1 {} // test

            """))

    # Check that block comments are moved back and restored as well
    def test_block_comment(self):
        beautified = SassBeautifyCommandInstance.restore_end_of_line_comments(textwrap.dedent("""\

            h1 {}
            /*---end-of-line-comment--- line 1
            line 2 */

            """))

        self.assertEqual(beautified, textwrap.dedent("""\

            h1 {} /* line 1
            line 2 */

            """))


class test_internal_function_beautify_newlines(TestCase):

    # Check that a newline is inserted between two selectors
    def test_insert_newline_1(self):
        beautified = SassBeautifyCommandInstance.beautify_newlines(textwrap.dedent("""\

            .ClassA {
                color: red;
            }
            .ClassB {
                color: blue;
            }

            """))

        self.assertEqual(beautified, textwrap.dedent("""\

            .ClassA {
                color: red;
            }

            .ClassB {
                color: blue;
            }

            """))

    # Check that a property followed by a selector is separated with a newline
    def test_insert_newline_2(self):
        beautified = SassBeautifyCommandInstance.beautify_newlines(textwrap.dedent("""\

            .ClassA {
                color: red;
                .ClassB {
                    color: blue;
                }
            }

            """))

        self.assertEqual(beautified, textwrap.dedent("""\

            .ClassA {
                color: red;

                .ClassB {
                    color: blue;
                }
            }

            """))

    # Check that a propery followed by inline comment and then selector is separated with newline
    def test_insert_newline_3(self):
        beautified = SassBeautifyCommandInstance.beautify_newlines(textwrap.dedent("""\

            .ClassA {
                color: red;
                // This is class b
                .ClassB {
                    color: blue;
                }
            }

            """))

        self.assertEqual(beautified, textwrap.dedent("""\

            .ClassA {
                color: red;

                // This is class b
                .ClassB {
                    color: blue;
                }
            }

            """))

    # Check that propery followed by inline comment and then selector is separated with newline
    def test_insert_newline_4(self):
        beautified = SassBeautifyCommandInstance.beautify_newlines(textwrap.dedent("""\

            .ClassA {
                color: red;
                /*
                 This is class b
                */
                .ClassB {
                    color: blue;
                }
            }

            """))

        self.assertEqual(beautified, textwrap.dedent("""\

            .ClassA {
                color: red;

                /*
                 This is class b
                */
                .ClassB {
                    color: blue;
                }
            }

            """))


    # Check that two selectors already separated by a newline doesn't get an additional newline
    def test_skip_insert_newline_1(self):
        beautified = SassBeautifyCommandInstance.beautify_newlines(textwrap.dedent("""\

            .ClassA {
                color: red;
            }

            .ClassB {
                color: blue;
            }

            """))

        self.assertEqual(beautified, textwrap.dedent("""\

            .ClassA {
                color: red;
            }

            .ClassB {
                color: blue;
            }

            """))

    # Check that two nested selectors doesn't get any newlines
    def test_skip_insert_newline_2(self):
        beautified = SassBeautifyCommandInstance.beautify_newlines(textwrap.dedent("""\

            .ClassA {
                .ClassB {
                    color: blue;
                }
            }

            """))

        self.assertEqual(beautified, textwrap.dedent("""\

            .ClassA {
                .ClassB {
                    color: blue;
                }
            }

            """))

class test_internal_function_remove_leading_zero(TestCase):

    # check that leading zeros are removed properly
    def test_leading_zero(self):
        beautified = SassBeautifyCommandInstance.remove_leading_zero(textwrap.dedent("""\

            .ClassA {
                -webkit-transform: scale(0.9);
                transition: -webkit-transform 0.1s;
                background-color: rgba(67, 67, 67, 0.5);
            }

            """))

        self.assertEqual(beautified, textwrap.dedent("""\

            .ClassA {
                -webkit-transform: scale(.9);
                transition: -webkit-transform .1s;
                background-color: rgba(67, 67, 67, .5);
            }

            """))


class test_internal_function_beautify_semicolons(TestCase):

    # Check that we add ;s to the end of lines, except for comments, lines ending in commas, and lines before an open {
    # all other cases where we might introduce a double semicolon or where a semicolon isn't needed are cleaned up by
    # sass-convert so we don't need to worry about them here
    def test_semicolons(self):
        beautified = SassBeautifyCommandInstance.beautify_semicolons(textwrap.dedent("""\

            // @import '_common';
            @import "_colors"

            //TODO: eat pizza
            //      and other things

            .ClassA,
            .ClassB
            {
                height: 14px
                font-size: 2em;
                margin: -3px 0 !important
            }

            """))

        self.assertEqual(beautified, textwrap.dedent("""\

            // @import '_common';
            @import "_colors";
            ;
            //TODO: eat pizza
            //      and other things
            ;
            .ClassA,
            .ClassB
            {;
                height: 14px;
                font-size: 2em;;
                margin: -3px 0 !important;
            };

            """))

class test_internal_function_use_allman_style_indentation(TestCase):

    def test_convert_from_kandr_to_allman(self):
        beautified = SassBeautifyCommandInstance.use_allman_style_indentation(textwrap.dedent("""\

            .ClassA,
            .ClassB{
                .ClassC{
                    height: 14px;

                    @mixin whistle($number-of-rows, $small-buttons){
                        padding-top: 139px;
                    }

                    .ClassD
                    {
                        &[count='1']{
                            background-color: #black;
                        }
                    }

                    p{
                        font-size: 10px;
                    }
                }
            }

            """))

        self.assertEqual(beautified, textwrap.dedent("""\

            .ClassA,
            .ClassB
            {
                .ClassC
                {
                    height: 14px;

                    @mixin whistle($number-of-rows, $small-buttons)
                    {
                        padding-top: 139px;
                    }

                    .ClassD
                    {
                        &[count='1']
                        {
                            background-color: #black;
                        }
                    }

                    p
                    {
                        font-size: 10px;
                    }
                }
            }

            """))

class test_internal_function_hex_length(TestCase):

    def test_short(self):
        beautified = SassBeautifyCommandInstance.hex_length(textwrap.dedent("""\

            background-color: #000;
            background-color: #Aa44dd;
            background-color: #aa44gg;

            """), 'short')

        self.assertEqual(beautified, textwrap.dedent("""\

            background-color: #000;
            background-color: #A4d;
            background-color: #aa44gg;

            """))

    def test_long(self):
        beautified = SassBeautifyCommandInstance.hex_length(textwrap.dedent("""\

            background-color: #A4d;
            background-color: #aa44ff;
            background-color: #aa44gg;

            """), 'long')

        self.assertEqual(beautified, textwrap.dedent("""\

            background-color: #AA44dd;
            background-color: #aa44ff;
            background-color: #aa44gg;

            """))

    def test_ignore(self):
        beautified = SassBeautifyCommandInstance.hex_length(textwrap.dedent("""\

            background-color: #000;
            background-color: #Aa44dd;
            background-color: #aa44gg;

            """), 'ignore')

        self.assertEqual(beautified, textwrap.dedent("""\

            background-color: #000;
            background-color: #Aa44dd;
            background-color: #aa44gg;

            """))

class test_internal_function_remove_zero_unit(self, content):

    def test_remove_zero_unit(self, content):
        beautified = SassBeautifyCommandInstance.remove_zero_unit(textwrap.dedent("""\

            border: 0px;
            border: 0;
            border: 0em;
            border:0vmax;
            border: 0s;

            """))

        self.assertEqual(beautified, textwrap.dedent("""\

            border: 0;
            border: 0;
            border: 0;
            border:0;
            border: 0s;

            """))

class test_internal_function_border_zero(TestCase):

    def test_zero(self):
        beautified = SassBeautifyCommandInstance.border_zero(textwrap.dedent("""\

            border  :   none;

            """), "zero")

        self.assertEqual(beautified, textwrap.dedent("""\

            border: 0;

            """))

    def test_none(self):
        beautified = SassBeautifyCommandInstance.border_zero(textwrap.dedent("""\

            border: 0;

            """), "none")

        self.assertEqual(beautified, textwrap.dedent("""\

            border: none;

            """))

    def test_ignore(self):
        beautified = SassBeautifyCommandInstance.border_zero(textwrap.dedent("""\

            border: none;
            border: 0;

            """), "ignore")

        self.assertEqual(beautified, textwrap.dedent("""\

            border: none;
            border: 0;

            """))