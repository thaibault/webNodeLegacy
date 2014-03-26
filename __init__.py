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

from copy import copy
from datetime import datetime as DateTime
from datetime import time as Time
from datetime import date as Date
from datetime import timedelta as TimeDelta
import inspect
import json
import logging
import multiprocessing
import re
import sys
## python3.3 pass
import time

from sqlalchemy.engine.default import DefaultExecutionContext
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
    data_wrapper = {}
    '''Holds a mapping to convert dictionaries for frontend.'''

    # endregion

    # region public methods

        # region static

            # region boolean

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
        return(sys.flags.optimize and not cls.debug) and cache_file

            # endregion

            # region helper

    @classmethod
    def clear_web_cache(cls):
        '''Clears all web cache files.'''
        __logger__.info(
            'Clear web cache in "%s".', cls.options['location']['web_cache'])
        for file in FileHandler(cls.options['location']['web_cache']):
            if cls.is_valid_web_asset(file):
                file.remove_deep()
        return cls

    @classmethod
    def convert_byte_to_string(cls, value):
        '''Converts a byte object to a python string.'''
## python3.3
##         if isinstance(value, bytes):
##             return value.decode(cls.options['encoding'])
        if isinstance(value, unicode):
            return value.encode(cls.options['encoding'])
##
        return value

    @classmethod
    def convert_for_client(cls, key, value=Null):
        '''Returns the serialized version of given value.'''
        key = cls.convert_byte_to_string(key)
        value = cls.convert_byte_to_string(value)
        if value is Null:
            value = key
        else:
## python3.3
##             if isinstance(value, Date):
##                 return int(time.mktime(value.timetuple()))
##             if isinstance(value, DateTime):
##                 return value.timestamp()
            if isinstance(value, (Date, DateTime)):
                return int(time.mktime(value.timetuple()))
##
            if isinstance(value, Time):
                return 60 ** 2 * value.hour + 60 * value.minute + value.second
            if(key == 'language' or key.endswith('_language')) and re.compile(
                '[a-z]{2}_[a-z]{2}$'
            ).match(value):
                return String(value).delimited_to_camel_case(
                ).content[:-1] + value[-1].upper()
        if value is None:
            return ''
        elif not isinstance(value, (int, float)):
            return str(value)
        return value

    @classmethod
    def convert_for_backend(cls, key, value=Null):
        '''Converts data from client to python specific data objects.'''
        key = cls.convert_byte_to_string(key)
        value = cls.convert_byte_to_string(value)
        if value is Null:
            value = key
        elif isinstance(key, str):
            if key == 'date_time' or key.endswith('_date_time'):
                if isinstance(value, int):
                    return DateTime.fromtimestamp(value)
                elif isinstance(value, str):
                    for delimiter in ('.', '/'):
                        for year_format in ('%y', '%Y'):
                            for microsecond_format in ('', ':%f'):
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
                                                microsecond=microsecond_format))
                                    except ValueError:
                                        pass
            if key == 'date' or key.endswith('_date'):
                if isinstance(value, int):
                    return Date.fromtimestamp(value)
                elif isinstance(value, str):
                    for delimiter in ('.', '/'):
                        for year_format in ('%y', '%Y'):
                            for date_format in (
                                '%x', '%d{delimiter}%m{delimiter}{year}',
                                '%m{delimiter}%d{delimiter}{year}',
                                '%w{delimiter}%m{delimiter}{year}'
                            ):
                                try:
## python3.3
##                                     return Date.fromtimestamp(
##                                         DateTime.strptime(
##                                             value, date_format.format(
##                                                 delimiter=delimiter,
##                                                 year=year_format
##                                             )).timestamp())
                                    return Date.fromtimestamp(time.mktime(
                                        DateTime.strptime(
                                            value, date_format.format(
                                                delimiter=delimiter,
                                                year=year_format
                                            )).timetuple()))
##
                                except ValueError:
                                    pass
            if key == 'time' or key.endswith('_time'):
                if isinstance(value, int):
                    return DateTime.fromtimestamp(value).time()
                elif isinstance(value, str):
                    for microsecond_format in ('', ':%f'):
                        try:
                            return DateTime.strptime(
                                value, '%X{microsecond}'.format(
                                    microsecond=microsecond_format))
                        except ValueError:
                            pass
            if(key == 'language' or key.endswith('_language')) and re.compile(
                '[a-z]{2}[A-Z]{2}'
            ).match(value):
                return String(value).camel_case_to_delimited().content
        if isinstance(value, str):
            try:
                return int(value)
            except(TypeError, ValueError):
                try:
                    return float(value)
                except(TypeError, ValueError):
                    return value
        return value

            # endregion

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
        FileHandler(self.options['location']['web_asset']).iterate_directory(
            add_asset_file, recursive=True)
        offline_manifest_template_file = FileHandler(
            self.options['location']['offline_manifest_template_file'])
        account_state = 1
        account_data = {}
        if user is not None:
            account_state = hash(
                Dictionary(user.dictionary).get_immutable())
            account_data = user.dictionary
        return TemplateParser(
            offline_manifest_template_file,
            template_context_default_indent=
            self.options['default_indent_level']
        ).render(
            asset_files=asset_files, index_html_file=self.index_html_file,
            asset_version=self.get_timestamps(
                self.options['location']['web_asset']),
            version='%s - %d' % (__version__, FileHandler(Module.get_name(
                path=True, extension=True, frame=inspect.currentframe()
            )).timestamp), account_state=account_state,
            request_file_name=__name__, host=self.data['handler'].host,
            account_data=account_data,
            offline_manifest_template_file=offline_manifest_template_file,
            mapping=self.controller.get_manifest_scope(request=self, user=user)
        ).output

    # endregion

    # region protected methods

        # region runnable implementation

    def _initialize(self):
        '''Starts the web controller if already started.'''

            # region properties

        self.data = __request_arguments__
        self.new_cookie = {}
        '''Normalize get and payload data.'''
## python3.3
##         self.data['get'] = Dictionary(self.data['get']).convert(
##             key_wrapper=lambda key, value: String(
##                 key
##             ).camel_case_to_delimited().content if isinstance(
##                 key, str
##             ) else self.convert_for_backend(key),
##             value_wrapper=self.convert_for_backend
##         ).content
##         self.data['data'] = Dictionary(self.data['data']).convert(
##             key_wrapper=lambda key, value: String(
##                 key
##             ).camel_case_to_delimited().content if isinstance(
##                 key, str
##             ) else self.convert_for_backend(key),
##             value_wrapper=self.convert_for_backend
##         ).content
        self.data['get'] = Dictionary(self.data['get']).convert(
            key_wrapper=lambda key, value: String(
                key
            ).camel_case_to_delimited().content if isinstance(
                key, (str, unicode)
            ) else self.convert_for_backend(key),
            value_wrapper=self.convert_for_backend
        ).content
        self.data['data'] = Dictionary(self.data['data']).convert(
            key_wrapper=lambda key, value: String(
                key
            ).camel_case_to_delimited().content if isinstance(
                key, (str, unicode)
            ) else self.convert_for_backend(key),
            value_wrapper=self.convert_for_backend
        ).content
##
        '''Holds the current request handler server instance.'''
        self.session = create_sql_session(bind=self.engine)()
        self.authorized_user = self._authenticate()

            # endregion

        try:
            self._web_controller()
        except TemplateError as exception:
            if self.debug:
                self.data['handler'].send_error(
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
        self.__class__.controller = Controller(main=self.__class__)
        self._set_options()
        self.__class__.given_command_line_arguments = \
            CommandLine.argument_parser(
                arguments=self.options['command_line_arguments'],
                module_name=__name__)
        self.__class__.debug = \
            sys.flags.debug or __logger__.isEnabledFor(logging.DEBUG)
        self.__class__.model = __import__('model')
        self._append_model_informations_to_options()
        self.__class__.index_html_file = FileHandler(
            self.options['location']['index_html_file'])
        self.__class__.frontend_data_wrapper = {
            'key_wrapper': lambda key, value: self.convert_for_client(String(
                key
            ).delimited_to_camel_case().content),
            'value_wrapper': self.convert_for_client}
        self.__class__.backend_data_wrapper = {
            'key_wrapper': lambda key, value: self.convert_for_backend(String(
                key
            ).camel_case_to_delimited().content),
            'value_wrapper': self.convert_for_backend}

            # endregion

        __logger__.info('Sandbox application into "%s".', self.ROOT_PATH)
        __logger__.info(
            'Application is running in %s mode.',
            'performance' if sys.flags.optimize else 'normal')
        if(self.debug or self.given_command_line_arguments.render_template or
           not self.index_html_file):
            __logger__.info('Render main entry html file.')
            index_file = FileHandler(
                self.options['location']['template_index_file'])
            if index_file.is_file():
                self.index_html_file.content = TemplateParser(
                    self.options['location']['template_index_file'],
                    template_context_default_indent=
                    self.options['default_indent_level']
                ).render(
                    options=self.options['frontend'],
                    debug=self.debug, deployment=
                    self.given_command_line_arguments.render_template,
                    mapping=self.controller.get_frontend_scope()
                ).output
        if self.given_command_line_arguments.render_template:
            return self
        self.clear_web_cache()
        __logger__.info(
            'Initialize database on "%s".',
            self.options['location']['database_file'])
        self._initialize_model()
        self.controller.initialize()
        return self._start_web_server()

        # endregion

        # region helper methods

            # region static

    @classmethod
    def _check_database_schema_version(cls):
        '''Checke if the database schema has changed.'''
        database_schema_file = FileHandler(
            cls.options['location']['database_schema_file'])
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
                key_wrapper=lambda key, value: cls.convert_byte_to_string(
                    key),
                value_wrapper=
                lambda key, value: cls.convert_byte_to_string(value)
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
    def _append_model_informations_to_options(cls):
        '''Appends validation strings to the global options object.'''
        cls.options['type'] = {}
        for model_name, model in Module.get_defined_objects(cls.model):
            if isinstance(model, type) and issubclass(model, cls.model.Model):
                cls.options['type'][model_name] = {}
                for property in model.__table__.columns:
                    cls.options['type'][model_name][property.name] = {}
                    if property.info:
                        cls.options['type'][model_name][property.name] = copy(
                            property.info)
                    if hasattr(property.type, 'length') and isinstance(
                        property.type.length, int
                    ):
                        cls.options['type'][model_name][property.name][
                            'maximum_length'
                        ] = property.type.length
                    if(hasattr(property, 'default') and
                       property.default is not None):
                        default_value = property.default.arg
                        if callable(default_value):
                            if hasattr(
                                cls.model,
                                'determine_language_specific_default_value'
                            ) and default_value == cls.model\
                                    .determine_language_specific_default_value:
                                default_value = Dictionary(cls.options[
                                    'model'
                                ]['generic']['language_specific'][
                                    'default'
                                ][property.name]).convert(
                                    key_wrapper=lambda key, value: cls
                                    .convert_for_client(String(
                                        key
                                    ).delimited_to_camel_case().content)
                                ).content
                            else:
                                default_value = property.default.arg(
                                    DefaultExecutionContext())
                                default_value = cls.convert_for_client(
                                    key=property.name, value=default_value)
                        else:
                            default_value = cls.convert_for_client(
                                key=property.name, value=default_value)
                        cls.options['type'][model_name][property.name][
                            'default_value'
                        ] = default_value
        cls.options['both']['type'] = cls.options['frontend']['type'] = \
            cls.options['type']
        '''
            NOTE: Frontend options could only be extended after they where \
            merged. So don't exchange these lines.
        '''
        cls.options['frontend']['type'] = Dictionary(
            cls.options['frontend']['type']
        ).convert(
            key_wrapper=lambda key, value: cls.convert_for_client(String(
                key
            ).delimited_to_camel_case().content)
        ).content
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
        global OPTIONS
        cls.options = Dictionary(json.loads(FileHandler(
            '/%s/%s' % (__name__, cls.CONFIGURATION_FILE_PATH)
        ).content)).update(json.loads(
            FileHandler(cls.CONFIGURATION_FILE_PATH).content
        )).content
        cls._merge_options().options['moduleName'] = __name__
        cls.options = Dictionary(cls.options).convert(
            key_wrapper=lambda key, value: cls.convert_for_backend(key),
            value_wrapper=cls.convert_for_backend
        ).content
        mapping = copy(cls.options['frontend'])
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
##                     mapping=mapping, module_name=__name__, main=cls
##                 ).output if isinstance(value, str) else value
##             ).content
            cls.options = Dictionary(cls.options).convert(
                value_wrapper=lambda key, value: TemplateParser(
                    value, string=True
                ).render(
                    mapping=mapping, module_name=__name__, main=cls
                ).output if isinstance(value, (unicode, str)) else value
            ).content
##
        cls.options = Dictionary(cls.options).convert(
            key_wrapper=lambda key, value: String(key).camel_case_to_delimited(
            ).content, value_wrapper=cls.convert_for_backend
        ).content
        String.abbreviations = cls.options['abbreviations']
        cls.options['frontend'] = Dictionary(cls.options['frontend']).convert(
            key_wrapper=lambda key, value: cls.convert_for_client(String(
                key
            ).delimited_to_camel_case().content)
        ).content
        cls.options['session']['expiration_interval'] = TimeDelta(
            minutes=cls.options['session']['expiration_time_in_minutes'])
        if 'authentication_handler' in cls.options['web_server']:
## python3.3
##             cls.options['web_server']['authentication_handler'] = exec(
##                 cls.options['web_server']['authentication_handler'],
##                 {'controller': cls.controller})
            cls.options['web_server']['authentication_handler'] = eval(
                cls.options['web_server']['authentication_handler'],
                {'controller': cls.controller})
##
        cls.options['model']['generic']['language']['default'] = String(
            cls.options['model']['generic']['language']['default']
        ).camel_case_to_delimited().content
        '''
            Export options to global scope to make them accessible for other \
            modules like model or controller.
        '''
        OPTIONS = cls.options
        return cls

    @classmethod
    def _initialize_model(cls):
        '''Initializes the model.'''
        cls.engine = create_sql_engine('%s%s%s' % (
            cls.options['database_engine_prefix'], cls.ROOT_PATH,
            cls.options['location']['database_file']
        ), echo=cls.debug)
        cls.model.Model.metadata.create_all(cls.engine)
        cls.session = create_sql_session(bind=cls.engine)()
        cls._check_database_schema_version()
        if cls.debug:
            cls.controller.insert_database_mockup()
        cls.session.commit()
        return cls

            # endregion

    def _authenticate(self):
        '''
            Authenticates a user by potential sent header identification data.
        '''
        user_id = session_token = None
        if self.options['authentication_method'] == 'header':
## python3.3
##             user_id = self.data['handler'].headers.get(String(
##                 self.options['session']['key']['user_id']
##             ).camel_case_to_delimited(delimiter='-').content
##             session_token = self.data['handler'].headers.get(String(
##                 self.options['session']['key']['token'])
##             ).camel_case_to_delimited(delimiter='-').content
            user_id = self.data['handler'].headers.getheader(String(
                self.options['session']['key']['user_id']
            ).camel_case_to_delimited(delimiter='-').content)
            session_token = self.data['handler'].headers.getheader(String(
                self.options['session']['key']['token']
            ).camel_case_to_delimited(delimiter='-').content)
##
        elif(self.options['authentication_method'] == 'cookie' and
             self.options['session']['key']['user_id'] in self.data[
                'cookie'
             ] and self.options['session']['key']['token_key'] in self.data[
                'cookie']):
            user_id = self.data['cookie'][self.options['session']['key'][
                'user_id']]
            session_token = \
                self.data['cookie'][self.options['session']['key']['token']]
        result = None
        if user_id and session_token:
            users = self.session.query(self.model.User).filter(
                self.model.User.id == user_id,
                self.model.User.session_token == session_token,
                self.model.User.session_expiration_date_time > DateTime.now())
            if users.count():
                result = users.one()
                result.session_expiration_date_time = DateTime.now(
                ) + self.options['session']['expiration_interval']
                __logger__.info(
                    'Authorize user "%s" (id: %d) for %d hours.',
                    result.e_mail_address, result.id, (
                        self.options['session'][
                            'expiration_interval'
                        ].total_seconds() / 60
                    ) / 60)
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
        if 'manifest' in self.data['get']:
            mime_type = 'text/cache-manifest'
            cache_control = 'no-cache'
            '''Dynamic request should be handled by frontend cache.'''
            user = None
            manifest_name = 'generic'
            if(self.options['session']['key']['user_id'] in self.data['cookie'] and
               self.options['session']['key']['token'] in self.data['cookie']):
                user = self.session.query(self.model.Model).filter(
                    self.model.User.id ==
                    self.data['cookie'][self.options['user_id_key']],
                    self.model.User.session_token ==
                    self.data['cookie'][self.options['session']['key']['token']]
                ).one().dictionary
                manifest_name = user.id
            cache_file = FileHandler(
                '%s%s.appcache' %
                (self.options['location']['web_cache'], manifest_name))
            if(self.given_command_line_arguments.web_cache and
               self.is_cached(cache_file)):
                __logger__.info('Response cache from "%s".', cache_file.path)
            else:
                cache_file.content = self.get_manifest(user)
        elif 'model' in self.data['get']:
            mime_type = 'application/json'
            output = RestResponse(request=self).output
        elif 'offline' in self.data['get']:
            __logger__.critical(
                'Ressource "%s" couldn\'t be determined by client.',
                self.data['get']['offline'])
        else:
            output, mime_type, cache_control, cache_file = \
                self.controller.response(
                    request=self, output=output, mime_type=mime_type,
                    cache_control=cache_control, cache_file=cache_file)
        if cache_file:
            self._produce_cache_file_headers(
                cache_file, mime_type, cache_control)
            output = cache_file.content
        else:
            self.data['handler'].send_content_type_header(
                mime_type=mime_type
            ).send_static_file_cache_header(cache_control=cache_control)
        if self.new_cookie:
            self.data['handler'].send_cookie(
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
##            self.data['handler'].headers.get('If-Modified-Since') ==
##            self.data['handler'].date_time_string(cache_timestamp)):
        if(mime_type != 'text/cache-manifest' and
           self.data['handler'].headers.getheader(
               'If-Modified-Since'
           ) == self.data['handler'].date_time_string(
                cache_timestamp)):
##
            __logger__.info(
                'Sent not modified header (304) for "%s".',
                cache_file.path)
            return self.data['handler'].send_content_type_header(
                response_code=304, mime_type=mime_type
            ).send_static_file_cache_header(
                timestamp=cache_timestamp, cache_control=cache_control)
        self.data['handler'].send_content_type_header(
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
