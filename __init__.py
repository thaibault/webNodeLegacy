#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# region header

'''
    Provides the main entry point for the web application. Initializes models \
    and starts the web socket.
'''

# # python3.4
# # pass
from __future__ import absolute_import, division, print_function, \
    unicode_literals
# #

__author__ = 'Torben Sickert'
__copyright__ = 'see module docstring'
__credits__ = 'Torben Sickert',
__license__ = 'see module docstring'
__maintainer__ = 'Torben Sickert'
__maintainer_email__ = 't.sickert["~at~"]gmail.com'
__status__ = 'stable'
__version__ = '1.0'

# # python3.4 import builtins
import __builtin__ as builtins
from copy import copy, deepcopy
from datetime import datetime as DateTime
from datetime import time as NativeTime
from datetime import date as Date
from datetime import timedelta as TimeDelta
import inspect
import json
import logging
import multiprocessing
import os
import re
import sys
import time

from sqlalchemy.engine.default import DefaultExecutionContext
from sqlalchemy import create_engine as create_database_engine
from sqlalchemy.orm import sessionmaker as create_database_session
from sqlalchemy.schema import CreateTable, DropTable, Table, MetaData
from sqlalchemy import event as SqlalchemyEvent
from sqlalchemy.engine import Engine as SqlalchemyEngine
from sqlite3 import Connection as SQLite3Connection

# # python3.4
import boostNode
from boostNode.extension.file import Handler as FileHandler
from boostNode.extension.native import Module, Dictionary, String, Time
from boostNode.extension.output import Print
from boostNode.extension.system import CommandLine, Runnable
from boostNode.extension.type import Null
from boostNode.paradigm.objectOrientation import Class
from boostNode.runnable.server import Web as WebServer
from boostNode.runnable.template import Parser as TemplateParser
from boostNode.runnable.template import __exception__ as TemplateError

try:
    Controller = builtins.__import__('controller', {}, {}, ('Main',)).Main
    RestResponse = builtins.__import__(
        'restController', {}, {}, ('Response',)
    ).Response
except builtins.ImportError as exception:
    module_import_error = exception
    Controller = RestResponse = None
else:
    module_import_error = None

# endregion


# region variables

OPTIONS = {}

# endregion


# region classes

class Main(Class, Runnable):

    '''Handles the applications core concerns.'''

    # region properties

    ROOT_PATH = '/'
    '''Saves the sandboxed application root path.'''
    CONFIGURATION_FILE_PATH = '/options.json'
    '''Saves a path pointing to the applications global configuration file.'''
    rest_data_timestamp_reference_file = None
    '''Saves a database timestamp reference file.'''
    web_server = None
    '''Saves the web server instance.'''
    debug = False
    '''Indicates weather the application is currently in debug mode.'''
    given_command_line_arguments = None
    '''Holds all given commend line arguments in a named tuple.'''
    options = {}
    '''Holds the backend and frontend specific options.'''
    model = None
    '''Holds the model module.'''
    web_api_lock = multiprocessing.Lock()
    '''
        A lock to acquire if workers should be finished before application \
        can be closed.
    '''
    frontend_html_file = None
    backend_html_file = None
    '''Holds the main entry files for bootstrapping the web application.'''
    html_template_file = None
    '''Saves the template file for frontend and backend based html file.'''
    package_name = ''
    '''Saves dynamically determined package name.'''

    # endregion

    # region public methods

    # # region static

    # # # region boolean

    @classmethod
    def is_valid_web_asset(cls, file):
        '''Checks if the given file is a valid web application asset.'''
        for pattern in cls.options['ignore_web_asset_pattern']:
# # python3.4             if re.compile(pattern).fullmatch(file.name):
            if re.compile('(?:%s)$' % pattern).match(file.name):
                return False
        return True

    @classmethod
    def is_cached(cls, cache_file):
        '''Determines weather given file is a valid usable cache file.'''
        return(sys.flags.optimize and not cls.debug) and cache_file

        # # endregion

        # # region helper

    @classmethod
    def extend_options(cls, options, consolidate=True):
        '''Extends options object with given options.'''
        if options:
            cls.options = Dictionary(cls.options).update(options).content
            if consolidate:
                cls.consolidate_options()
        return cls

    @classmethod
    def convert_options_for_client(cls):
        '''
            Converts options dictionary for client. Key are converted to its \
            camel case representation and values are converted to java script \
            compatible types.
        '''
# # python3.4
# #         cls.options['frontend'] = Dictionary(cls.options['frontend']).convert(
# #             key_wrapper=lambda key, value: cls.convert_for_client(String(
# #                 key
# #             ).get_delimited_to_camel_case(
# #                 preserve_wrong_formatted_abbreviations=True
# #             ).content),
# #             value_wrapper=cls.convert_for_client
# #         ).content
        cls.options['frontend'] = Dictionary(cls.options['frontend']).convert(
            key_wrapper=lambda key, value: cls.convert_for_client(
                builtins.unicode(String(key).get_delimited_to_camel_case(
                    preserve_wrong_formatted_abbreviations=True
                ).content, boostNode.ENCODING)),
            value_wrapper=cls.convert_for_client
        ).content
# #
        return cls

    @classmethod
    def consolidate_options(cls):
        '''Merges, renders and resolves internal option dependencies.'''
        '''
            NOTE: This is the only backend needed camel case option, because \
            it will be appended via introspection.
        '''
        cls._merge_options().options['moduleName'] = __name__
        frontend_options = cls.options['frontend']
        del cls.options['frontend']
        cls.options = Dictionary(cls.options).convert(
            key_wrapper=lambda key, value: cls.convert_for_backend(key),
            value_wrapper=cls.convert_for_backend
        ).content
        cls.options['frontend'] = frontend_options
        '''
            NOTE: We have to run over options twice to handle cyclic \
            dependencies.
        '''
        for number in builtins.range(2):
# # python3.4
# #             cls.options = Dictionary(cls.options).convert(
# #                 value_wrapper=lambda key, value: TemplateParser(
# #                     value.replace('\\', 2 * '\\').replace('<%%', '<%%%'),
# #                     string=True
# #                 ).render(
# #                     mapping=cls.options, module_name=__name__, main=cls
# #                 ).output if builtins.isinstance(
# #                     value, builtins.str
# #                 ) else value
# #             ).content
            cls.options = Dictionary(cls.options).convert(
                value_wrapper=lambda key, value: TemplateParser(
                    value.replace('\\', 2 * '\\').replace('<%%', '<%%%'),
                    string=True
                ).render(
                    mapping=cls.options, module_name=__name__, main=cls
                ).output if builtins.isinstance(
                    value, (builtins.unicode, builtins.str)
                ) else value
            ).content
# #
        frontend_options = cls.options['frontend']
        del cls.options['frontend']
# # python3.4
# #         cls.options = Dictionary(cls.options).convert(
# #             key_wrapper=lambda key, value: String(
# #                 key
# #             ).get_camel_case_to_delimited().content,
# #             value_wrapper=cls.convert_for_backend
# #         ).content
        cls.options = Dictionary(cls.options).convert(
            key_wrapper=lambda key, value: builtins.unicode(String(
                key
            ).get_camel_case_to_delimited().content, boostNode.ENCODING),
            value_wrapper=cls.convert_for_backend
        ).content
# #
        cls.options['frontend'] = frontend_options
        cls.options['session']['expiration_interval'] = TimeDelta(
            minutes=cls.options['session']['expiration_time_in_minutes'])
        return cls

    @classmethod
    def extend_user_authorization(
        cls, user_id, session_token, location=None
    ):
        '''Extends user authorization time.'''
        user = None
        if user_id and session_token:
            session = create_database_session(bind=cls.engine)()
            users = session.query(cls.model.User).filter(
                cls.model.User.enabled == True,
                cls.model.User.id == builtins.int(user_id),
                cls.model.User.session_token == session_token,
                cls.model.User.session_expiration_date_time > DateTime.now())
            if users.count():
                user = users.one()
                user.session_expiration_date_time = DateTime.now(
                ) + cls.options['session']['expiration_interval']
                __logger__.info('Authorize user "%d" for %d hours.', user.id, (
                    cls.options['session'][
                        'expiration_interval'
                    ].total_seconds() / 60
                ) / 60)
                if location is not None:
                    user.location = location
                session.commit()
        return user

    @classmethod
    def render_templates(cls, all=False):
        '''Renders the main index html file.'''
        mapping = {
            'options': deepcopy(cls.options),
            'debug': cls.debug, 'given_command_line_arguments':
            cls.given_command_line_arguments, 'root': FileHandler.get_root()}
        if 'admin' in mapping['options']['frontend']:
            del mapping['options']['frontend']['admin']
        if all:
            FileHandler(location='/').iterate_directory(
                function=cls._render_template, recursive=True, mapping=mapping)
        cls._render_html_templates(mapping)
        return cls

    @classmethod
    def clear_web_cache(cls):
        '''Clears all web cache files.'''
        __logger__.info(
            'Clear web cache in "%s".', cls.options['location']['web_cache'])
        for file in FileHandler(location=cls.options['location']['web_cache']):
            if cls.is_valid_web_asset(file):
                file.remove_deep()
        return cls

    @classmethod
    def convert_for_client(cls, key, value=Null):
        '''Returns the serialized version of given value.'''
        if value is Null:
            value = key
        else:
# # python3.4
# #             if builtins.isinstance(value, Date):
# #                 return time.mktime(value.timetuple())
# #             if builtins.isinstance(value, DateTime):
# #                 return value.timestamp(
# #                 ) + builtins.float(value.microsecond) / 1000 ** 2
            if builtins.isinstance(value, Date):
                return time.mktime(value.timetuple())
            if builtins.isinstance(value, DateTime):
                return(
                    time.mktime(value.timetuple()) +
                    value.microsecond / 1000 ** 2)
# #
            if builtins.isinstance(value, NativeTime):
                return(
                    60.0 ** 2 * value.hour + 60 * value.minute +
                    value.second + value.microsecond / 1000 ** 2)
# # python3.4
# #             if(builtins.isinstance(key, builtins.str) and (
# #                 key == 'language' or key.endswith('_language') or
# #                 key.endswith('Language')
# #             )) and re.compile('[a-z]{2}_[a-z]{2}').fullmatch(value):
# #                 return String(value).get_delimited_to_camel_case(
# #                 ).content[:-1] + value[-1].upper()
            if(builtins.isinstance(key, (
                builtins.unicode, builtins.str
            )) and (
                key == 'language' or key.endswith('_language') or
                key.endswith('Language')
            )) and re.compile('[a-z]{2}_[a-z]{2}$').match(value):
                return '%s%s' % (builtins.unicode(
                    String(value).get_delimited_to_camel_case().content[:-1],
                    boostNode.ENCODING
                ), value[-1].upper())
# #
        if not builtins.isinstance(value, (
            builtins.int, builtins.float, builtins.type(None)
        )):
# # python3.4
# #             pass
            if builtins.isinstance(value, builtins.unicode):
                return value
            if builtins.isinstance(value, builtins.str):
                return builtins.unicode(value, boostNode.ENCODING)
# #
            return builtins.str(value)
        return value

    @classmethod
    def convert_dictionary_for_backend(cls, data):
        '''Converts a given dictionary in backend compatible data types.'''
# # python3.4
# #         return Dictionary(data).convert(
# #             key_wrapper=lambda key, value: String(
# #                 key
# #             ).get_camel_case_to_delimited().content if builtins.isinstance(
# #                 key, builtins.str
# #             ) else cls.convert_for_backend(key),
# #             value_wrapper=cls.convert_for_backend
# #         ).content
        return Dictionary(data).convert(
            key_wrapper=lambda key, value: builtins.unicode(
                String(key).get_camel_case_to_delimited().content,
                boostNode.ENCODING
            ) if builtins.isinstance(
                key, (builtins.unicode, builtins.str)
            ) else cls.convert_for_backend(key),
            value_wrapper=cls.convert_for_backend
        ).content
# #

    @classmethod
    def convert_for_backend(cls, key, value=Null):
        '''Converts data from client to python specific data objects.'''
        if value is not None:
            if value is Null:
                value = key
# # python3.4
# #             elif builtins.isinstance(key, builtins.str):
            elif builtins.isinstance(key, (builtins.unicode, builtins.str)):
# #
                if key == 'date_time' or key.endswith('_date_time'):
                    if builtins.isinstance(
                        value, (builtins.int, builtins.float)
                    ):
                        try:
                            return DateTime.fromtimestamp(value)
                        except builtins.ValueError:
                            pass
                    converted_value = String(value).get_number()
                    if builtins.isinstance(
                        converted_value, (builtins.int, builtins.float)
                    ):
                        try:
                            return DateTime.fromtimestamp(converted_value)
                        except builtins.ValueError:
                            pass
# # python3.4
# #                     if builtins.isinstance(value, builtins.str):
                    if builtins.isinstance(
                        value, (builtins.unicode, builtins.str)
                    ):
# #
                        for delimiter in ('.', '/'):
                            for year_format in ('%y', '%Y'):
                                for ms_format in ('', ':%f'):
                                    for date_time_format in (
                                        '%c',
                                        '%d{delimiter}%m{delimiter}{year} '
                                        '%X{microsecond}',
                                        '%m{delimiter}%d{delimiter}{year} '
                                        '%X{microsecond}',
                                        '%w{delimiter}%m{delimiter}{year} '
                                        '%X{microsecond}',
                                    ):
                                        try:
                                            return DateTime.strptime(
                                                value, date_time_format.format(
                                                    delimiter=delimiter,
                                                    year=year_format,
                                                    microsecond=ms_format)
                                            )
                                        except builtins.ValueError:
                                            pass
                if key == 'date' or key.endswith('_date') or key.endswith(
                    'Date'
                ):
                    if builtins.isinstance(
                        value, (builtins.int, builtins.float)
                    ):
                        try:
                            return Date.fromtimestamp(value)
                        except builtins.ValueError:
                            pass
                    converted_value = String(value).get_number()
                    if builtins.isinstance(converted_value, (
                        builtins.int, builtins.float
                    )):
                        try:
                            return Date.fromtimestamp(converted_value)
                        except builtins.ValueError:
                            pass
# # python3.4
# #                     if builtins.isinstance(value, builtins.str):
                    if builtins.isinstance(value, (
                        builtins.unicode, builtins.str
                    )):
# #
                        for delimiter in ('.', '/'):
                            for year_format in ('%y', '%Y'):
                                for date_format in (
                                    '%x', '%d{delimiter}%m{delimiter}{year}',
                                    '%m{delimiter}%d{delimiter}{year}',
                                    '%w{delimiter}%m{delimiter}{year}'
                                ):
                                    try:
# # python3.4
# #                                        return Date.fromtimestamp(
# #                                            DateTime.strptime(
# #                                                value, date_format.format(
# #                                                    delimiter=delimiter,
# #                                                    year=year_format
# #                                                )).timestamp())
                                        return Date.fromtimestamp(time.mktime(
                                            DateTime.strptime(
                                                value, date_format.format(
                                                    delimiter=delimiter,
                                                    year=year_format
                                                )).timetuple()))
# #
                                    except builtins.ValueError:
                                        pass
                if key == 'time' or key.endswith('_time') or key.endswith(
                    'Time'
                ):
                    return Time(value).content
# # python3.4
# #                 if(key == 'language' or key.endswith('_language') or
# #                    key.endswith('Language')
# #                    ) and re.compile('[a-z]{2}[A-Z]{2}').fullmatch(value):
# #                     return String(value).get_camel_case_to_delimited().content
# #             if builtins.isinstance(value, builtins.str):
# #                 return String(value).get_number()
                if(key == 'language' or key.endswith('_language') or
                   key.endswith('Language')
                   ) and re.compile('[a-z]{2}[A-Z]{2}$').match(value):
                    return builtins.unicode(
                        String(value).get_camel_case_to_delimited().content,
                        boostNode.ENCODING)
            if builtins.isinstance(value, (builtins.unicode, builtins.str)):
                if builtins.isinstance(value, builtins.unicode):
                    number = String(value.encode(
                        boostNode.ENCODING
                    )).get_number()
                else:
                    number = String(value).get_number()
                if builtins.isinstance(number, builtins.str):
                    return builtins.unicode(number, boostNode.ENCODING)
                return number
# #
        return value

        # # endregion

        # endregion

        # region getter

    @classmethod
    def get_web_asset_file_paths(cls, path=None):
        '''
            Determine a list of relative file paths needed for the web \
            application.
        '''
        paths = []
        if path is None:
            path = cls.options['location']['web_asset']
            cls._root_asset_path_len = builtins.len(FileHandler(
                location=path
            ).path)
        for file in FileHandler(location=path):
            if cls.is_valid_web_asset(file):
                if file.is_directory():
                    paths += cls._determine_file_assets(file.path)
                else:
                    paths.append(file.path[cls._root_asset_path_len:])
        return paths

    @classmethod
    def get_timestamps(cls, path):
        '''
            Generates a string consisting of any file timestamp of web \
            application needed file in the given location.
        '''
        version = 0
        for file in FileHandler(location=path):
            if cls.is_valid_web_asset(file):
                if file.is_directory():
                    version += cls.get_timestamps(file.path)
                else:
                    version += file.timestamp
        return version

        # endregion

    def stop(self, *arguments, **keywords):
        '''
            This method is triggered if the application should die. The web \
            server will be closed.
        '''
        if self.web_server:
            '''
                Take this method type by the abstract class via introspection.
            '''
            with self.web_api_lock:
                getattr(self.web_server, inspect.stack()[0][3])(
                    *arguments, **keywords)
        if not (Controller is None or self.controller is None):
            self.controller.stop()
        '''Take this method type by the abstract class via introspection.'''
        return getattr(
            super(self.__class__, self), inspect.stack()[0][3]
        )(*arguments, **keywords)

    def get_manifest(self, user):
        '''
            Prints the dynamically generated manifest file. It includes all \
            web depended file timestamps to make sure that the web \
            application recognizes a newer version.
        '''
        asset_files = []

        def add_asset_file(file):
            '''Append each valid asset to the asset file list.'''
            if self.is_valid_web_asset(file):
                if file.is_file():
                    asset_files.append(file)
                return True
        FileHandler(
            location=self.options['location']['web_asset']
        ).iterate_directory(add_asset_file, recursive=True)
        offline_manifest_template_file = FileHandler(
            location=self.options['location'][
                'offline_manifest_template_file'])
        account_state = 1
        account_data = {}
        if user is not None:
            account_data = user.dictionary
            account_state = builtins.hash(
                Dictionary(account_data).get_immutable())
        return TemplateParser(
            offline_manifest_template_file,
            template_context_default_indent=self.options[
                'default_indent_level']
        ).render(
            asset_files=asset_files, html_file=self.frontend_html_file,
            asset_version=self.get_timestamps(
                self.options['location']['web_asset']),
            version='%s - %d' % (__version__, FileHandler(
                location=Module.get_name(
                    path=True, extension=True, frame=inspect.currentframe()
                )
            ).timestamp), account_state=account_state,
            request_file_name=__name__, host=self.data['handler'].host,
            account_data=account_data,
            offline_manifest_template_file=offline_manifest_template_file,
            mapping=self.controller.get_manifest_scope(request=self, user=user)
        ).output

    def authenticate(self):
        '''
            Authenticates a user by potential sent header identification data.
        '''
        user_id = session_token = location = None
        # TODO convert Strings to unicode in python2.7
        if self.options['authentication_method'] == 'header':
            user_id = self.data['handler'].headers.get(String(
                self.options['session']['key']['user_id']
            ).get_camel_case_to_delimited(delimiter='-').content)
            session_token = self.data['handler'].headers.get(String(
                self.options['session']['key']['token']
            ).get_camel_case_to_delimited(delimiter='-').content)
            if self.data['request_type'] != 'head':
                location = self.data['handler'].headers.get(String(
                    self.options['session']['key']['location']
                ).get_camel_case_to_delimited(delimiter='-').content)
        elif self.options['authentication_method'] == 'cookie':
            user_id = self.data['cookie'].get(
                self.options['session']['key']['user_id'])
            session_token = self.data['cookie'].get(
                self.options['session']['key']['token'])
            if self.data['request_type'] != 'head':
                location = self.data['cookie'].get(
                    self.options['session']['key']['location'])
        return self.extend_user_authorization(
            user_id, session_token, location)

    # endregion

    # region protected methods

        # region runnable implementation

    def _initialize(self):
        '''Starts the web controller if already started.'''

        # # region properties

        self.data = __request_arguments__

        self.new_cookie = {}
        '''Normalize get and payload data.'''
        self.data['get'] = self.convert_dictionary_for_backend(
            self.data['get'])
        if builtins.isinstance(self.data['data'], builtins.list):
            for index, item in builtins.enumerate(self.data['data']):
                self.data['data'][index] = self.convert_dictionary_for_backend(
                    item)
        else:
            if self.options['remove_duplicated_request_key']:
                for key, value in self.data['data'].items():
                    if builtins.isinstance(value, builtins.list):
                        if builtins.len(value) > 0:
                            self.data['data'][key] = value[0]
                        else:
                            self.data['data'][key] = None
            self.data['data'] = self.convert_dictionary_for_backend(
                self.data['data'])
        self.authorized_user = self.authenticate()

        # # endregion

        '''
            Export options to global scope to make them accessible for other \
            modules like model or controller.
        '''
        try:
            self._web_controller()
        except TemplateError as exception:
            if self.debug:
# # python3.4
# #                 self.data['handler'].send_error(500, '%s: "%s"' % (
# #                     exception.__class__.__name__, builtins.str(exception)))
                self.data['handler'].send_error(500, builtins.str(
                    '%s: "%s"'
                ) % (
                    builtins.str(exception.__class__.__name__),
                    builtins.unicode(
                        builtins.str(exception), boostNode.ENCODING
                    ).encode(boostNode.ENCODING)))
# #
            else:
                '''NOTE: The web server will handle this.'''
                raise
        return self

    def _run(self):
        '''Initializes the web server.'''

        # # region properties

        self.__class__.package_name = Module.get_package_name(
            frame=inspect.currentframe())
        FileHandler.set_root(location=FileHandler(location=FileHandler(
            location=Module.get_name(
                frame=inspect.currentframe(), path=True, extension=True),
            output_with_root_prefix=True
        ).directory_path).directory_path)
        self.__class__.ROOT_PATH = FileHandler.get_root().path
        self.__class__.controller = None
        if not (__test_mode__ or module_import_error is None):
            raise module_import_error
        self._set_options()
        '''Export options dictionary for early access to other modules.'''
        global OPTIONS
        OPTIONS = self.options
        self.__class__.given_command_line_arguments = \
            CommandLine.argument_parser(
                arguments=self.options['command_line_arguments'],
                module_name=__name__)
        self.__class__.debug = \
            sys.flags.debug or __logger__.isEnabledFor(logging.DEBUG)
        if Controller is not None:
            self.__class__.controller = Controller(main=self.__class__)
            if 'authentication_handler' in self.options['web_server']:
# # python3.4
# #                 self.options['web_server']['authentication_handler'] = \
# #                 builtins.eval(
# #                     self.options['web_server']['authentication_handler'],
# #                     {'controller': self.controller})
                self.options['web_server']['authentication_handler'] = \
                builtins.eval(
                    self.options['web_server']['authentication_handler'],
                    {'controller': self.controller})
# #
        try:
            self.__class__.model = builtins.__import__('model')
        except builtins.ImportError:
            if __test_mode__:
                self.__class__.model = None
            else:
                raise
        self._append_model_informations_to_options()
        self.__class__.frontend_html_file = FileHandler(
            location=self.options['location']['html_file']['frontend'])
        self.__class__.backend_html_file = FileHandler(
            location=self.options['location']['html_file']['backend'])
        self.__class__.html_template_file = FileHandler(
            location=self.options['location']['html_file']['template'])
        self.__class__.frontend_data_wrapper = {
            'key_wrapper': lambda key, value: self.convert_for_client(String(
                key
            ).get_delimited_to_camel_case().content),
            'value_wrapper': self.convert_for_client}
        self.__class__.backend_data_wrapper = {
            'key_wrapper': lambda key, value: self.convert_for_backend(String(
                key
            ).get_camel_case_to_delimited().content),
            'value_wrapper': self.convert_for_backend}

        # # endregion

        __logger__.info('Sandbox application into "%s".', self.ROOT_PATH)
        __logger__.info(
            'Application is running in %s mode.',
            'performance' if sys.flags.optimize else 'normal')
        __logger__.info(
            'Initialize database on "%s".',
            self.options['location']['database']['url'])
        self._initialize_model()
        if self.controller is not None:
            self.__class__.options = self.controller.initialize()
        self.convert_options_for_client()
        if(self.options['initial_template_rendering'] or
           self.given_command_line_arguments.render_template):
            __logger__.info('Render template files.')
            self.render_templates(all=True)
        self.__class__.rest_data_timestamp_reference_file = FileHandler(
            location=self.options['location']['database'][
                'rest_data_timestamp_reference_file_path'])
        if self.debug:
            self.clear_web_cache()
        if not self.rest_data_timestamp_reference_file:
            self.__class__.rest_data_timestamp_reference_file.content = ''
        if not self.given_command_line_arguments.render_template:
            return self._start_web_server()

        # endregion

    # # region static

    # # # region helper methods

    @classmethod
    def _render_template(cls, file, mapping):
        '''
            Renders each template and distinguishes between backend and \
            frontend templates.
        '''
        if(file.is_symbolic_link() or
           file.path in cls.options['location']['template_ignored']):
            '''Don't enter ignored locations or parse ignored files.'''
            return None
# # python3.4
# #         if(file.extension == TemplateParser.DEFAULT_FILE_EXTENSION_SUFFIX
# #         and FileHandler(
# #             location='%s%s' % (file.directory_path, file.basename)
# #         ).extension and file != cls.html_template_file):
        if(file.extension == TemplateParser.DEFAULT_FILE_EXTENSION_SUFFIX
        and FileHandler(
            location='%s%s' % (file.directory_path, file.basename)
        ).extension and not (file == cls.html_template_file)):
# #
            FileHandler(location='%s%s' % (
                file.directory_path, file.name[:-builtins.len('%s%s' % (
                    os.extsep, TemplateParser.DEFAULT_FILE_EXTENSION_SUFFIX))]
            )).content = cls._render_template_helper(file, mapping)
        return cls

    @classmethod
    def _render_html_templates(cls, mapping):
        '''Renders all frontend html templates.'''
        for site in ('frontend', 'backend'):
            '''
                NOTE: Only build and admin file if there exists an admin \
                section in frontend options.
            '''
            if site == 'frontend' or 'admin' in cls.options['frontend']:
                builtins.getattr(
                    cls, '%s_html_file' % site
                ).content = cls._render_template_helper(
                    cls.html_template_file, mapping,
                    force_backend=site == 'backend')
        return cls

    @classmethod
    def _render_template_helper(cls, file, mapping, force_backend=False):
        '''Renders a concrete template file.'''
        __logger__.debug('Render "%s".', file.path)
        is_backend = force_backend
        '''
            Check if any parent folder has the "backend" prefix to indicate \
            frontend or template scope for current template.
        '''
        if file.name.startswith('backend'):
            is_backend = True
        parent_folder = FileHandler(location=file.directory_path)
        while True:
            if parent_folder.name.startswith('backend'):
                is_backend = True
            if parent_folder == FileHandler.get_root() or is_backend:
                break
            parent_folder = FileHandler(
                location=parent_folder.directory_path)
        mapping['options']['frontend']['admin'] = ((is_backend) and
            'admin' in cls.options['frontend'])
        mapping = cls.controller.get_template_scope(deepcopy(mapping))
        if mapping['options']['frontend']['admin']:
            mapping['options']['frontend'] = Dictionary(
                mapping['options']['frontend']
            ).update(cls.options['frontend']['admin']).content
        return TemplateParser(
            file, template_context_default_indent=cls.options[
                'default_indent_level']
        ).render(mapping=mapping).output

    @classmethod
    def _check_database_file_references(cls):
        '''
            Checks if all file references saved in database records exists. \
            If a dead link was found the user will be asked for deleting \
            referenced database records.
        '''
        session = create_database_session(
            bind=cls.engine, expire_on_commit=False
        )()
        checked_paths = {}
        for model_name, model in Module.get_defined_objects(cls.model):
            if builtins.isinstance(
                model, builtins.type
            ) and builtins.issubclass(model, cls.model.Model):
                for property in model.__table__.columns:
                    if property.info and 'file_reference' in property.info:
                        for model_instance in session.query(model):
                            value = builtins.getattr(
                                model_instance, property.name)
                            if value is not None:
                                file_path = property.info['file_reference'] % \
                                    value
                                if(not (
                                    file_path in checked_paths or FileHandler(
                                        location=file_path)
                                ) and CommandLine.boolean_input(
                                    'Model %s has a dead file reference via '
                                    'attribute "%s" to "%s". Do you want to '
                                    'delete this record? {boolean_arguments}: '
                                    % (builtins.repr(
                                        model_instance
                                    ), property.name, file_path))
                                ):
                                    session.query(model).filter_by(
                                        **model_instance.dictionary
                                    ).delete()
                                    session.commit()
                                elif(file_path not in checked_paths or
                                     checked_paths[file_path] != model_name):
                                    checked_paths[file_path] = model_name
                                    __logger__.debug(
                                        'Check file reference "%s" for model '
                                        '"%s".', file_path, model_name)
        session.close()
        return cls

    @classmethod
    def _check_database_schema_version(cls, database_backup_file):
        '''Checke if the database schema has changed.'''
        if cls.model is None:
            return cls
        database_schema_file = FileHandler(
            location=cls.options['location']['database']['schema_file'])
        old_schemas = {}
        serialized_schema = ''
        if database_schema_file:
            serialized_schema = database_schema_file.content
            old_schemas = json.loads(
                serialized_schema, encoding=cls.options['encoding'])
        new_schemas = {}
        models = builtins.filter(
            lambda entity: builtins.isinstance(
                entity[1], builtins.type
            ) and builtins.issubclass(entity[1], cls.model.Model),
            Module.get_defined_objects(cls.model))
        session = create_database_session(
            bind=cls.engine, expire_on_commit=False
        )()
        for model_name, model in models:
            new_schemas[model.__tablename__] = builtins.str(CreateTable(
                model.__table__))
            # TODO Schemas can have equivalent different string
            # representations (in python3.4 at the latest!)
            if model.__tablename__ in old_schemas:
                if(old_schemas[model.__tablename__] !=
                   new_schemas[model.__tablename__]):
                    __logger__.info('Model "%s" has changed.', model_name)
                    temporary_table_name = '%s_temp' % model.__tablename__
                    while temporary_table_name in builtins.map(
                        lambda model: model[1].__tablename__, models
                    ):
                        temporary_table_name = '%s_temp' % temporary_table_name
                    __logger__.info(
                        'Create new temporary table "%s".',
                        temporary_table_name)
                    temporary_table = Table(
                        temporary_table_name, MetaData(bind=cls.engine))
                    old_columns = {}
                    for column in model.__table__.columns:
                        if column.name in old_schemas[model.__tablename__]:
                            old_columns[column.name] = builtins.getattr(
                                model, column.name)
                        temporary_table.append_column(column.copy())
                    for constraint in model.__table__.constraints:
                        '''
                            NOTE: Produces a warning. Constraints seems not \
                            to reference local columns. "constraint.copy()" \
                            is no option because the result loses the column \
                            bounding.
                        '''
                        temporary_table.append_constraint(constraint)
                    temporary_table.create(cls.engine)
                    session.commit()
                    __logger__.info(
                        'Transferring old records from "%s" to "%s".',
                        model.__tablename__, temporary_table_name)
                    '''
                        NOTE: We have to select all old column names \
                        explicitly because some properties may not exist in \
                        old database reflection.
                    '''
                    migration_successful = True
                    for values in session.query(*old_columns.values()):
                        __logger__.debug(
                            'Transferring record "%s".', '", "'.join(values))
                        try:
                            session.execute(temporary_table.insert(
                                builtins.dict(builtins.zip(
                                    old_columns.keys(), values))))
                        except builtins.Exception as exception:
                            __logger__.critical(
                                '%s: %s', exception.__class__.__name__,
                                builtins.str(exception))
                            migration_successful = False
                    session.commit()
                    if(migration_successful and
                       cls.options['database_engine_prefix'].startswith(
                           'sqlite:')):
                        __logger__.info(
                            'Drop old table "%s".', model.__tablename__)
                        '''
                            NOTE: We have to temporary remove foreign key \
                            checks.
                        '''
                        session.execute('PRAGMA foreign_keys=OFF;')
                        session.execute(DropTable(Table(
                            model.__tablename__, MetaData(bind=cls.engine))))
                        __logger__.info(
                            'Rename new table "%s" to old table name "%s".',
                            temporary_table_name, model.__tablename__)
                        session.execute('ALTER TABLE %s RENAME TO %s;' % (
                            temporary_table_name, model.__tablename__))
                        session.execute('PRAGMA foreign_key_check;')
                        session.execute('PRAGMA foreign_keys=ON;')
                        __logger__.info(
                            'Automatic migration of model "%s" was '
                            'successful.', model_name)
                    else:
                        __logger__.info(
                            'Please migrate table "%s" by hand or prepare '
                            'for next try.', model.__tablename__)
                        new_schemas[model.__tablename__] = \
                            old_schemas[model.__tablename__]
                    session.commit()
            elif model.__tablename__ not in old_schemas:
                __logger__.info('New model "%s" detected.', model_name)
                '''NOTE: sqlalchemy will create this table automatically.'''
        '''Load all existing table names from current database.'''
        cls.model.Model.metadata.reflect(cls.engine)
        for table_name in cls.model.Model.metadata.tables.keys():
            if table_name not in new_schemas and cls.engine.dialect.has_table(
                cls.engine.connect(), table_name
            ):
                session.execute(DropTable(Table(table_name, MetaData(
                    bind=cls.engine))))
                session.commit()
                __logger__.info('Table "%s" has been removed.', table_name)
# # python3.4
# #             database_schema_file.content = json.dumps(
# #                 new_schemas, sort_keys=True,
# #                 indent=cls.options['default_indent_level'])
            database_schema_file.content = json.dumps(
                new_schemas, encoding=cls.options['encoding'],
                sort_keys=True, indent=cls.options['default_indent_level'])
# #
        session.close()
        if(database_schema_file.content != serialized_schema and
           database_backup_file):
            now = DateTime.now()
# # python3.4
# #             time_stamp = now.timestamp() + now.microsecond / 1000 ** 2
            time_stamp = time.mktime(now.timetuple()) + \
                now.microsecond / 1000 ** 2
# #
            long_term_database_file = FileHandler(location='%s%s%d%s' % (
                database_backup_file.directory_path,
                database_backup_file.basename, time_stamp,
                database_backup_file.extension_suffix))
            __logger__.info(
                'Save long term database file "%s".',
                long_term_database_file.path)
            database_backup_file.copy(target=long_term_database_file)
        return cls

    @classmethod
    def _append_model_informations_to_options(cls):
        '''Appends validation strings to the global options object.'''
        cls.options['type'] = {}
        for model_name, model in Module.get_defined_objects(cls.model):
            name = model_name[0]
            if len(model_name) > 1:
                name += model_name[1:]
            if builtins.isinstance(
                model, builtins.type
            ) and builtins.issubclass(model, cls.model.Model):
                cls.options['type'][name] = {}
                for property in model.__table__.columns:
                    cls.options['type'][name][property.name] = {
                        'required': True}
                    if property.info:
                        cls.options['type'][name][property.name].update(
                            property.info)
                    if builtins.hasattr(
                        property.type, 'length'
                    ) and builtins.isinstance(
                        property.type.length, builtins.int
                    ):
                        cls.options['type'][name][property.name][
                            'maximum_length'
                        ] = property.type.length
                    if(builtins.hasattr(property, 'default') and
                       property.default is not None):
                        cls.options['type'][name][property.name][
                            'required'
                        ] = False
                        default_value = property.default.arg
                        if builtins.callable(default_value):
                            if builtins.hasattr(
                                cls.model,
                                'determine_language_specific_default_value'
                            ) and default_value == cls.model\
                                    .determine_language_specific_default_value:
# # python3.4
# #                                 default_value = Dictionary(cls.options[
# #                                     'model'
# #                                 ]['generic']['language_specific'][
# #                                     'default'
# #                                 ][property.name]).convert(
# #                                     key_wrapper=lambda key, value: cls
# #                                     .convert_for_client(String(
# #                                         key
# #                                     ).get_delimited_to_camel_case().content)
# #                                 ).content
                                default_value = Dictionary(cls.options[
                                    'model'
                                ]['generic']['language_specific'][
                                    'default'
                                ][property.name]).convert(
                                    key_wrapper=lambda key, value: cls
                                    .convert_for_client(builtins.unicode(
                                        String(
                                            key
                                        ).get_delimited_to_camel_case(
                                        ).content, boostNode.ENCODING))
                                ).content
# #
                            else:
                                default_value = property.default.arg(
                                    DefaultExecutionContext())
                                default_value = cls.convert_for_client(
                                    key=property.name, value=default_value)
                        else:
                            default_value = cls.convert_for_client(
                                key=property.name, value=default_value)
                        cls.options['type'][name][property.name][
                            'default_value'
                        ] = default_value
                    elif builtins.hasattr(
                        property, 'nullable'
                    ) and property.nullable:
                        cls.options['type'][name][property.name][
                            'required'
                        ] = False
        return cls

    @classmethod
    def _merge_options(cls):
        '''Merge frontend and backend options.'''
        cls.options = Dictionary(cls.options).update(
            cls.options['both']
        ).update(cls.options['backend']).content
        cls.options['frontend'] = Dictionary(cls.options['both']).update(
            cls.options['frontend']
        ).content
        return cls

    @classmethod
    def _set_options(cls):
        '''Renders backend and frontend options.'''
        cls.options = Dictionary(json.loads(FileHandler(
            location='/%s%s' % (cls.package_name, cls.CONFIGURATION_FILE_PATH)
        ).content)).content
        configuration_file = FileHandler(location=cls.CONFIGURATION_FILE_PATH)
        if configuration_file.is_file():
            return cls.extend_options(options=json.loads(
                configuration_file.content))
        return cls.consolidate_options()

    @SqlalchemyEvent.listens_for(SqlalchemyEngine, 'connect')
    def _set_sqlite_foreign_key_pragma(dbapi_connection, connection_record):
        '''Activates sqlite3 foreign key support.'''
        if builtins.isinstance(dbapi_connection, SQLite3Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute('PRAGMA foreign_keys=ON;')
            cursor.close()

    @classmethod
    def _initialize_model(cls):
        '''Initializes the model.'''
        if cls.options['database_engine_prefix'].startswith('sqlite:'):
            database_file = FileHandler(
                location=cls.options['location']['database']['url'])
            database_backup_file = FileHandler(
                location='%s%sBackup%s' % (
                    cls.options['location']['database']['backup'],
                    database_file.basename,
                    database_file.extension_suffix))
            if database_file:
                __logger__.info(
                    'Backup database "%s" to "%s".', database_file.path,
                    database_backup_file.path)
                database_file.copy(target=database_backup_file)
        cls.engine = create_database_engine('%s%s%s' % (
            cls.options['database_engine_prefix'], cls.ROOT_PATH,
            cls.options['location']['database']['url']
        ), echo=__logger__.isEnabledFor(logging.DEBUG))
        if cls.model is not None:
            cls.model.Model.metadata.create_all(cls.engine)
        '''Create a persistent inter thread database session.'''
        cls._check_database_schema_version(database_backup_file)
        cls._check_database_file_references()
        if cls.controller is not None:
            cls.controller.insert_needed_database_record()
            if cls.debug:
                cls.controller.insert_database_mockup()
        return cls

        # # endregion

        # endregion

        # region web server

    def _start_web_server(self):
        '''Starts the web server daemon as child thread.'''
        self.__class__.web_server = WebServer(
            port=self.given_command_line_arguments.port,
            **self.options['web_server'])
        if callable(getattr(self.controller, 'initialize_frontend', None)):
            self.controller.initialize_frontend()
        return self.wait_for_order()

    def _web_controller(self):
        '''Handles each request to the web server.'''
        cache_file = None
        output = ''
        mime_type = 'text/html'
        cache_control_header = 'public, max-age=0'
        if '__manifest__' in self.data['get']:
            mime_type = 'text/cache-manifest'
            cache_control_header = 'no-cache'
            '''Dynamic request should be handled by frontend cache.'''
            user = None
            manifest_name = 'generic'
            if(self.options['session']['key']['user_id'] in
               self.data['cookie'] and
               self.options['session']['key']['token'] in self.data['cookie']):
                users = self.session.query(self.model.User).filter(
                    self.model.User.id == self.data['cookie'][
                        self.options['session']['key']['user_id']])
                if users.count():
                    user = users.one()
                    manifest_name = user.id
            cache_file = FileHandler(
                location='%s%s.appcache' %
                (self.options['location']['web_cache'], manifest_name))
            if(self.given_command_line_arguments.web_cache and
               self.is_cached(cache_file)):
                __logger__.info('Response cache from "%s".', cache_file.path)
            else:
                cache_file.content = self.get_manifest(user)
        elif '__model__' in self.data['get']:
            mime_type = 'application/json'
            output = RestResponse(request=self).output
        elif '__offline__' in self.data['get']:
            __logger__.critical(
                'Ressource "%s" couldn\'t be determined by client.',
                self.data['get']['__offline__'])
        else:
            output, mime_type, cache_control_header, cache_file = \
                self.controller.response(
                    request=self, output=output, mime_type=mime_type,
                    cache_control_header=cache_control_header,
                    cache_file=cache_file)
        if cache_file:
            self._produce_cache_file_headers(
                cache_file, mime_type, cache_control_header)
            output = cache_file.content
        else:
            self.data['handler'].send_content_type_header(
                mime_type=mime_type
            ).send_static_file_cache_header(
                cache_control_header=cache_control_header)
        if self.new_cookie:
            self.data['handler'].send_cookie(
                self.new_cookie, maximum_age_in_seconds=self.options[
                    'maximum_cookie_age_in_seconds'])
        Print(output, end='')
        return self

    def _produce_cache_file_headers(
        self, cache_file, mime_type, cache_control_header
    ):
        '''Produces http headers for given server sided cache file.'''
        cache_timestamp = cache_file.timestamp
        if(mime_type != 'text/cache-manifest' and
           self.data['handler'].headers.get(
               'if-modified-since'
           ) == self.data['handler'].date_time_string(cache_timestamp)):
            __logger__.info(
                'Sent not modified header (304) for "%s".',
                cache_file.path)
            return self.data['handler'].send_content_type_header(
                response_code=304, mime_type=mime_type
            ).send_static_file_cache_header(
                timestamp=cache_timestamp,
                cache_control_header=cache_control_header)
        self.data['handler'].send_content_type_header(
            mime_type=mime_type
        ).send_static_file_cache_header(
            timestamp=cache_timestamp,
            cache_control_header=cache_control_header)
        return self

        # endregion

    # endregion

# endregion

# region footer

'''
    Preset some variables given by introspection letting the linter know what \
    globale variables are available.
'''
__logger__ = __exception__ = __module_name__ = __file_path__ = \
    __test_mode__ = __test_buffer__ = __test_folder__ = __test_globals__ = \
    __request_arguments__ = None
'''
    Extends this module with some magic environment variables to provide \
    better introspection support. A generic command line interface for some \
    code preprocessing tools is provided by default.
'''
Module.default(name=__name__, frame=inspect.currentframe())

# endregion

# region modline

# vim: set tabstop=4 shiftwidth=4 expandtab:
# vim: foldmethod=marker foldmarker=region,endregion:

# endregion
