#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-

# region header

'''
    Provides the main entry point for the web application. Initializes models \
    and starts the web socket.
'''

# # python2.7
# # from __future__ import absolute_import, division, print_function, \
# #     unicode_literals
pass
# #

__author__ = 'Torben Sickert'
__copyright__ = 'see module docstring'
__credits__ = 'Torben Sickert',
__license__ = 'see module docstring'
__maintainer__ = 'Torben Sickert'
__maintainer_email__ = 't.sickert["~at~"]gmail.com'
__status__ = 'stable'
__version__ = '1.0'

# # python2.7 import __builtin__ as builtins
import builtins
from copy import copy, deepcopy
from datetime import datetime as DateTime
from datetime import time as Time
from datetime import date as Date
from datetime import timedelta as TimeDelta
from httplib import HTTPConnection
import inspect
import json
import logging
import multiprocessing
import os
import re as regularExpression
from socket import error as SocketError
import sys
import time

from sqlalchemy.engine.default import DefaultExecutionContext
from sqlalchemy.exc import OperationalError
from sqlalchemy import create_engine as create_database_engine
from sqlalchemy.orm import sessionmaker as create_database_session
from sqlalchemy.schema import CreateTable, DropTable, Table, MetaData
from sqlalchemy import event as SqlalchemyEvent
from sqlalchemy.engine import Engine as SqlalchemyEngine
from sqlite3 import Connection as SQLite3Connection

# # python2.7 from boostNode import convert_to_string, convert_to_unicode
pass
from boostNode.extension.file import Handler as FileHandler
from boostNode.extension.native import Dictionary, Module, Object
from boostNode.extension.native import String as StringExtension
from boostNode.extension.native import __exception__ as NativeError
from boostNode.extension.output import Print
from boostNode.extension.system import CommandLine, Runnable, Platform
from boostNode.extension.system import __exception__ as SystemError
from boostNode.extension.type import Null
from boostNode.paradigm.objectOrientation import Class
from boostNode.runnable.server import Web as WebServer
from boostNode.runnable.template import Parser as TemplateParser
from boostNode.runnable.template import __exception__ as TemplateError
from boostNode import highPerformanceModification


# # python2.7
# # String = lambda content: StringExtension(convert_to_string(content))
# NOTE: Should be removed if we drop python2.X support.
String = StringExtension
# #

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
    SUPPORTED_PROXY_SERVER_NAME_PATTERN = 'nginx/.+',
    '''Saves all supported proxy server name patterns.'''
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
    port = None
    '''
        Saves port (eather proxy or application server) of currently running \
        web application.
    '''
    proxy_port = None
    '''
        Saves proxy port if available and "None" if no proxy server could be \
        determined.
    '''

    # endregion

    # region static methods

    # # region public

    # # # region boolean

    @classmethod
    def is_valid_web_asset(cls, file):
        '''Checks if the given file is a valid web application asset.'''
        for pattern in cls.options['ignore_web_asset_pattern']:
# # python2.7
# #             if regularExpression.compile('(?:%s)$' % pattern).match(file.path):
            if regularExpression.compile(pattern).fullmatch(file.path):
# #
                return False
        return True

        # # endregion

        # # region helper

    @classmethod
    def extend_options(
        cls, options, consolidate=True, remove_no_wrap_indicator=False
    ):
        '''Extends options object with given options.'''
        if options:
            cls.options = Dictionary(content=cls.options).update(
                options
            ).content
            if consolidate:
                cls.consolidate_options(remove_no_wrap_indicator)
        return cls

    @classmethod
    def consolidate_options(cls, remove_no_wrap_indicator=False):
        '''Merges, renders and resolves internal option dependencies.'''
        '''
            NOTE: This is the only backend needed camel case option, because \
            it will be appended via introspection.
        '''
        cls._merge_options().options['moduleName'] = __name__
        frontend_options = cls.options['frontend']
        del cls.options['frontend']
        '''
            We convert only keys to backend compatible types to make them \
            available for the rendering phase.
        '''
        cls.options = Dictionary(content=cls.options).convert(
            key_wrapper=lambda key, value: cls.convert_for_backend(key),
            remove_no_wrap_indicator=False
        ).content
        cls.options['frontend'] = frontend_options
        mockup_template = TemplateParser('', string=True)
        '''
            NOTE: A check for left template code delimiter avoids parsing \
            plain strings as templates and lose many performance.
        '''
        def value_wrapper(key, value):
# # python2.7
# #             while builtins.isinstance(
# #                 value, (builtins.unicode, builtins.str)
# #             ) and mockup_template.left_code_delimiter in value:
            while builtins.isinstance(
                value, builtins.str
            ) and mockup_template.left_code_delimiter in value:
# #
                value = TemplateParser(
                    convert_to_unicode(value).replace(
                        '\\', 2 * '\\'
                    ).replace('%s%s' % (
                        mockup_template.left_code_delimiter,
                        mockup_template.right_escaped
                    ), '%s%s%s' % (
                        mockup_template.left_code_delimiter,
                        mockup_template.right_escaped,
                        mockup_template.right_escaped
                    )), string=True,
                ).render(
                    mapping=cls.options, module_name=__name__, main=cls
                ).output
            return value
        cls.options = Dictionary(content=cls.options).convert(
            value_wrapper=value_wrapper, remove_no_wrap_indicator=False
        ).content
        frontend_options = cls.options['frontend']
        del cls.options['frontend']
        '''
            After converting keys to backend compatible types we now convert \
            the values after rendering phase.
        '''
# # python2.7
# #         cls.options = Dictionary(content=cls.options).convert(
# #             key_wrapper=lambda key, value: convert_to_unicode(String(
# #                 key
# #             ).camel_case_to_delimited.content),
# #             value_wrapper=cls.convert_for_backend,
# #             remove_no_wrap_indicator=remove_no_wrap_indicator
# #         ).content
        cls.options = Dictionary(content=cls.options).convert(
            key_wrapper=lambda key, value: String(
                key
            ).camel_case_to_delimited.content,
            value_wrapper=cls.convert_for_backend,
            remove_no_wrap_indicator=remove_no_wrap_indicator
        ).content
# #
        cls.options['frontend'] = frontend_options
        return cls

    @classmethod
    def extend_user_authorization(
        cls, user_id, session_token, location=None
    ):
        '''
            Extends user authorization time. If successfully the user id will \
            be returned "None" otherwise.
        '''
        result = None
        while user_id and session_token:
            try:
                user_id = builtins.int(user_id)
                session = create_database_session(bind=cls.engine)()
                users = session.query(cls.model.User).filter(
                    cls.model.User.enabled == True,
                    cls.model.User.id == user_id,
                    cls.model.User.session_token == session_token,
                    cls.model.User.session_expiration_date_time > DateTime.now(
                    ))
                if users.count():
                    user = users.one()
                    user.session_expiration_date_time = DateTime.now(
                    ) + cls.options['session']['expiration_time_delta']
                    __logger__.info(
                        'Authorize user with id %d for %.2f hours.', user.id, (
                            cls.options['session'][
                                'expiration_time_delta'
                            ].total_seconds() / 60) / 60)
                    if location is not None:
                        user.location = location
                    result = user.id
                    session.commit()
            except OperationalError as exception:
                session.close()
# # python2.7
# #                 if 'database is locked' in builtins.str(exception):
# #                     __logger__.warning(
# #                         'Database seems to be locked. Retrying to connect'
# #                         '. %s: %s',
# #                         exception.__class__.__name__,
# #                         builtins.str(exception))
                if 'database is locked' in builtins.str(exception):
                    __logger__.warning(
                        'Database seems to be locked. Retrying to connect'
                        '. %s: %s', exception.__class__.__name__,
                        builtins.str(exception))
# #
                    time.sleep(1)
                    continue
                raise
            else:
                session.close()
                break
        return result

    @classmethod
    def render_templates(cls, all=False, proxy_restart=False):
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
            if cls.proxy_port is not None:
                cls._reinitialize_proxy_server(proxy_restart)
        cls._render_html_templates(mapping)
        return cls

    @classmethod
    def clear_web_cache(cls):
        '''Clears all web cache files.'''
        web_cache = FileHandler(location=cls.options['location']['web_cache'])
        if web_cache.is_directory():
            __logger__.info('Clear web cache in "%s".', web_cache.path)
            for file in builtins.filter(lambda file: cls.is_valid_web_asset(
                file
            ), web_cache):
                file.remove_deep()
        template_cache = FileHandler(
            location=cls.options['location']['template_cache'])
        if template_cache.is_directory():
            __logger__.info(
                'Clear template cache in "%s".', template_cache.path)
            template_file_extension_suffix = '%s%s' % (
                os.extsep, TemplateParser.DEFAULT_FILE_EXTENSION)
            for file in builtins.filter(lambda file: file.is_file(
            ) and file.name.endswith('%s%spy' % (
                template_file_extension_suffix, os.extsep
            )) or file.is_directory() and file.name.endswith(
                template_file_extension_suffix
            ), template_cache):
                file.remove_deep()
        return cls

    @classmethod
    def convert_for_client(cls, key, value=Null):
        '''Returns the serialized version of given value.'''
        if value is Null:
            value = key
# # python2.7
# #         if(builtins.isinstance(key, builtins.unicode) and (
# #             key == 'language' or key.endswith('_language') or
# #             key.endswith('Language')
# #         )) and regularExpression.compile('[a-z]{2}_[a-z]{2}$').match(value):
# #             return '%s%s' % (convert_to_unicode(String(
# #                 value
# #             ).delimited_to_camel_case.content[:-1]),
# #             convert_to_unicode(value[-1].upper()))
        if(builtins.isinstance(key, builtins.str) and (
            key == 'language' or key.endswith('_language') or
            key.endswith('Language')
        )) and regularExpression.compile('[a-z]{2}_[a-z]{2}').fullmatch(
            value
        ):
            return '%s%s' % (String(
                value
            ).delimited_to_camel_case.content[:-1], value[-1].upper())
# #
        return Object(content=value).compatible_type

    @classmethod
    def convert_for_backend(cls, key, value=Null):
        '''Converts data from client to python specific data objects.'''
        if value is Null:
            value = key
        if 'data_keys_to_ignore' in cls.options and key in cls.options[
            'data_keys_to_ignore'
        ]:
            return value
# # python2.7
# #         if builtins.isinstance(key, (
# #             builtins.unicode, builtins.str
# #         )) and (key == 'language' or key.endswith('_language') or
# #             key.endswith('Language')
# #         ) and regularExpression.compile('[a-z]{2}[A-Z]{2}$').match(value):
# #             return convert_to_unicode(String(
# #                 value
# #             ).camel_case_to_delimited.content)
        if builtins.isinstance(
            key, builtins.str
        ) and (key == 'language' or key.endswith('_language') or
        key.endswith('Language')) and regularExpression.compile(
            '[a-z]{2}[A-Z]{2}'
        ).fullmatch(value):
            return String(
                value
            ).camel_case_to_delimited.content
# #
        try:
            return Object(content=value).get_known_type(
                description=None if key == value else key)
        except NativeError:
            return value

        # # endregion

    # # # region getter

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

    # # # endregion

    # # endregion

    # # region protected

    @classmethod
    def _reinitialize_proxy_server(cls, proxy_restart):
        '''
            Restarts of reloads an existing proxy server. This is needed \
            after configuration file updates for example.
        '''
        if(proxy_restart and
           cls.options['system_commands']['proxy_server']['start'] and
           cls.options['system_commands']['proxy_server']['stop']
        ):
            for command in ('stop', 'start'):
                __logger__.debug(
                    'Run "%s".', cls.options['system_commands'][
                        'proxy_server'][command])
                try:
                    Platform.run(
                        command=cls.options['system_commands'][
                            'proxy_server'
                        ][command], native_shell=True)
                except SystemError as exception:
                    __logger__.warning(
                        '%s: %s You may have a miss configured proxy '
                        'server at port %d or we have not enough '
                        'permissions to control the proxy server. '
                        'Command was "%s".',
                        exception.__class__.__name__,
                        builtins.str(exception), cls.proxy_port,
                        cls.options['system_commands']['proxy_server'][
                            command])
                else:
                    if command == 'stop':
                        time.sleep(0.1)
        elif cls.options['system_commands']['proxy_server']['reload']:
            __logger__.debug(
                'Run "%s".', cls.options['system_commands'][
                    'proxy_server']['reload'])
            try:
                Platform.run(
                    command=cls.options['system_commands'][
                        'proxy_server'
                    ]['reload'])
            except SystemError as exception:
                __logger__.warning(
                    '%s: %s You may have a miss configured proxy '
                    'server at port %d or we have not enough '
                    'permissions to control the proxy server. '
                    'Command was "%s".', exception.__class__.__name__,
                    builtins.str(exception), cls.proxy_port,
                    cls.options['system_commands']['proxy_server'][
                        'reload'])
        return cls

    @classmethod
    def _render_template(cls, file, mapping):
        '''
            Renders each template and distinguishes between backend and \
            frontend templates.
        '''
        if(file.name.startswith('.') or file.is_symbolic_link() or
           file.path in cls.options['location']['template_ignored']):
            '''Don't enter ignored locations or parse ignored files.'''
            return None
# # python2.7
# #         if(file.extension == TemplateParser.DEFAULT_FILE_EXTENSION and
# #         FileHandler(
# #             location='%s%s' % (file.directory.path, file.basename)
# #         ).extension and not (file == cls.html_template_file)):
        if(file.extension == TemplateParser.DEFAULT_FILE_EXTENSION and
        FileHandler(
            location='%s%s' % (file.directory.path, file.basename)
        ).extension and file != cls.html_template_file):
# #
            FileHandler(location='%s%s' % (
                file.directory.path, file.name[:-builtins.len('%s%s' % (
                    os.extsep, TemplateParser.DEFAULT_FILE_EXTENSION))]
            )).content = cls._render_template_helper(file, mapping)
        return cls

    @classmethod
    def _render_html_templates(cls, mapping):
        '''Renders all frontend html templates.'''
        if cls.html_template_file.is_file():
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
        parent_folder = file.directory
        while True:
            if parent_folder.name.startswith('backend'):
                is_backend = True
            if parent_folder == FileHandler.get_root() or is_backend:
                break
            parent_folder = parent_folder.directory
        mapping['options']['frontend']['admin'] = ((is_backend) and
            'admin' in cls.options['frontend'])
        mapping = cls.controller.get_template_scope(deepcopy(mapping))
        if mapping['options']['frontend']['admin']:
            mapping['options']['frontend'] = Dictionary(
                content=mapping['options']['frontend']
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
        for model_name, model in builtins.filter(
            lambda model: builtins.isinstance(
                model, builtins.type
            ) and builtins.issubclass(model, cls.model.Model),
            Module.get_defined_objects(cls.model)
        ):
            for property in builtins.filter(
                lambda property: property.info and 'file_reference' in \
                    property.info,
                model.__table__.columns
            ):
                for model_instance in builtins.filter(
                    lambda model_instance: builtins.getattr(
                        model_instance, property.name
                    ) is not None, session.query(model)
                ):
                    file = FileHandler(
                        location=property.info['file_reference'] %
                        builtins.getattr(model_instance, property.name))
                    __logger__.debug(
                        'Check file reference "%s" for model "%s".', file_path,
                        model_name)
                    if not file and CommandLine.boolean_input(
                        'Model %s has a dead file reference via attribute "%s"'
                        ' to "%s". Do you want to delete this record? '
                        '{boolean_arguments}: ' % (builtins.repr(
                            model_instance
                        ), property.name, file.path)
                    ):
                        session.query(model).filter_by(
                            **model_instance.dictionary
                        ).delete()
                        session.commit()
        session.close()
        return cls

    @classmethod
    def _check_database_schema_version(cls, database_backup_file):
        '''Checke if the database schema has changed.'''
        if cls.model is None: return cls
        old_schemas = {}
        serialized_schema = ''
        database_schema_file = FileHandler(
            location=cls.options['location']['database']['schema_file'])
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
        migration_successful = True
        session = create_database_session(
            bind=cls.engine, expire_on_commit=False
        )()
        for model_name, model in models:
# # python2.7
# #             new_schemas[model.__tablename__] = convert_to_unicode(
# #                 CreateTable(model.__table__))
            new_schemas[model.__tablename__] = builtins.str(CreateTable(
                model.__table__))
# #
            if model.__tablename__ in old_schemas:
                # TODO Schemas can have equivalent different string
                # representations (in python3.4 at the latest!)
# # python2.7
# #                 if(old_schemas[model.__tablename__] !=
# #                    new_schemas[model.__tablename__]):
                if(old_schemas[model.__tablename__] !=
                   new_schemas[model.__tablename__] and False):
# #
                    __logger__.info('Model "%s" has changed.', model_name)
                    migration_successful = cls._migrate_table(
                        model, models, migration_successful, session)
            elif model.__tablename__ not in old_schemas:
                __logger__.info('New model "%s" detected.', model_name)
                '''NOTE: sqlalchemy will create this table automatically.'''
        cls._save_database_schema(database_schema_file, session, new_schemas)
        session.close()
        if not migration_successful: sys.exit(1)
        return cls._save_database_backup(
            database_schema_file, serialized_schema, database_backup_file)

    @classmethod
    def _migrate_model(cls, model, models, migration_successful, session):
        '''
            Migrates given model. Creates new schema and copies old data to \
            them.
        '''
        temporary_table_name = '%s_temp' % model.__tablename__
        while temporary_table_name in builtins.map(
            lambda model: model[1].__tablename__, models
        ):
            temporary_table_name = '%s_temp' % temporary_table_name
        __logger__.info(
            'Create new temporary table "%s".', temporary_table_name)
        temporary_table = Table(
            temporary_table_name, MetaData(bind=cls.engine))
        old_columns = {}
        for column in model.__table__.columns:
            if column.name in old_schemas[model.__tablename__]:
                old_columns[column.name] = builtins.getattr(model, column.name)
            temporary_table.append_column(column.copy())
        for constraint in model.__table__.constraints:
            '''
                NOTE: Produces a warning. Constraints seems not to reference \
                local columns. "constraint.copy()" is no option because the \
                result loses the column bounding.
            '''
            temporary_table.append_constraint(constraint)
        temporary_table.create(cls.engine)
        session.commit()
        __logger__.info(
            'Transferring old records from "%s" to "%s".', model.__tablename__,
            temporary_table_name)
        '''
            NOTE: We have to select all old column names explicitly because \
            some properties may not exist in old database reflection.
        '''
        for values in session.query(*old_columns.values()):
# # python2.7
# #             __logger__.debug(
# #                 'Transferring record "%s".', '", "'.join(builtins.map(
# #                     lambda value: convert_to_unicode(value), values)))
            __logger__.debug(
                'Transferring record "%s".', '", "'.join(builtins.map(
                    lambda value: builtins.str(value), values)))
# #
            try:
                session.execute(temporary_table.insert(builtins.dict(
                    builtins.zip(old_columns.keys(), values))))
            except builtins.Exception as exception:
# # python2.7
# #                 __logger__.critical(
# #                     '%s: %s', exception.__class__.__name__,
# #                     convert_to_unicode(exception))
                __logger__.critical(
                    '%s: %s', exception.__class__.__name__,
                    builtins.str(exception))
# #
                migration_successful = False
        session.commit()
        if(migration_successful and
           cls.options['database']['engine_prefix'].startswith('sqlite:')):
            __logger__.info('Drop old table "%s".', model.__tablename__)
            '''NOTE: We have to temporary remove foreign key checks.'''
            # TODO Check
            # defer_foreign_keys=ON
            # ignore_check_constraints=ON
            session.execute('PRAGMA foreign_keys=OFF;')
            session.execute(DropTable(Table(model.__tablename__, MetaData(
                bind=cls.engine))))
            __logger__.info(
                'Rename new table "%s" to old table name "%s".',
                temporary_table_name, model.__tablename__)
            session.execute('ALTER TABLE %s RENAME TO %s;' % (
                temporary_table_name, model.__tablename__))
            session.execute('PRAGMA foreign_key_check;')
            session.execute('PRAGMA foreign_keys=ON;')
            __logger__.info(
                'Automatic migration of model "%s" was successful.',
                model_name)
        else:
            __logger__.critical(
                'Please migrate table "%s" by hand or prepare for next try.',
                model.__tablename__)
            new_schemas[model.__tablename__] = old_schemas[model.__tablename__]
        session.commit()
        return migration_successful

    @classmethod
    def _save_database_backup(
        cls, database_schema_file, serialized_schema, database_backup_file
    ):
        '''Saves a database backup of current database state.'''
        if(database_schema_file.content != serialized_schema and
           database_backup_file):
            now = DateTime.now()
# # python2.7
# #             time_stamp = time.mktime(now.timetuple()) + \
# #                 now.microsecond / 1000 ** 2
            time_stamp = now.timestamp() + now.microsecond / 1000 ** 2
# #
            long_term_database_file = FileHandler(location='%s%s%d%s' % (
                database_backup_file.directory.path,
                database_backup_file.basename, time_stamp,
                database_backup_file.extension_suffix))
            __logger__.info(
                'Save long term database file "%s".',
                long_term_database_file.path)
            long_term_database_file.directory.make_directories()
            database_backup_file.copy(target=long_term_database_file)
        return cls

    @classmethod
    def _save_database_schema(cls, database_schema_file, session, new_schemas):
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
# # python2.7
# #         database_schema_file.content = json.dumps(
# #             new_schemas, encoding=cls.options['encoding'],
# #             sort_keys=True, indent=cls.options['default_indent_level'])
        database_schema_file.content = json.dumps(
            new_schemas, sort_keys=True,
            indent=cls.options['default_indent_level'])
# #
        return cls

    @classmethod
    def _append_model_informations_to_options(cls):
        '''Appends validation strings to the global options object.'''
        '''
            NOTE: If final option consolidation is activated we don't have to \
            explicitly prevent type property rendering.
        '''
        cls.options['type'] = {'__no_wrapping__': {}}
        option_target = cls.options['type']['__no_wrapping__']
        if cls.options['final_option_consolidation']:
            option_target = cls.options['type'] = {}
        for model_name, model in builtins.filter(
            lambda model: builtins.isinstance(
                model[1], builtins.type
            ) and builtins.issubclass(model[1], cls.model.Model),
            Module.get_defined_objects(cls.model)
        ):
            name = model_name[0]
            if len(model_name) > 1:
                name += model_name[1:]
            option_target[name] = {}
            for property in model.__table__.columns:
                option_target[name][property.name] = \
                    cls._determine_property_information(property)
        return cls

    @classmethod
    def _determine_property_information(cls, property):
        result = property.info if property.info else {}
        result['maximum_length'] = property.type.length if builtins.hasattr(
            property.type, 'length'
        ) and builtins.isinstance(
            property.type.length, builtins.int
        ) else cls.options['database']['maximum_field_size']
        result['required'] = not builtins.hasattr(
            property, 'nullable'
        ) and property.nullable
        if builtins.hasattr(
            property, 'default'
        ) and property.default is not None:
            result['required'] = False
            result['default_value'] = property.default.arg
            if builtins.callable(result['default_value']):
                if builtins.hasattr(
                    cls.model, 'determine_language_specific_default_value'
                ) and result['default_value'] == cls.model\
                .determine_language_specific_default_value:
# # python2.7
# #                     result['default_value'] = Dictionary(
# #                         content=cls.options['model']['generic'][
# #                             'language_specific'
# #                         ]['default'][property.name]).convert(
# #                             key_wrapper=lambda key, value: cls
# #                             .convert_for_client(convert_to_unicode(
# #                                 String(
# #                                     key
# #                                 ).delimited_to_camel_case.content))
# #                         ).content
                    result['default_value'] = Dictionary(
                        content=cls.options['model']['generic'][
                            'language_specific'
                        ]['default'][property.name]).convert(
                            key_wrapper=lambda key, value: cls
                            .convert_for_client(String(
                                key
                            ).delimited_to_camel_case.content)
                        ).content
# #
                else:
                    result['default_value'] = cls.convert_for_client(
                        key=property.name, value=property.default.arg(
                        DefaultExecutionContext()))
            else:
                result['default_value'] = cls.convert_for_client(
                    key=property.name, value=result['default_value'])
        return result

    @classmethod
    def _merge_options(cls):
        '''Merge frontend and backend options.'''
        cls.options = Dictionary(content=cls.options).update(
            cls.options['both']
        ).update(cls.options['backend']).content
        cls.options['frontend'] = Dictionary(
            content=cls.options['both']
        ).update(cls.options['frontend']).content
        return cls

    @classmethod
    def _set_options(cls):
        '''Renders backend and frontend options.'''
        configuration_file = FileHandler(location=cls.CONFIGURATION_FILE_PATH)
        cls.options = Dictionary(content=json.loads(FileHandler(
            location='/%s%s' % (cls.package_name, configuration_file.path)
        ).content)).content
        if configuration_file.is_file():
            return cls.extend_options(
                options=json.loads(configuration_file.content),
                remove_no_wrap_indicator=cls.options['backend'][
                    'finalOptionConsolidation'])
        return cls.consolidate_options(
            remove_no_wrap_indicator=cls.options['final_option_consolidation'])

    @SqlalchemyEvent.listens_for(SqlalchemyEngine, 'connect')
    def _set_database_initialisation(dbapi_connection, connection_record):
        '''Activates configured database features.'''
        if builtins.isinstance(dbapi_connection, SQLite3Connection):
            cursor = dbapi_connection.cursor()
            for command in OPTIONS['database']['initialisation_commands']:
                cursor.execute(command)
            cursor.close()

    @classmethod
    def _initialize_model_module(cls):
        '''Imports and loads the model informations.'''
        '''Export options dictionary for early access to other modules.'''
        global OPTIONS
        OPTIONS = cls.options
        try:
            cls.model = builtins.__import__('model')
        except builtins.ImportError:
            if __test_mode__:
                cls.model = None
            else:
                raise
        return cls._append_model_informations_to_options()

    @classmethod
    def _initialize_model(cls):
        '''Initializes the model.'''
        if cls.options['database']['engine_prefix'].startswith('sqlite:'):
            database_file = FileHandler(
                location=cls.options['location']['database']['url'])
            database_backup_file = FileHandler(
                location='%s%sBackup%s' % (
                    cls.options['location']['database']['backup'],
                    database_file.basename,
                    database_file.extension_suffix))
            database_backup_file.directory.make_directories()
            if database_file:
                __logger__.info(
                    'Backup database "%s" to "%s".', database_file.path,
                    database_backup_file.path)
                database_backup_file.directory.make_directories()
                database_file.copy(target=database_backup_file)
        cls.engine = create_database_engine('%s%s%s' % (
            cls.options['database']['engine_prefix'], cls.ROOT_PATH,
            cls.options['location']['database']['url']
        ), echo=__logger__.isEnabledFor(logging.DEBUG),
        connect_args=cls.options['database']['connection_arguments'])
        if cls.model is not None:
            cls.model.Model.metadata.create_all(cls.engine)
        '''Create a persistent inter thread database session.'''
        cls._check_database_schema_version(database_backup_file)
        if cls.controller is not None:
            cls.controller.initialize_model()
            if cls.debug:
                cls.controller.initialize_model_mockup()
        return cls

    # # # region web server

    def _start_web_server(self):
        '''Starts the web server daemon as child thread.'''
        self.__class__.web_server = WebServer(
            port=self.given_command_line_arguments.port,
            host_name=self.given_command_line_arguments.host_name,
            **self.options['web_server'])
        if builtins.callable(builtins.getattr(
            self.controller, 'initialize_frontend', None
        )):
            self.controller.initialize_frontend()
        return self.wait_for_order()

    def _web_controller(self):
        '''Handles each request to the web server.'''
        cache_file = None
        output = ''
        mime_type = 'text/html'
        cache_control_header = 'public, max-age=0'
        if '__manifest__' in self.data['get']:
            mime_type, cache_control_header, cache_file = \
                self._manifest_controller()
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

    def _manifest_controller(self):
        '''Handles each manifest request.'''
        mime_type = 'text/cache-manifest'
        cache_control_header = 'no-cache'
        '''Dynamic request should be handled by frontend cache.'''
        user = None
        manifest_name = 'generic'
        if(self.options['session']['key']['user_id'] in
           self.data['cookie'] and
           self.options['session']['key']['token'] in self.data['cookie']):
            session = create_database_session(bind=self.engine)()
            users = session.query(self.model.User).filter(
                self.model.User.id == self.data['cookie'][
                    self.options['session']['key']['user_id']])
            if users.count():
                user = users.one()
                manifest_name = user.id
            session.close()
        cache_file = FileHandler(
            location='%s%s.appcache' %
            (self.options['location']['web_cache'], manifest_name))
        if(self.given_command_line_arguments.web_cache and
           cache_file.is_file()):
            __logger__.info('Response cache from "%s".', cache_file.path)
        else:
            cache_file.content = self.get_manifest(user)
        return mime_type, cache_control_header, cache_file

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

    # # # endregion

    # # endregion

    # endregion

    # region dynamic methods

    # # region public

    # # # region getter

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
                Dictionary(content=account_data).get_immutable())
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

    # # # endregion

# # python2.7
# #     def stop(self, *arguments, **keywords):
    def stop(self, *arguments, force_stopping=False, **keywords):
# #
        '''
            This method is triggered if the application should die. The web \
            server will be closed.
        '''
# # python2.7
# #         force_stopping, keywords = Dictionary(content=keywords).pop(
# #             name='force_stopping', default_value=False)
        pass
# #
        if self.web_server:
            '''
                Take this method type by the abstract class via introspection.
            '''
            if force_stopping:
                builtins.getattr(self.web_server, inspect.stack()[0][3])(
                    *arguments, force_stopping=force_stopping, **keywords)
            else:
                with self.web_api_lock:
                    builtins.getattr(self.web_server, inspect.stack()[0][3])(
                        *arguments, force_stopping=force_stopping, **keywords)
        if not (Controller is None or self.controller is None):
            self.controller.stop(
                *arguments, force_stopping=force_stopping, **keywords)
        '''Take this method type by the abstract class via introspection.'''
        return builtins.getattr(
            builtins.super(self.__class__, self), inspect.stack()[0][3]
        )(*arguments, force_stopping=force_stopping, **keywords)

    def authenticate(self):
        '''
            Authenticates a user by potential sent header identification data.
        '''
        user_id = session_token = location = None
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

    # # endregion

    # # region protected methods

    # # # region runnable implementation

    def _initialize(self):
        '''Starts the web controller if server is already running.'''

        # # region properties

        self.data = __request_arguments__
        self.new_cookie = {}
        '''Normalize get and payload data.'''
# # python2.7
# #         self.data['get'] = Dictionary(content=self.data['get']).convert(
# #             key_wrapper=lambda key, value: self.convert_for_backend(String(
# #                 key
# #             ).camel_case_to_delimited.content if isinstance(
# #                 key, (unicode, str)
# #             ) else key), value_wrapper=self.convert_for_backend
# #         ).content
        self.data['get'] = Dictionary(content=self.data['get']).convert(
            key_wrapper=lambda key, value: self.convert_for_backend(String(
                key
            ).camel_case_to_delimited.content if isinstance(
                key, str
            ) else key), value_wrapper=self.convert_for_backend
        ).content
# #
        if builtins.isinstance(self.data['data'], builtins.list):
            for index, item in builtins.enumerate(self.data['data']):
# # python2.7
# #                 self.data['data'][index] = Dictionary(
# #                     content=item
# #                 ).convert(
# #                     key_wrapper=lambda key, value:
# #                         self.convert_for_backend(
# #                             String(
# #                                 key
# #                             ).camel_case_to_delimited.content if \
# #                                 isinstance(key, (unicode, str)) else key
# #                         ), value_wrapper=self.convert_for_backend
# #                 ).content
                self.data['data'][index] = Dictionary(
                    content=item
                ).convert(
                    key_wrapper=lambda key, value:
                        self.convert_for_backend(
                            String(
                                key
                            ).camel_case_to_delimited.content if \
                                isinstance(key, str) else key
                        ), value_wrapper=self.convert_for_backend
                ).content
# #
        else:
            if self.options['remove_duplicated_request_key']:
                for key, value in self.data['data'].items():
                    if builtins.isinstance(value, builtins.list):
                        if builtins.len(value) > 0:
                            self.data['data'][key] = value[0]
                        else:
                            self.data['data'][key] = None
# # pythoin3.4
# #             self.data['data'] = Dictionary(
# #                 content=self.data['data']
# #             ).convert(
# #                 key_wrapper=lambda key, value: self.convert_for_backend(
# #                     String(
# #                         key
# #                     ).camel_case_to_delimited.content if isinstance(
# #                         key, str
# #                     ) else key
# #                 ), value_wrapper=self.convert_for_backend
# #             ).content
            self.data['data'] = Dictionary(
                content=self.data['data']
            ).convert(
                key_wrapper=lambda key, value: self.convert_for_backend(
                    String(
                        key
                    ).camel_case_to_delimited.content if isinstance(
                        key, (unicode, str)
                    ) else key
                ), value_wrapper=self.convert_for_backend
            ).content
# #
        self.authorized_user_id = self.authenticate()

        # # endregion

        '''
            Export options to global scope to make them accessible for other \
            modules like model or controller.
        '''
        try:
            self._web_controller()
        except TemplateError as exception:
            if self.debug:
# # python2.7
# #                 self.data['handler'].send_error(500, '%s: "%s"' % (
# #                     exception.__class__.__name__, convert_to_unicode(
# #                         exception)))
                self.data['handler'].send_error(500, '%s: "%s"' % (
                    exception.__class__.__name__, builtins.str(exception)))
# #
            else:
                '''NOTE: The web server will handle this.'''
                raise
        return self

    def _run(self):
        '''Initializes the web server.'''

        # # Profiling area
        start = time.clock()
        #try:
        #    import cProfile as profile
        #except ImportError:
        #    import profile
        #profiler = profile.Profile()
        #profiler.enable()
        # #

        self.__class__.package_name = Module.get_package_name(
            frame=inspect.currentframe())
        FileHandler.set_root(location=FileHandler(location=Module.get_name(
            frame=inspect.currentframe(), path=True, extension=True
        ), output_with_root_prefix=True).directory.directory)
        self.__class__.ROOT_PATH = FileHandler.get_root().path
        highPerformanceModification.ROOT_PATH = self.ROOT_PATH
        self.__class__.controller = None
        if not (__test_mode__ or module_import_error is None):
            raise module_import_error
        self._set_options()
        self.__class__.given_command_line_arguments = \
            CommandLine.argument_parser(
                arguments=self.options['command_line_arguments'],
                module_name=__name__)
        self.__class__.debug = \
            sys.flags.debug or __logger__.isEnabledFor(logging.DEBUG)
        if Controller is not None:
            self.__class__.controller = Controller(main=self.__class__)
        self._initialize_model_module()
        self.__class__.options['frontend']['proxy'] = {'port': None}
        self.__class__.port = self.given_command_line_arguments.port
        self._determine_suitable_proxy_server()
        self.__class__.options['frontend']['proxy']['hostNamePrefix'] = \
            self.given_command_line_arguments.proxy_host_name_prefix
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
        self._initialize_templates()
        self._initialize_data_structure()

        # # Profiling area
        #profiler.disable()
        __logger__.info(
            'Elapsed time for starting webApp: %.2f seconds',
            time.clock() - start)
        #profiler.print_stats(sort=0) # Call count
        #profiler.print_stats(sort=1) # Internal function time
        #profiler.print_stats(sort=2) # Cumulative time
        # #

        if not self.given_command_line_arguments.render_template:
            return self._start_web_server()

    # # # endregion

    def _initialize_templates(self):
        '''Determines templates files and renders them.'''
        self.__class__.frontend_html_file = FileHandler(
            location=self.options['location']['html_file']['frontend'])
        self.__class__.backend_html_file = FileHandler(
            location=self.options['location']['html_file']['backend'])
        self.__class__.html_template_file = FileHandler(
            location=self.options['location']['html_file']['template'])
        self._register_authentication_handler()
        self.__class__.options['frontend'] = Dictionary(
            content=self.options['frontend']
        ).compatible_types.content
        if(self.options['initial_template_rendering'] or
           self.given_command_line_arguments.render_template):
            __logger__.info('Render template files.')
            self.render_templates(all=True, proxy_restart=True)
        return self

    def _register_authentication_handler(self):
        '''Registers a basic http authentication handler to webserver.'''
# # python2.7
# #         if self.controller is not None and builtins.isinstance(
# #             self.options['web_server'].get('authentication_handler'),
# #             (builtins.unicode, builtins.str)
# #         ):
# #             self.options['web_server']['authentication_handler'] = \
# #             builtins.eval(
# #                 self.options['web_server']['authentication_handler'],
# #                 {'controller': self.controller})
        if self.controller is not None and builtins.isinstance(
            self.options['web_server'].get('authentication_handler'),
            builtins.str
        ):
            self.options['web_server']['authentication_handler'] = \
            builtins.eval(
                self.options['web_server']['authentication_handler'],
                {'controller': self.controller})
# #
        return self

    def _initialize_data_structure(self):
        '''Initializes database and file based caching layer.'''
        self.__class__.rest_data_timestamp_reference_file = FileHandler(
            location=self.options['location']['database'][
                'rest_data_timestamp_reference_file_path'])
        if self.debug:
            self.clear_web_cache()
        if not self.rest_data_timestamp_reference_file:
            self.__class__.rest_data_timestamp_reference_file.content = ''
        if self.controller is not None:
            self.controller.launch()
        self._check_database_file_references()
        return self

    def _determine_suitable_proxy_server(self):
        '''Search for suitable proxy server.'''
        connection = HTTPConnection(
            self.given_command_line_arguments.host_name,
            self.given_command_line_arguments.proxy_ports[0])
        try:
            connection.request('HEAD', '')
        except SocketError:
            pass
        else:
            server_name = builtins.dict(
                connection.getresponse().getheaders()
            ).get('server')
            for pattern in self.SUPPORTED_PROXY_SERVER_NAME_PATTERN:
# # python2.7
# #                 if regularExpression.compile('(?:%s)$' % pattern).match(
# #                     server_name
# #                 ):
                if regularExpression.compile(pattern).fullmatch(
                    server_name
                ):
# #
                    self.__class__.port = self.__class__.proxy_port = \
                        self.given_command_line_arguments.proxy_ports[0]
                    self.__class__.options['frontend']['proxy']['port'] = \
                        self.proxy_port
                    __logger__.info(
                        'Detected proxy server "%s" at "%s" listing on '
                        'incoming requests which matches pattern "%s" on port '
                        '%d.', server_name,
                        self.given_command_line_arguments.host_name,
                        self.given_command_line_arguments.\
                            proxy_host_name_pattern,
                        self.proxy_port)
                    break
        return self

    # # endregion

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
