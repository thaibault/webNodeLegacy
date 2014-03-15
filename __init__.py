#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# region header

'''
    Provides the main entry point for the web application. Initializes models \
    and starts the web socket.
'''

## python3.3 pass
from __future__ import print_function

__author__ = 'Torben Sickert'
__copyright__ = 'see module docstring'
__credits__ = 'Torben Sickert',
__license__ = 'see module docstring'
__maintainer__ = 'Torben Sickert'
__maintainer_email__ = 't.sickert@gmail.com'
__status__ = 'stable'
__version__ = '1.0'

import copy
from datetime import datetime as DateTime
from datetime import timedelta as TimeDelta
import inspect
import json
import logging
import multiprocessing
import re
import sys
## python3.3 pass
import time

from sqlalchemy import create_engine as create_sql_engine
from sqlalchemy.orm import sessionmaker as create_sql_session
from sqlalchemy.schema import CreateTable, DropTable, Table, MetaData

from boostNode.extension.file import Handler as FileHandler
from boostNode.extension.native import Module, Dictionary, String
from boostNode.extension.output import Print
from boostNode.extension.system import CommandLine, Runnable
from boostNode.extension.type import Null
from boostNode.paradigm.objectOrientation import Class
from boostNode.runnable.server import Web as WebServer
from boostNode.runnable.template import Parser as TemplateParser
from boostNode.runnable.template import __exception__ as TemplateError

from controller import Main as Controller
from restController import Response as RestResponse

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
    web_server = None
    '''Saves the web server instance.'''
    debug = False
    '''Indicates weather the application is currently in debug mode.'''
    given_command_line_arguments = None
    '''Holds all given commend line arguments in a named tuple.'''
    session = None
    '''
        Holds the orm database session instance. NOTE: There is a class and
        instance binded session.
    '''
    options = {}
    '''Holds the backend and frontend specific options.'''
    model = None
    '''Holds the model module.'''
    web_api_lock = multiprocessing.Lock()
    '''
        A lock to acquire if workers should be finished before application \
        can be closed.
    '''
    index_html_file = None
    '''Holds the main entry file for bootstrapping the web application.'''

    # endregion

    # region public methods

        # region static

    @classmethod
    def is_valid_web_asset(cls, file):
        '''Checks if the given file is a valid web application asset.'''
        for pattern in cls.options['ignore_web_asset_pattern']:
            if re.compile(pattern).match(file.name):
                return False
        return True

    @classmethod
    def is_cached(cls, cache_file):
        '''Determines weather given file is a valid usable cache file.'''
        return (sys.flags.optimize and not cls.debug) and cache_file

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
            path = cls.options['web_asset_path']
            cls._root_asset_path_len = len(FileHandler(path).path)
        for file in FileHandler(path):
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
        for file in FileHandler(path):
            if cls.is_valid_web_asset(file):
                if file.is_directory():
                    version += cls.get_timestamps(file.path)
                else:
                    version += file.timestamp
        return version

        # endregion

    def stop(self, *arguments, **keywords):
        '''
            This method is triggered if the application should die, The web \
            server will be closed.
        '''
        if self.web_server:
            '''
                Take this method type by the abstract class via introspection.
            '''
            with self.web_api_lock:
                getattr(self.web_server, inspect.stack()[0][3])(
                    *arguments, **keywords)
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
        FileHandler(self.options['web_asset_path']).iterate_directory(
            add_asset_file, recursive=True)
        offline_manifest_template_file = FileHandler(
            self.options['offline_manifest_template_file_path'])
        '''Dynamic request should be handled by frontend cache.'''
        requests = ()
        account_state = 1
        if user is not None:
            account_state = hash(
                Dictionary(user.dictionary).get_immutable())
        return TemplateParser(
            offline_manifest_template_file,
            template_context_default_indent=
            self.options['default_indent_level']
        ).render(
            asset_files=asset_files, requests=requests,
            index_html_file=self.index_html_file,
            asset_version=self.get_timestamps(self.options['web_asset_path']),
            version='%s - %d' % (__version__, FileHandler(Module.get_name(
                path=True, extension=True, frame=inspect.currentframe()
            )).timestamp), account_state=account_state,
            request_file_name=__name__, host=self.request['handler'].host
        ).output

    # endregion

    # region protected methods

        # region runnable implementation

    def _initialize(self):
        '''Starts the web controller if already started.'''

            # region properties

        self.request = __request_arguments__
        self.new_cookie = {}
        '''Normalize get and payload data.'''
## python3.3
##         self.request['get'] = Dictionary(self.request['get']).convert(
##             key_wrapper=lambda key, value: String(
##                 key
##             ).camel_case_to_delimited().content if isinstance(
##                 key, str
##             ) else self._convert_for_backend(key),
##             value_wrapper=self._convert_for_backend
##         ).content
##         self.request['data'] = Dictionary(self.request['data']).convert(
##             key_wrapper=lambda key, value: String(
##                 key
##             ).camel_case_to_delimited().content if isinstance(
##                 key, str
##             ) else self._convert_for_backend(key),
##             value_wrapper=self._convert_for_backend
##         ).content
        self.request['get'] = Dictionary(self.request['get']).convert(
            key_wrapper=lambda key, value: String(
                key
            ).camel_case_to_delimited().content if isinstance(
                key, (str, unicode)
            ) else self._convert_for_backend(key),
            value_wrapper=self._convert_for_backend
        ).content
        self.request['data'] = Dictionary(self.request['data']).convert(
            key_wrapper=lambda key, value: String(
                key
            ).camel_case_to_delimited().content if isinstance(
                key, (str, unicode)
            ) else self._convert_for_backend(key),
            value_wrapper=self._convert_for_backend
        ).content
##
        '''Holds the current request handler server instance.'''
        self.session = create_sql_session(bind=self.engine)()
        if self.options['authentication'] == 'advanced':
            self.authorized_user = self._authenticate()

            # endregion

        try:
            self._web_controller()
        except TemplateError as exception:
            if self.debug:
                self.request['handler'].send_error(
                    500, '%s: "%s"' % (
                        exception.__class__.__name__, str(exception)))
            else:
                # NOTE: The web server will handle this.
                raise
        finally:
            self.session.commit()
        return self

    def _run(self):
        '''Initializes the web server.'''

            # region properties

        FileHandler.set_root(location=FileHandler(FileHandler(
            Module.get_name(
                frame=inspect.currentframe(), path=True, extension=True),
            output_with_root_prefix=True
        ).directory_path).directory_path)
        self.__class__.ROOT_PATH = FileHandler.get_root().path
        self._set_options()
        self.__class__.given_command_line_arguments = \
            CommandLine.argument_parser(
                arguments=self.options['command_line_arguments'],
                module_name=__name__)
        self.__class__.debug = \
            sys.flags.debug or __logger__.isEnabledFor(logging.DEBUG)
        self.__class__.model = __import__('model')
        self._append_validation_to_options()
        self.__class__.index_html_file = FileHandler(
            self.options['index_html_file_path'])
        self.__class__.controller = None

            # endregion

        __logger__.info('Sandbox application into "%s".', self.ROOT_PATH)
        __logger__.info(
            'Application is running in %s mode.',
            'performance' if sys.flags.optimize else 'normal')
        if(self.debug or self.given_command_line_arguments.render_template or
           not self.index_html_file):
            __logger__.info('Render main entry html file.')
            self.index_html_file.content = TemplateParser(
                self.options['template_index_file_path'],
                template_context_default_indent=
                self.options['default_indent_level']
            ).render(
                request_file_name=__name__, options=self.options['frontend'],
                debug=self.debug,
                deployment=self.given_command_line_arguments.render_template
            ).output
        if self.given_command_line_arguments.render_template:
            return self
        __logger__.info(
            'Clear web cache in "%s".', self.options['web_cache_path'])
        for file in FileHandler(self.options['web_cache_path']):
            if self.is_valid_web_asset(file):
                file.remove_deep()
        __logger__.info(
            'Initialize database on "%s".', self.options['database_file_path'])
        self._initialize_model()
        self.__class__.controller = Controller(web_handler=self)
        return self._start_web_server()

        # endregion

        # region helper methods

            # region static

    @classmethod
    def _check_database_schema_version(cls):
        '''Checke if the database schema has changed.'''
        database_schema_file = FileHandler(
            cls.options['database_schema_file_path'])
        old_schemas = {}
        if database_schema_file:
## python3.3
##             old_schemas = json.loads(
##                 database_schema_file.content,
##                 encoding=cls.options['encoding'])
            old_schemas = Dictionary(json.loads(
                database_schema_file.content,
                encoding=cls.options['encoding'])
            ).convert(
                key_wrapper=lambda key, value: cls._convert_byte_to_string(
                    key),
                value_wrapper=
                lambda key, value: cls._convert_byte_to_string(value)
            ).content
##
        new_schemas = {}
        for model_name, model in Module.get_defined_objects(cls.model):
            if isinstance(model, type) and issubclass(model, cls.model.Model):
                new_schemas[model.__tablename__] = str(CreateTable(
                    model.__table__))
                if not model.__tablename__ in old_schemas:
                    __logger__.info('New model "%s" detected.', model_name)
                    '''
                        NOTE: sqlalchemy will create this table automatically.
                    '''
                elif(old_schemas[model.__tablename__] !=
                     new_schemas[model.__tablename__]):
                    __logger__.info('Model "%s" has changed.', model_name)
                    # TODO
        for table_name in old_schemas:
            if not table_name in new_schemas:
                __logger__.info('Table "%s" has been removed.', table_name)
                cls.session.execute(DropTable(Table(table_name, MetaData(
                    bind=cls.engine))))
## python3.3
##         database_schema_file.content = json.dumps(
##             new_schemas, sort_keys=True,
##             indent=cls.options['default_indent_level'])
        database_schema_file.content = json.dumps(
            new_schemas, encoding=cls.options['encoding'], sort_keys=True,
            indent=cls.options['default_indent_level'])
##
        return cls

    @classmethod
    def _append_validation_to_options(cls):
        '''Appends validation strings to the global options object.'''
        cls.options['both']['model'] = {}
        for model_name, model in Module.get_defined_objects(cls.model):
            if isinstance(model, type) and issubclass(model, cls.model.Model):
                cls.options['both']['model'][model_name] = {}
                for property in model.__table__.columns:
                    if property.info:
                        cls.options['both']['model'][model_name][
                            property.name
                        ] = property.info
                        cls.options['both']['model'][model_name][
                            property.name
                        ].update({
                            'maximum_length': 2 ** 32, 'minimum_length': 0})
                        if hasattr(property.type, 'length') and isinstance(
                            property.type.length, int
                        ):
                            cls.options['both']['model'][model_name][
                                property.name
                            ]['maximum_length'] = property.type.length
        return cls._set_options()

    @classmethod
    def _set_options(cls):
        '''Renders backend and frontend options.'''
        global OPTIONS
        if not cls.options:
            cls.options = json.loads(
                FileHandler(cls.CONFIGURATION_FILE_PATH).content)
        cls.options.update(cls.options['both'])
        cls.options.update(cls.options['backend'])
        cls.options['frontend'].update(cls.options['both'])
        cls.options['moduleName'] = __name__
        cls.options = Dictionary(cls.options).convert(
            key_wrapper=lambda key, value: cls._convert_for_backend(key),
            value_wrapper=cls._convert_for_backend
        ).content
        mapping = copy.copy(cls.options['frontend'])
        mapping.update(cls.options)
        '''
            NOTE: We have to run over options twice to handle cyclic \
            dependencies.
        '''
        for number in range(2):
## python3.3
##             cls.options = Dictionary(cls.options).convert(
##                 value_wrapper=lambda key, value: TemplateParser(
##                     value, string=True
##                 ).render(
##                     mapping=mapping, module_name=__name__, web_handler=cls
##                 ).output if isinstance(value, str) else value
##             ).content
            cls.options = Dictionary(cls.options).convert(
                value_wrapper=lambda key, value: TemplateParser(
                    value, string=True
                ).render(
                    mapping=mapping, module_name=__name__, web_handler=cls
                ).output if isinstance(value, (unicode, str)) else value
            ).content
##
        cls.options = Dictionary(cls.options).convert(
            key_wrapper=lambda key, value: String(key).camel_case_to_delimited(
            ).content, value_wrapper=cls._convert_for_backend
        ).content
        cls.options['frontend'] = Dictionary(cls.options['frontend']).convert(
            key_wrapper=lambda key, value: cls._convert_for_client(String(
                key
            ).delimited_to_camel_case().content)
        ).content
        cls.options['session_expiration_time'] = TimeDelta(
            minutes=cls.options['session_expiration_time_in_minutes'])
        '''
            Export Options to global scope to make accessible for other \
            modules like the model.
        '''
        OPTIONS = cls.options
        return cls

    @classmethod
    def _initialize_model(cls):
        '''Initializes the model.'''
        cls.engine = create_sql_engine('sqlite:///%s%s' % (
            cls.ROOT_PATH, cls.options['database_file_path']
        ), echo=cls.debug)
        cls.model.Model.metadata.create_all(cls.engine)
        cls.session = create_sql_session(bind=cls.engine)()
        cls._check_database_schema_version()
        cls.controller.insert_database_mockups()
        cls.session.commit()
        return cls

    @classmethod
    def _convert_byte_to_string(cls, value):
        '''Converts a byte object to a python string.'''
## python3.3
##         if isinstance(value, bytes):
##             return value.decode(cls.options['encoding'])
        if isinstance(value, unicode):
            return value.encode(cls.options['encoding'])
##
        return value

    @classmethod
    def _convert_for_client(cls, key, value=Null):
        '''Returns the serialized version of given value.'''
        key = cls._convert_byte_to_string(key)
        value = cls._convert_byte_to_string(value)
        if value is Null:
            value = key
        else:
            if isinstance(value, DateTime):
## python3.3                 return value.timestamp()
                return time.mktime(value.timetuple())
            if key == 'language' or key.endswith('_language'):
                return String(value).delimited_to_camel_case(
                ).content[:-1] + value[-1].upper()
        if isinstance(value, str):
            return re.compile('([a-z])Id([A-Z]|$)').sub('\\1ID\\2', value)
        elif value is None:
            return ''
        elif not isinstance(value, int):
            return str(value)
        return value

    @classmethod
    def _convert_for_backend(cls, key, value=Null):
        '''Converts data from client to python specific data objects.'''
        key = cls._convert_byte_to_string(key)
        value = cls._convert_byte_to_string(value)
        if value is Null:
            value = key
        elif isinstance(key, str):
            if key == 'date_time' or key.endswith('_date_time'):
                return DateTime.fromtimestamp(value)
            if key == 'language' or key.endswith('_language'):
                return String(value).camel_case_to_delimited().content
        try:
            return int(value)
        except(TypeError, ValueError):
            return value

            # endregion

    def _authenticate(self):
        '''
            Authenticates a user by potential sent header identification data.
        '''
## python3.3
##         user_id = self.request['handler'].headers.get(
##             '%s-User-ID' % self.options['session_data_description_prefix'])
##         session_token = self.request['handler'].headers.get(
##             '%s-Session-Token' %
##             self.options['session_data_description_prefix'])
        user_id = self.request['handler'].headers.getheader(
            '%s-User-ID' % self.options['session_data_description_prefix'])
        session_token = self.request['handler'].headers.getheader(
            '%s-Session-Token' %
            self.options['session_data_description_prefix'])
##
        result = None
        if user_id and session_token:
            users = self.session.query(
                self.model.User
            ).filter(
                self.model.User.id == user_id,
                self.model.User.session_token == session_token,
                self.model.User.session_expiration_date_time > DateTime.now())
            if users.count():
                result = users.one()
                result.session_expiration_date_time = DateTime.now(
                ) + self.options['session_expiration_time']
                __logger__.info(
                    'Authorize user "%s" (id: %d) for %d hours.',
                    result.e_mail_address, result.id, (
                        self.options['session_expiration_time'].total_seconds()
                        / 60) / 60)
        return result

        # endregion

        # region web server

    def _start_web_server(self):
        '''Starts the web server daemon as child thread.'''
        self.__class__.web_server = WebServer(
            port=self.given_command_line_arguments.port,
            **self.options['web_server'])
        return self.wait_for_order()

    def _web_controller(self):
        '''Handles each request to the web server.'''
        cache_file = None
        output = ''
        mime_type = 'text/html'
        cache_control = 'public, max-age=0'
        if 'manifest' in self.request['get']:
            mime_type = 'text/cache-manifest'
            cache_control = 'no-cache'
            '''Dynamic request should be handled by frontend cache.'''
            user = None
            manifest_name = 'generic'
            if(self.options['user_id_key'] in self.request['cookie'] and
               self.options['session_token_key'] in self.request['cookie']):
                user = self.session.query(self.model.Model).filter(
                    self.model.User.id ==
                    self.request['cookie'][self.options['user_id_key']],
                    self.model.User.session_token ==
                    self.request['cookie'][self.options['session_token_key']]
                ).one().dictionary
                manifest_name = user.id
            cache_file = FileHandler(
                '%s%s.appcache' %
                (self.options['web_cache_path'], manifest_name))
            if(self.given_command_line_arguments.web_cache and
               self.is_cached(cache_file)):
                __logger__.info('Response cache from "%s".', cache_file.path)
            else:
                cache_file.content = self.get_manifest(user)
        elif 'model' in self.request['get']:
            mime_type = 'application/json'
            output = RestResponse(web_handler=self).output
        elif 'offline' in self.request['get']:
            __logger__.critical(
                'Ressource "%s" couldn\'t be determined by client.',
                self.request['get']['offline'])
        if cache_file:
            self._produce_cache_file_headers(
                cache_file, mime_type, cache_control)
            output = cache_file.content
        else:
            self.request['handler'].send_content_type_header(
                mime_type=mime_type
            ).send_static_file_cache_header(cache_control=cache_control)
        if self.new_cookie:
            self.request['handler'].send_cookie(
                self.new_cookie, maximum_age_in_seconds=
                self.options['maximumCookieAgeInSeconds'])
        Print(output, end='')
        return self

    def _produce_cache_file_headers(
        self, cache_file, mime_type, cache_control
    ):
        '''Produces http headers for given server sided cache file.'''
        cache_timestamp = cache_file.timestamp
## python3.3
##         if(mime_type != 'text/cache-manifest' and
##            self.request['handler'].headers.get('If-Modified-Since') ==
##            self.request['handler'].date_time_string(cache_timestamp)):
        if(mime_type != 'text/cache-manifest' and
           self.request['handler'].headers.getheader(
               'If-Modified-Since'
           ) == self.request['handler'].date_time_string(
                cache_timestamp)):
##
            __logger__.info(
                'Sent not modified header (304) for "%s".',
                cache_file.path)
            return self.request['handler'].send_content_type_header(
                response_code=304, mime_type=mime_type
            ).send_static_file_cache_header(
                timestamp=cache_timestamp, cache_control=cache_control)
        self.request['handler'].send_content_type_header(
            mime_type=mime_type
        ).send_static_file_cache_header(
            timestamp=cache_timestamp, cache_control=cache_control)
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
