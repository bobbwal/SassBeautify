'''
SassBeautify - A Sublime Text 2/3 plugin that beautifies sass files.
https://github.com/badsyntax/SassBeautify
'''
import sublime
import sublime_plugin
import os
import subprocess
import threading
import re

__version__ = '1.4.1'
__author__ = 'Richard Willis'
__email__ = 'willis.rh@gmail.com'
__copyright__ = 'Copyright 2013, Richard Willis'
__license__ = 'MIT'
__credits__ = ['scotthovestadt', 'WilliamVercken', 'Napanee']


class ExecSassCommand(threading.Thread):

    '''
    This is a threaded class that we use for running the sass command in a
    different thread. We thread the sub-process se we don't lockup the UI.
    '''

    def __init__(self, cmd, env, stdin):

        self.cmd = cmd
        self.env = env
        self.stdin = stdin
        self.returncode = 0
        self.stdout = None
        self.stderr = None

        threading.Thread.__init__(self)

    def run(self):
        '''
        Executes the command in a sub-process.
        '''
        try:
            process = subprocess.Popen(
                self.cmd,
                env=self.env,
                shell=sublime.platform() == 'windows',
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            (self.stdout, self.stderr) = process.communicate(input=self.stdin)
            self.returncode = process.returncode
        except OSError as e:
            self.stderr = str(e)
            self.returncode = 1

class SassBeautifyReplaceTextCommand(sublime_plugin.TextCommand):

    '''
    A Text Command to replace the entire view with new text.
    '''

    def run(self, edit, text=None):
        self.view.replace(edit, sublime.Region(0, self.view.size()), text)


class SassBeautifyEvents(sublime_plugin.EventListener):

    '''
    An EventListener class to utilize Sublime's events.
    '''

    def on_post_save(self, view):
        '''
        After saving the file, optionally beautify it. This is done
        on_post_save because the beautification is asynchronous.
        '''
        settings = sublime.load_settings('SassBeautify.sublime-settings')
        beautify_on_save = settings.get('beautifyOnSave', False)
        project_data = sublime.active_window().project_data()
        if project_data:
            project_settings = project_data.get('SassBeautify', {})
            if 'beautifyOnSave' in project_settings:
                beautify_on_save = project_settings['beautifyOnSave']

        if not SassBeautifyCommand.saving and beautify_on_save:
            view.run_command('sass_beautify', {
                'show_errors': False
            })


class SassBeautifyCommand(sublime_plugin.TextCommand):

    '''
    Our main SassBeautify Text Command.
    '''

    saving = False
    viewport_pos = None
    selection = None

    def run(self, edit, action='beautify', convert_from_type=None, show_errors=True):

        self.action = action
        self.convert_from_type = convert_from_type
        self.settings = sublime.load_settings('SassBeautify.sublime-settings')
        self.show_errors = show_errors

        project_data = sublime.active_window().project_data()
        if project_data:
            project_settings = project_data.get('SassBeautify', {})
            for k,v in project_settings.items():
                self.settings.set(k, v)

        if self.check_file():
            self.beautify()

    def check_file(self):
        '''
        Performs some validation checks on the file to ensure we're working with
        something that we can beautify.
        '''
        # A file has to be saved so we can get the conversion type from the
        # file extension.
        if self.view.file_name() is None:
            self.error_message('Please save this file before trying to beautify.')
            return False

        # Check the file has the correct extension before beautifying.
        if self.get_type() not in ['sass', 'scss']:
            self.error_message('Not a valid Sass file.')
            return False

        return True

    def error_message(self, message):
        '''
        Shows a Sublime error message.
        '''
        if self.show_errors:
            sublime.error_message(message)

    def beautify(self):
        '''
        Runs the sass beautify command.
        '''
        thread = ExecSassCommand(
            self.get_cmd(),
            self.get_env(),
            self.get_text()
        )
        thread.start()
        self.check_thread(thread)

    def restore_end_of_line_comments(self, content):
        def restore(m):
            return ' ' + m.group(2) + m.group(4);

        # Restore line and block comments at the end of lines that have been pushed to the next line by sass-convert
        content = re.sub('(\s+)(//|/\\*)(---end-of-line-comment---)(.*)', restore, content)

        # Cleanup, some // and /* might have gotten ---end-of-line-comment--- added which were not
        # matched and removed by regexp (for instance, // appeared inside a block comment),
        # in which case we want to restore the comment. We don't need regexp, so we're using simple string replace.
        content = content.replace('//---end-of-line-comment---', '//')
        content = content.replace('/*---end-of-line-comment---', '/*')

        return content

    def beautify_newlines(self, content):
        def insert_newline_between_capturing_parentheses(m):
            return m.group(1) + '\n' + m.group(2)

        # Insert newline after "}" or ";" if the line after defines (or starts to define) a selector
        # (i.e. contains some characters followed by a "{" or "," on the same line).
        # This is in order to make the selector more visible and increase readability
        content = re.sub(re.compile('(;.*|}.*)(\n.+[{,])$', re.MULTILINE), insert_newline_between_capturing_parentheses, content)

        # Similar to above, except the next line starts a comment block followed by a selector
        matchCommentBlockRegEx = '/\\*(\\*(?!/)|[^\\*])*\\*/'
        content = re.sub(re.compile('(;.*|}.*)(\n +' + matchCommentBlockRegEx + '\n.+[{,])$', re.MULTILINE), insert_newline_between_capturing_parentheses, content)

        # Similar to above, except the next line is a commented out line followed by a selector
        content = re.sub(re.compile('(;.*|}.*)(\n +//.*\n.+[{,])$', re.MULTILINE), insert_newline_between_capturing_parentheses, content)

        return content

    def use_single_quotes(self, content):
        content = content.replace('"', '\'')
        return content

    def border_zero(self, content, option):
        if option == 'zero':
            content = re.sub(re.compile('(border *: *none)'), 'border: 0', content)
        elif option == 'none':
            content = re.sub(re.compile('(border *: *0)'), 'border: none', content)

        return content

    def remove_zero_unit(self, content):
        content = re.sub(r'([ :]0) *(rem|vmin|vmax|px|em|ex|ch|vh|vw|vm|px|mm|cm|in|pt|pc|%)', r'\1', content)
        return content

    def hex_length(self, content, option):
        if option == 'long':
            content = re.sub(re.compile(r'#([a-f0-9])([a-f0-9])([a-f0-9])([ ;])', re.I), r'#\1\1\2\2\3\3\4', content)
        elif option == 'short':
            content = re.sub(re.compile(r'#([a-f0-9])\1([a-f0-9])\2([a-f0-9])\3', re.I), r'#\1\2\3', content)

        return content

    def use_allman_style_indentation(self, content):
        def insert_newline_before_open_bracket(m):
            return m.group(1) + m.group(2) + '\n' + m.group(1) + '{'

        content = re.sub(re.compile('([ \t]*)(\S.*[\])\w]? *){$', re.MULTILINE), insert_newline_before_open_bracket, content)
        return content

    def remove_leading_zero(self, content):
        return re.sub(r'([\( ]+)0\.(\d*)', r'\1.\2', content)

    def beautify_semicolons(self, content):
        '''
        Appends a semicolon to the lines missing one
        '''
        def remove_semicolon_from_end_of_comment(m):
            return m.group(1) + m.group(2)

        content = re.sub(re.compile('(?<!,)$', re.MULTILINE), ';', content) # add ; to all lines not ending in ,
        content = re.sub(re.compile(';(?=$\s*\{)', re.MULTILINE), '', content) # remove ; if next line starts with {
        content = re.sub(re.compile('(//|/\\*)(.*);$', re.MULTILINE), remove_semicolon_from_end_of_comment, content) # remove ; if at end of comment
        # sass-convert removes all other cases of extra ;s, so don't worry about them here
        return content

    def check_thread(self, thread, i=0, dir=1):
        '''
        Checks if the thread is still running.
        '''

        # This animates a little activity indicator in the status area
        # Taken from https://github.com/wbond/sublime_prefixr
        before = i % 8
        after = (7) - before
        if not after:
            dir = -1
        if not before:
            dir = 1
        i += dir

        self.view.set_status(
            'sassbeautify',
            'SassBeautify [%s=%s]' % (' ' * before, ' ' * after)
        )

        if thread.is_alive():
            return sublime.set_timeout(lambda: self.check_thread(thread, i, dir), 100)

        self.view.erase_status('sassbeautify')
        self.handle_process(thread.returncode, thread.stdout, thread.stderr)

    def handle_process(self, returncode, output, error):
        '''
        Handles the streams from the threaded process.
        '''

        if type(output) is bytes:
            output = output.decode('utf-8')

        if type(error) is bytes:
            error = error.decode('utf-8')

        if returncode != 0:
            return self.error_message(
                'There was an error beautifying your Sass:\n\n' + error
            )

        # Ensure we're working with unix-style newlines.
        # Fixes issue on windows with Sass < v3.2.10.
        output = '\n'.join(output.splitlines())

        if self.settings.get('inlineComments', False):
            output = self.restore_end_of_line_comments(output)

        if self.settings.get('newlineBetweenSelectors', False):
            output = self.beautify_newlines(output)

        if self.settings.get('useSingleQuotes', False):
            output = self.use_single_quotes(output)

        output = self.border_zero(output, self.settings.get('borderZero', 'ignore'))

        if self.settings.get('zeroUnit', False):
            output = self.remove_zero_unit(output)


        output = self.hex_length(output, self.settings.get('hexLength', 'ignore'))

        if self.settings.get('indentStyle', 'kandr') == 'allman':
            output = self.use_allman_style_indentation(output)

        if self.settings.get('leadingZero', False):
            output = self.remove_leading_zero(output)

        self.viewport_pos = self.view.viewport_position()
        self.selection = self.view.sel()[0]

        # Update the text in the editor
        self.view.run_command('sass_beautify_replace_text', {'text': output})

        # Save the file
        sublime.set_timeout(self.save, 1)

    def get_cmd(self):
        '''
        Generates the sass command.
        '''
        filetype = self.get_type()

        cmd = [
            'sass-convert',
            '--unix-newlines',
            '--stdin',
            '--indent', str(self.settings.get('indent', 't')),
            '--from', filetype if self.action == 'beautify' else self.convert_from_type,
            '--to', filetype
        ]

        # Convert underscores to dashes.
        if self.settings.get('dasherize', False):
            cmd.append('--dasherize')

        # Output the old-style ':prop val' property syntax.
        # Only meaningful when generating Sass.
        if self.settings.get('old', False) and filetype == 'sass':
            cmd.append('--old')

        return cmd

    def get_env(self):
        '''
        Generates the process environment.
        '''
        env = os.environ.copy()

        if self.settings.get('path', False):
            env['PATH'] = self.settings.get('path')

        if self.settings.get('gemPath', False):
            env['GEM_PATH'] = self.settings.get('gemPath')

        return env

    def get_ext(self):
        '''
        Extracts the extension from the filename.
        '''
        (basename, ext) = os.path.splitext(self.view.file_name())
        return ext.strip('.')

    def get_type(self):
        '''
        Returns the file type.
        '''
        filetype = self.get_ext()
        # Added experimental CSS support with issue #27.
        # If this is a CSS file, then we're to treat it exactly like a SCSS file.
        if self.action == 'beautify' and filetype == 'css':
            filetype = 'scss'
        return filetype

    def get_text(self):

        def mark_end_of_line_comment(m):
            return m.group(1) + m.group(2) + '---end-of-line-comment---' + m.group(3)

        '''
        Gets the sass text from the Sublime view.
        '''
        content = self.view.substr(sublime.Region(0, self.view.size()))

        content = self.beautify_semicolons(content)

        if self.settings.get('inlineComments', False):
            '''
            Mark comments at the end of lines so we can move them back to the end of the line after sass-convert has pushed them to a new line
            '''
            content = re.sub(re.compile('([;{}]+[ \t]*)(//|/\\*)(.*)$', re.MULTILINE), mark_end_of_line_comment, content)

        return content.encode('utf-8')

    def save(self):
        '''
        Saves the file and show a success message.
        '''

        # We have to store the state to prevent us getting in an infinite loop
        # when beautifying on_post_save.
        SassBeautifyCommand.saving = True
        self.view.run_command('save')
        SassBeautifyCommand.saving = False

        self.view.set_viewport_position(self.viewport_pos, False)
        self.view.sel().clear()
        self.view.sel().add(self.selection)

        sublime.status_message('Successfully beautified ' + self.view.file_name())
