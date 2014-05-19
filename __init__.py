#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# region header

'''
    Provides the main entry point for the web application. Initializes models \
    and starts the web socket.
'''

__author__ = 'Torben Sickert'
__copyright__ = 'see module docstring'
__credits__ = 'Torben Sickert',
__license__ = 'see module docstring'
__maintainer__ = 'Torben Sickert'
__maintainer_email__ = 't.sickert@gmail.com'
__status__ = 'stable'
__version__ = '1.0'

from copy import copy, deepcopy
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
import time

try:
    from django.conf import settings as django_settings
    from django.template import Context as DjangoTemplateContext
    from django.template import Template as DjangoTemplateParser
    from django.utils.safestring import mark_safe as marke_safe_string
except ImportError:
    DjangoTemplateParser = DjangoTemplateContext = None

from sqlalchemy.engine.default import DefaultExecutionContext
from sqlalchemy import create_engine as create_database_engine
from sqlalchemy.orm import sessionmaker as create_database_session
from sqlalchemy.schema import CreateTable, DropTable, Table, MetaData

from sqlalchemy import event as SqlalchemyEvent
from sqlalchemy.engine import Engine as SqlalchemyEngine
from sqlite3 import Connection as SQLite3Connection

from boostNode.extension.file import Handler as FileHandler
from boostNode.extension.native import Module, Dictionary, String
from boostNode.extension.output import Print
from boostNode.extension.system import CommandLine, Runnable
from boostNode.extension.type import Null
from boostNode.paradigm.objectOrientation import Class
from boostNode.runnable.server import Web as WebServer
from boostNode.runnable.template import Parser as TemplateParser
from boostNode.runnable.template import __exception__ as TemplateError

try:
    from controller import Main as Controller
    from restController import Response as RestResponse
except ImportError:
    Controller = RestResponse = None

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
    frontend_data_wrapper = {}
    '''Holds a mapping to convert dictionaries for frontend.'''
    backend_data_wrapper = {}
    '''Holds a mapping to convert dictionaries for backend.'''
    django_settings_set = False
    '''Indicates if django is already configured.'''
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
    def render_main_index_html_file(cls):
        '''Renders the main index html file.'''
        index_template_file = FileHandler(
            location=cls.options['location']['template_index_file'])
        if index_template_file.is_file():
            root_mapping = {
                'options': deepcopy(cls.options['frontend']),
                'debug': cls.debug, 'deployment':
                cls.given_command_line_arguments.render_template}
            del root_mapping['options']['admin']
            for site in ('frontend', 'backend'):
                root_mapping['backend'] = (
                    site == 'backend' and 'admin' in cls.options['frontend'])
                mapping = cls.controller.get_frontend_scope(deepcopy(
                    root_mapping))
                if mapping['backend']:
                    mapping['options'] = Dictionary(
                        mapping['options']
                    ).update(cls.options['frontend']['admin']).content
                if site == 'frontend' or root_mapping['backend']:
                    if(django_settings is None or
                       cls.options['template_engine'] == 'internal'):
                        getattr(
                            cls, '%s_index_html_file' % site
                        ).content = TemplateParser(
                            cls.options['location']['template_index_file'],
                            template_context_default_indent=cls.options[
                                'default_indent_level']
                        ).render(mapping=mapping).output
                    else:
                        if not cls.django_settings_set:
                            cls.django_settings_set = True
                            django_settings.configure(
                                TEMPLATE_DIRS='%s%s' % (
                                    cls.ROOT_PATH,
                                    cls.options['location']['database_folder']
                                ), DEBUG=cls.debug, TEMPLATE_DEBUG=cls.debug,
                                LANGUAGE_CODE=cls.options['default_language'])
                        mapping['optionsAsJSON'] = marke_safe_string(
                            json.dumps(mapping['options']))
# # python3.4
# #                     getattr(
# #                         cls, '%s_index_html_file' % site
# #                     ).content = DjangoTemplateParser(
# #                         FileHandler(
# #                             cls.options['location']['template_index_file']
# #                         ).content
# #                     ).render(DjangoTemplateContext(mapping))
                    getattr(
                        cls, '%s_index_html_file' % site
                    ).content = DjangoTemplateParser(
                        FileHandler(
                            cls.options['location']['template_index_file']
                        ).content
                    ).render(DjangoTemplateContext(mapping)).encode(
                        cls.options['encoding'])
# #

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
# # python3.4
# #         if isinstance(value, bytes):
# #             return value.decode(cls.options['encoding'])
        if isinstance(value, unicode):
            return value.encode(cls.options['encoding'])
# #
        return value

    @classmethod
    def convert_for_client(cls, key, value=Null):
        '''Returns the serialized version of given value.'''
        key = cls.convert_byte_to_string(key)
        value = cls.convert_byte_to_string(value)
        if value is Null:
            value = key
        else:
# # python3.4
# #             if isinstance(value, Date):
# #                 return time.mktime(value.timetuple())
# #             if isinstance(value, DateTime):
# #                 return value.timestamp(
# #                 ) + value.microsecond / 1000 ** 2
            if isinstance(value, Date):
                return time.mktime(value.timetuple())
            if isinstance(value, DateTime):
                return(
                    time.mktime(value.timetuple()) +
                    value.microsecond / 1000 ** 2)
# #
            if isinstance(value, Time):
                return(
                    1000 ** 2 * 60 ** 2 * value.hour +
                    1000 ** 2 * 60 * value.minute +
                    1000 ** 2 * value.second + value.microsecond / 1000 ** 2)
# # python3.4
# #             if(isinstance(key, str) and (
# #                 key == 'language' or key.endswith('_language') or
# #                 key.endswith('Language')
# #             )) and re.compile('[a-z]{2}_[a-z]{2}').fullmatch(value):
            if(isinstance(key, str) and (
                key == 'language' or key.endswith('_language') or
                key.endswith('Language')
            )) and re.compile('[a-z]{2}_[a-z]{2}$').match(value):
# #
                return String(value).delimited_to_camel_case(
                ).content[:-1] + value[-1].upper()
        if not isinstance(value, (int, float, type(None))):
            return str(value)
        return value

    @classmethod
    def convert_dictionary_for_backend(cls, data):
        '''Converts a given dictionary in backend compatible data types.'''
# # python3.4
# #         return Dictionary(data).convert(
# #             key_wrapper=lambda key, value: String(
# #                 key
# #             ).camel_case_to_delimited().content if isinstance(
# #                 key, str
# #             ) else cls.convert_for_backend(key),
# #             value_wrapper=cls.convert_for_backend
# #         ).content
        return Dictionary(data).convert(
            key_wrapper=lambda key, value: String(
                key
            ).camel_case_to_delimited().content if isinstance(
                key, (str, unicode)
            ) else cls.convert_for_backend(key),
            value_wrapper=cls.convert_for_backend
        ).content
# #

    @classmethod
    def convert_for_backend(cls, key, value=Null):
        '''Converts data from client to python specific data objects.'''
        key = cls.convert_byte_to_string(key)
        value = cls.convert_byte_to_string(value)
        if value is Null:
            value = key
        elif isinstance(key, str):
            if key == 'date_time' or key.endswith('_date_time'):
                if isinstance(value, (int, float)):
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
                                                microsecond=microsecond_format)
                                        )
                                    except ValueError:
                                        pass
            if key == 'date' or key.endswith('_date') or key.endswith('Date'):
                if isinstance(value, (int, float)):
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
# # python3.4
# #                                     return Date.fromtimestamp(
# #                                         DateTime.strptime(
# #                                             value, date_format.format(
# #                                                 delimiter=delimiter,
# #                                                 year=year_format
# #                                             )).timestamp())
                                    return Date.fromtimestamp(time.mktime(
                                        DateTime.strptime(
                                            value, date_format.format(
                                                delimiter=delimiter,
                                                year=year_format
                                            )).timetuple()))
# #
                                except ValueError:
                                    pass
            if key == 'time' or key.endswith('_time') or key.endswith('Time'):
                if isinstance(value, (int, float)):
                    return DateTime.fromtimestamp(value).time()
                elif isinstance(value, str):
                    for microsecond_format in ('', ':%f'):
                        try:
                            return DateTime.strptime(
                                value, '%X{microsecond}'.format(
                                    microsecond=microsecond_format))
                        except ValueError:
                            pass
# # python3.4
# #             if(key == 'language' or key.endswith('_language') or
# #                key.endswith('Language')
# #                ) and re.compile('[a-z]{2}[A-Z]{2}').fullmatch(value):
            if(key == 'language' or key.endswith('_language') or
               key.endswith('Language')
               ) and re.compile('[a-z]{2}[A-Z]{2}$').match(value):
# #
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
            account_data = user.dictionary
            account_state = hash(
                Dictionary(account_data).get_immutable())
        return TemplateParser(
            offline_manifest_template_file,
            template_context_default_indent=self.options[
                'default_indent_level']
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

        # # region properties

        self.data = __request_arguments__
        self.new_cookie = {}
        '''Normalize get and payload data.'''
        self.data['get'] = self.convert_dictionary_for_backend(
            self.data['get'])
        if isinstance(self.data['data'], list):
            for index, item in enumerate(self.data['data']):
                self.data['data'][index] = self.convert_dictionary_for_backend(
                    item)
        else:
            if self.options['remove_duplicated_request_key']:
                for key, value in self.data['data'].items():
                    if isinstance(value, list):
                        if len(value) > 0:
                            self.data['data'][key] = value[0]
                        else:
                            self.data['data'][key] = None
            self.data['data'] = self.convert_dictionary_for_backend(
                self.data['data'])
            '''
                If post data doesn't support native data types we have to \
                convert a second time to first evaluate integers and floats \
                and detect timestamps in second round.
            '''
            if not self.options['post_supports_native_types']:
                self.data['data'] = self.convert_dictionary_for_backend(
                    self.data['data'])
        '''Holds the current request handler server instance.'''
        self.session = create_database_session(bind=self.engine)()
        self.authorized_user = self._authenticate()

        # # endregion

        try:
            self._web_controller()
        except TemplateError as exception:
            if self.debug:
                self.data['handler'].send_error(500, '%s: "%s"' % (
                    exception.__class__.__name__, str(exception)))
            else:
                # NOTE: The web server will handle this.
                raise
        finally:
            self.session.close()
        return self

    def _run(self):
        '''Initializes the web server.'''

        # # region properties

        self.__class__.package_name = Module.get_package_name(
            frame=inspect.currentframe())
        FileHandler.set_root(location=FileHandler(FileHandler(
            Module.get_name(
                frame=inspect.currentframe(), path=True, extension=True),
            output_with_root_prefix=True
        ).directory_path).directory_path)
        self.__class__.ROOT_PATH = FileHandler.get_root().path
        self.__class__.controller = None
        self._set_options()
        if Controller is not None:
            self.__class__.controller = Controller(main=self.__class__)
        self.__class__.given_command_line_arguments = \
            CommandLine.argument_parser(
                arguments=self.options['command_line_arguments'],
                module_name=__name__)
        self.__class__.debug = \
            sys.flags.debug or __logger__.isEnabledFor(logging.DEBUG)
        try:
            self.__class__.model = __import__('model')
        except ImportError:
            self.__class__.model = None
        self._append_model_informations_to_options()
        self.__class__.frontend_index_html_file = FileHandler(
            self.options['location']['index_html_file']['frontend'])
        self.__class__.backend_index_html_file = FileHandler(
            self.options['location']['index_html_file']['backend'])
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
        if not self.given_command_line_arguments.render_template:
            self.clear_web_cache()
            __logger__.info(
                'Initialize database on "%s".',
                self.options['location']['database_url'])
            self._initialize_model()
        if self.controller is not None:
            self.__class__.options = self.controller.initialize()
        if(self.debug or self.given_command_line_arguments.render_template or
           not self.frontend_index_html_file or
           not self.backend_index_html_file):
            __logger__.info(
                'Render main entry html file "%s".',
                self.options['location']['template_index_file'])
            self.render_main_index_html_file()
        if not self.given_command_line_arguments.render_template:
            return self._start_web_server()

        # endregion

        # region helper methods

            # region static

    @classmethod
    def _check_database_file_references(cls):
        '''
            Checks if all file references saved in database records exists. \
            If a dead link was found the user will be asked for deleting \
            referenced database records.
        '''
        checked_paths = {}
        for model_name, model in Module.get_defined_objects(cls.model):
            if isinstance(model, type) and issubclass(model, cls.model.Model):
                for property in model.__table__.columns:
                    if property.info and 'file_reference' in property.info:
                        for model in cls.session.query(model):
                            file_path = property.info['file_reference'] % \
                                getattr(model, property.name)
                            if(not (
                                file_path in checked_paths or FileHandler(
                                    file_path)
                            ) and CommandLine.boolean_input(
                                'Model "%s" (%s) has a dead file reference via'
                                ' attribute "%s" to "%s". Do you want to '
                                'delete this record? {boolean_arguments}: ' % (
                                    repr(model), model_name, property.name,
                                    file_path))
                            ):
                                cls.session.delete(model)
                            elif(file_path not in checked_paths or
                                 checked_paths[file_path] != model_name):
                                checked_paths[file_path] = model_name
                                __logger__.debug(
                                    'Check file reference "%s" for model '
                                    '"%s".', file_path, model_name)
        return cls

    @classmethod
    def _check_database_schema_version(cls):
        '''Checke if the database schema has changed.'''
        database_schema_file = FileHandler(
            cls.options['location']['database_schema_file'])
        old_schemas = {}
        if database_schema_file:
# # python3.4
# #             old_schemas = json.loads(
# #                 database_schema_file.content,
# #                 encoding=cls.options['encoding'])
            old_schemas = Dictionary(json.loads(
                database_schema_file.content,
                encoding=cls.options['encoding'])
            ).convert(
                key_wrapper=lambda key, value: cls.convert_byte_to_string(
                    key),
                value_wrapper=lambda key, value: cls.convert_byte_to_string(
                    value)
            ).content
# #
        new_schemas = {}
        for model_name, model in Module.get_defined_objects(cls.model):
            if isinstance(model, type) and issubclass(model, cls.model.Model):
                new_schemas[model.__tablename__] = str(CreateTable(
                    model.__table__))
                if model.__tablename__ not in old_schemas:
                    __logger__.info('New model "%s" detected.', model_name)
                    '''
                        NOTE: sqlalchemy will create this table automatically.
                    '''
                elif(old_schemas[model.__tablename__] !=
                     new_schemas[model.__tablename__]):
                    __logger__.info('Model "%s" has changed.', model_name)
                    # TODO implement
        for table_name in old_schemas:
            if(table_name not in new_schemas and
               cls.engine.dialect.has_table(cls.engine.connect(), table_name)):
                cls.session.execute(DropTable(Table(table_name, MetaData(
                    bind=cls.engine))))
                __logger__.info('Table "%s" has been removed.', table_name)
        if cls.model is not None:
# # python3.4
# #             database_schema_file.content = json.dumps(
# #                 new_schemas, sort_keys=True,
# #                 indent=cls.options['default_indent_level'])
            database_schema_file.content = json.dumps(
                new_schemas, encoding=cls.options['encoding'],
                sort_keys=True, indent=cls.options['default_indent_level'])
# #
        return cls

    @classmethod
    def _append_model_informations_to_options(cls):
        '''Appends validation strings to the global options object.'''
        cls.options['type'] = {}
        for model_name, model in Module.get_defined_objects(cls.model):
            if isinstance(model, type) and issubclass(model, cls.model.Model):
                cls.options['type'][model_name] = {}
                for property in model.__table__.columns:
                    cls.options['type'][model_name][property.name] = {
                        'required': True}
                    if property.info:
                        cls.options['type'][model_name][property.name].update(
                            property.info)
                    if hasattr(property.type, 'length') and isinstance(
                        property.type.length, int
                    ):
                        cls.options['type'][model_name][property.name][
                            'maximum_length'
                        ] = property.type.length
                    if(hasattr(property, 'default') and
                       property.default is not None):
                        cls.options['type'][model_name][property.name][
                            'required'
                        ] = False
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
                    elif hasattr(property, 'nullable') and property.nullable:
                        cls.options['type'][model_name][property.name][
                            'required'
                        ] = False
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
            location='/%s/%s' % (cls.package_name, cls.CONFIGURATION_FILE_PATH)
        ).content))
        configuration_file = FileHandler(location=cls.CONFIGURATION_FILE_PATH)
        if configuration_file:
            cls.options.update(json.loads(configuration_file.content))
        cls.options = cls.options.content
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
# # python3.4
# #             cls.options = Dictionary(cls.options).convert(
# #                 value_wrapper=lambda key, value: TemplateParser(
# #                     value, string=True
# #                 ).render(
# #                     mapping=mapping, module_name=__name__, main=cls
# #                 ).output if isinstance(value, str) else value
# #             ).content
            cls.options = Dictionary(cls.options).convert(
                value_wrapper=lambda key, value: TemplateParser(
                    value, string=True
                ).render(
                    mapping=mapping, module_name=__name__, main=cls
                ).output if isinstance(value, (unicode, str)) else value
            ).content
# #
        cls.options = Dictionary(cls.options).convert(
            key_wrapper=lambda key, value: String(key).camel_case_to_delimited(
            ).content, value_wrapper=cls.convert_for_backend
        ).content
        String.abbreviations = cls.options['abbreviations']
        cls.options['frontend'] = Dictionary(cls.options['frontend']).convert(
            key_wrapper=lambda key, value: cls.convert_for_client(String(
                key
            ).delimited_to_camel_case().content),
            value_wrapper=cls.convert_for_client
        ).content
        cls.options['session']['expiration_interval'] = TimeDelta(
            minutes=cls.options['session']['expiration_time_in_minutes'])
        if 'authentication_handler' in cls.options['web_server']:
# # python3.4
# #             cls.options['web_server']['authentication_handler'] = eval(
# #                 cls.options['web_server']['authentication_handler'],
# #                 {'controller': cls.controller})
            cls.options['web_server']['authentication_handler'] = eval(
                cls.options['web_server']['authentication_handler'],
                {'controller': cls.controller})
# #
        '''
            Export options to global scope to make them accessible for other \
            modules like model or controller.
        '''
        OPTIONS = cls.options
        return cls

    @SqlalchemyEvent.listens_for(SqlalchemyEngine, 'connect')
    def _set_sqlite_foreign_key_pragma(dbapi_connection, connection_record):
        '''Activates sqlite3 foreign key support.'''
        if isinstance(dbapi_connection, SQLite3Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute('PRAGMA foreign_keys=ON;')
            cursor.close()

    @classmethod
    def _initialize_model(cls):
        '''Initializes the model.'''
        cls.engine = create_database_engine('%s%s%s' % (
            cls.options['database_engine_prefix'], cls.ROOT_PATH,
            cls.options['location']['database_url']
        ), echo=__logger__.isEnabledFor(logging.DEBUG))
        if cls.model is not None:
            cls.model.Model.metadata.create_all(cls.engine)
        cls.session = create_database_session(bind=cls.engine)()
        cls._check_database_schema_version()
        cls._check_database_file_references()
        if cls.controller is not None:
            cls.controller.insert_needed_database_record()
            if cls.debug:
                cls.controller.insert_database_mockup()
        cls.session.commit()
        return cls

        # # endregion

    def _authenticate(self):
        '''
            Authenticates a user by potential sent header identification data.
        '''
        user_id = session_token = None
        if self.options['authentication_method'] == 'header':
            user_id = self.data['handler'].headers.get(String(
                self.options['session']['key']['user_id']
            ).camel_case_to_delimited(delimiter='-').content)
            session_token = self.data['handler'].headers.get(String(
                self.options['session']['key']['token']
            ).camel_case_to_delimited(delimiter='-').content)
        elif(self.options['authentication_method'] == 'cookie' and
             self.options['session']['key']['user_id'] in self.data['cookie']
             and self.options['session']['key']['token_key'] in
             self.data['cookie']):
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
        if '__manifest__' in self.data['get']:
            mime_type = 'text/cache-manifest'
            cache_control = 'no-cache'
            '''Dynamic request should be handled by frontend cache.'''
            user = None
            manifest_name = 'generic'
            if(self.options['session']['key']['user_id'] in
               self.data['cookie'] and
               self.options['session']['key']['token'] in self.data['cookie']):
                user = self.session.query(self.model.Model).filter(
                    self.model.User.id ==
                    self.data['cookie'][self.options['user_id_key']],
                    self.model.User.session_token == self.data['cookie'][
                        self.options['session']['key']['token']]
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
        elif '__model__' in self.data['get']:
            mime_type = 'application/json'
            output = RestResponse(request=self).output
        elif '__offline__' in self.data['get']:
            __logger__.critical(
                'Ressource "%s" couldn\'t be determined by client.',
                self.data['get']['__offline__'])
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
                self.new_cookie, maximum_age_in_seconds=self.options[
                    'maximumCookieAgeInSeconds'])
        Print(output, end='')
        return self

    def _produce_cache_file_headers(
        self, cache_file, mime_type, cache_control
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
