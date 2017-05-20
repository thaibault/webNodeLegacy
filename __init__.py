#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# region header

'''
    Provides the main entry point for the web application. Initializes models \
    and starts the web socket.
'''

# # python3.5
# # pass
from __future__ import absolute_import, division, print_function, \
    unicode_literals
# #

__author__ = 'Torben Sickert'
__copyright__ = 'see module docstring'
__credits__ = 'Torben Sickert',
__license__ = 'see module docstring'
__maintainer__ = 'Torben Sickert'
__maintainer_email__ = 'info["~at~"]torben.website'
__status__ = 'stable'
__version__ = '1.0'

# # python3.5 import builtins
import __builtin__ as builtins
from copy import copy, deepcopy
from datetime import datetime as DateTime
from datetime import time as Time
from datetime import date as Date
from datetime import timedelta as TimeDelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from httplib import HTTPConnection
import inspect
import json
import logging
import multiprocessing
import os
try:
    from cProfile import Profile as Profiler
except builtins.ImportError:
    from profile import Profile as Profiler
import re as regularExpression
from smtplib import SMTP, SMTP_SSL
import socket
from sqlite3 import Connection as SQLite3Connection
import sys
from time import clock, sleep, time
# # python3.5 pass
from time import mktime as make_time
import traceback
from unicodedata import normalize as normalize_unicode

from sqlalchemy.engine.default import DefaultExecutionContext
from sqlalchemy.exc import OperationalError
from sqlalchemy import create_engine as create_database_engine
from sqlalchemy.orm import sessionmaker as create_database_session
from sqlalchemy.schema import CreateTable, DropTable, Table, MetaData
from sqlalchemy import event as SqlalchemyEvent
from sqlalchemy.engine import Engine as SqlalchemyEngine

# # python3.5 pass
from boostnode import convert_to_string, convert_to_unicode
from boostnode.extension.file import Handler as FileHandler
from boostnode.extension.native import Object, Iterable, Dictionary, Module
from boostnode.extension.native import String
from boostnode.extension.native import __exception__ as NativeError
from boostnode.extension.output import Print
from boostnode.extension.system import CommandLine, Runnable, Platform
from boostnode.extension.system import __exception__ as BoostNodeSystemError
from boostnode.extension.type import Null
from boostnode.paradigm.objectOrientation import Class
from boostnode.runnable.server import Web as WebServer
from boostnode.runnable.template import Parser as TemplateParser
from boostnode.runnable.template import __exception__ as TemplateError
from boostnode import highPerformanceModification

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
    state = None
    '''Saves a timestamp and user id for each database instance.'''
    web_server = None
    '''Saves the web server instance.'''
    debug = False
    '''Indicates whether the application is currently in debug mode.'''
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

    # # # region getter

    @builtins.classmethod
    def get_web_asset_file_paths(cls, path=None):
        '''
            Determine a list of relative file paths needed for the web \
            application.
        '''
        paths = []
        if path is None:
            path = cls.options['location']['webAsset']
            cls._root_asset_path_len = builtins.len(FileHandler(
                location=path
            ).path)
        for file in builtins.filter(
            lambda file: cls.is_valid_web_asset(file),
            FileHandler(location=path)
        ):
            if file.is_directory():
                paths += cls._determine_file_assets(file.path)
            else:
                paths.append(file.path[cls._root_asset_path_len:])
        return paths

    @builtins.classmethod
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

    # # # region boolean

    @builtins.classmethod
    def is_valid_web_asset(cls, file):
        '''Checks if the given file is a valid web application asset.'''
        return not ((
            file.extension == TemplateParser.DEFAULT_FILE_EXTENSION and
            FileHandler(location='%s%s' % (
                file.directory.path, file.basename
            )).extension
        ) or Iterable(cls.options['webAssetPatternIgnore']).is_in_pattern(
            value=file.path))

    # # # endregion

    # # # region helper

    @builtins.classmethod
    def consolidate_field(cls, value, specification):
        '''Checks if given data is valid against given specification.'''
        if None not in (value, specification):
            if(
                specification.get('type') == 'string' or
                'minimumLength' in specification or
                'maximumLength' in specification
            ):
# # python3.5                 return builtins.str(value)
                return convert_to_unicode(value)
            elif(specification.get('type') == 'file'):
                return value
            elif(
                specification.get('type') == 'number' or
                'minimum' in specification or 'maximum' in specification
            ):
                converted_value = String(value).get_number(default=False)
                if converted_value is False:
# # python3.5
# #                     raise builtins.ValueError(
# #                         'Given value "%s" couldn\'t be interpreted as '
# #                         'number.' % builtins.str(value))
                    raise builtins.ValueError(
                        'Given value "%s" couldn\'t be interpreted as '
                        'number.' % convert_to_unicode(value))
# #
                return converted_value
        return value

    @builtins.classmethod
    def validate_field(cls, value, specification):
        '''Checks if given data is valid against given specification.'''
        if specification is not None:
            if value is None:
                return not specification.get('required', False)
            if 'choices' in specification:
                for item in specification['choices']:
                    if 'key' in item:
                        if item['key'] == value:
                            return True
                    elif item == value:
                        return True
                return False
            if specification.get('type') == 'file':
                if specification.get('required', False):
                    if not isinstance(value, dict) or not value.get(
                        'data', False
                    ):
                        return False
                    if (
                        'maximum' in specification and 'size' not in value or
                        specification['maximum'] < value['size'] or
                        specification['maximum'] < 10 * len(value['data'])
                    ):
                        return False
                    if (
                       'pattern' in specification and
                        'mimeType' not in value or regularExpression.compile(
                            '(?:%s)$' % specification['pattern']
                        ).match(value['mimeType']) is None
                    ):
                        return False
                return True
            if((
                'minimumLength' in specification and
                builtins.len(value) < specification['minimumLength']
            ) or (
                'maximumLength' in specification and
                builtins.len(value) > specification['maximumLength']
            ) or (
                'minimum' in specification and
                value < specification['minimum']
            ) or ('numberType' in specification and (
                'integer' == specification['numberType'] and
                not builtins.isinstance(
                    value, builtins.int
                ) or 'float' == specification['numberType'] and
                not builtins.isinstance(
                    value, builtins.float
                ) or 'number' == specification['numberType'] and
                not builtins.isinstance(value, (builtins.float, builtins.int))
            )) or (
                'maximum' in specification and value > specification['maximum']
            ) or ('pattern' in specification and regularExpression.compile(
# # python3.5
# #                 specification['pattern']
# #             ).fullmatch(value) is None
                '(?:%s)$' % specification['pattern']
            ).match(value) is None
# #
            )):
                return False
        return True

    @builtins.classmethod
    def send_e_mail(
        cls, content, configuration={}, attachments=[], **keywords
    ):
        '''Sends given message via mail.'''
        configuration.update(keywords)
        message = MIMEMultipart(configuration['mime_type_sub_type'])
        message['Subject'] = configuration['subject']
        message['From'] = configuration.get(
            'sender_address', configuration['login'])
        message['To'] = configuration['recipient_address']
        '''
            We support html mails and text mails as fallback. Attach parts \
            into message container. According to RFC 2046, the last part of a \
            multipart message, in this case the HTML message, is best and \
            preferred.
        '''
        if configuration['html']:
# # python3.5
# #             message.attach(MIMEText(
# #                 message, 'html', cls.options['encoding']))
# #         else:
# #             message.attach(MIMEText(
# #                 message, 'plain', cls.options['encoding']))
            message.attach(MIMEText(convert_to_string(
                content
            ), 'html', cls.options['encoding']))
        else:
            message.attach(MIMEText(convert_to_string(
                content
            ), 'plain', cls.options['encoding']))
# #
        for file in attachments:
            attachment = MIMEApplication(file['data'], Name=file['name'])
            attachment['Content-Disposition'] = 'attachment; filename="%s"' % \
                file['name']
            message.attach(attachment)
        '''Send the message specified SMTP server.'''
        connection_data = (
            configuration['smtp_server']['url'],
            configuration['smtp_server']['port'])
        if configuration.get('encryption') == 'tls':
            server = SMTP(*connection_data)
            server.ehlo_or_helo_if_needed()
            server.starttls()
        elif configuration.get('encryption') == 'ssl':
            server = SMTP_SSL(*connection_data)
        else:
            server = SMTP(*connection_data)
        if 'login' in configuration and 'password' in configuration:
            server.ehlo_or_helo_if_needed()
            try:
                server.login(configuration['login'], configuration['password'])
            except Exception as exception:
                if configuration.get('handle_exception'):
                    message = exception
                else:
                    raise
        if not isinstance(message, Exception):
            server.ehlo_or_helo_if_needed()
            try:
                server.sendmail(message['From'], message['To'] if isinstance(
                    message['To'], (tuple, list, set)
                ) else (message['To'],), message.as_string())
            except Exception as exception:
                if configuration.get('handle_exception'):
                    message = exception
                else:
                    raise
            server.ehlo_or_helo_if_needed()
            server.quit()
        return message

    @builtins.classmethod
    def determine_referenced_models(cls, model_name):
        '''Determines all linked model names for given model name.'''
        if builtins.hasattr(cls.model, model_name):
            model_column_names = builtins.filter(lambda key: '%s_%s' % (
                model_name.lower(), key
            ), builtins.map(
                lambda property: property.name, builtins.getattr(
                    cls.model, model_name
                ).__table__.columns))
            for model_name, model in builtins.filter(
                lambda model: builtins.isinstance(
                    model[1], builtins.type
                ) and builtins.issubclass(model[1], cls.model.Model),
                Module.get_defined_objects(cls.model)
            ):
                other_model_column_names = builtins.list(builtins.map(
                    lambda property: property.name, model.__table__.columns))
                for name in builtins.filter(
                    lambda name: name not in other_model_column_names,
                    model_column_names
                ):
                    yield model_name
                    break

    @builtins.classmethod
    def remove_model_cache(
        cls, model_name, flat=False, properties=(), preserve_timestamp=False,
        removed_models=None, user_id=1
    ):
        '''
            Updates model cache timestamp indicator and removes corresponding \
            static cache files.
        '''
        if not preserve_timestamp:
            cls.state.update(model_name)
        indicator = '?__model__=%s&' % model_name
        select_indicator = '&__select__='
        for file in builtins.filter(
            lambda file: model_name == 'Data' or (file.basename.endswith(
                indicator[:-1]
            ) or indicator in file.basename) and not (
                flat and properties and not (
                    select_indicator not in file.basename or builtins.len(
                        builtins.filter(
                            lambda property: regularExpression.compile(
                                '^.*\?%s.*%s(?:.+,)?%s(,.+)?$' % (
                                    indicator[1:-1], select_indicator, String(
                                        property
                                    ).delimited_to_camel_case.content)
                            ).match(file.basename), properties))
            )), FileHandler(location=cls.options['location']['webCache'])
        ):
            file.remove_file()
        if not flat:
            if removed_models is None:
                removed_models = {model_name}
            else:
                removed_models.add(model_name)
            for linked_model_name in builtins.filter(
                lambda name: name not in removed_models,
                cls.determine_referenced_models(model_name)
            ):
                cls.remove_model_cache(
                    model_name=linked_model_name, flat=flat, properties=(),
                    preserve_timestamp=preserve_timestamp,
                    removed_models=removed_models, user_id=user_id)
        return cls

    @builtins.classmethod
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

    @builtins.classmethod
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
        cls.options = Dictionary(content=cls.options).get_rendered(
            mapping=cls.options, module_name=__name__, main=cls)
        frontend_options = cls.options['frontend']
        del cls.options['frontend']
        '''
            After converting keys to backend compatible types we now convert \
            the values after rendering phase.
        '''
        cls.options = Dictionary(content=cls.options).convert(
            value_wrapper=cls.convert_for_backend,
            remove_no_wrap_indicator=remove_no_wrap_indicator
        ).content
        cls.options['frontend'] = frontend_options
        return cls

    @builtins.classmethod
    def render_templates(cls, all=False, initialize=False):
        '''Renders all template files.'''
        mapping = cls.controller.get_template_scope(scope=deepcopy({
            'options': deepcopy(cls.options), 'debug': cls.debug,
            'given_command_line_arguments': cls.given_command_line_arguments,
            'root': FileHandler.get_root(), 'proxy_port': cls.proxy_port}))
        if 'admin' in mapping['options']['frontend']:
            del mapping['options']['frontend']['admin']
        if all:
            FileHandler(location='/').iterate_directory(
                function=cls._render_template, recursive=True, mapping=mapping,
                initialize=initialize)
            cls._reinitialize_proxy_server()
        cls._render_html_templates(mapping)
        return cls

    @builtins.classmethod
    def clear_web_cache(cls):
        '''Clears all web cache files.'''
        web_cache = FileHandler(location=cls.options['location']['webCache'])
        if web_cache.is_directory():
            __logger__.info('Clear web cache in "%s".', web_cache.path)
            web_cache.remove_deep()
        template_cache = FileHandler(
            location=cls.options['location']['templateCache'])
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

    @builtins.classmethod
    def convert_for_client(cls, key, value=Null):
        '''Returns the serialized version of given value.'''
        if value is Null:
            value = key
# # python3.5
# #         if(builtins.isinstance(key, builtins.str) and (
# #             key == 'language' or key.endswith('_language') or
# #             key.endswith('Language')
# #         )) and regularExpression.compile('[a-z]{2}_[a-z]{2}').fullmatch(
# #             value
# #         ):
# #             return '%s%s' % (String(
# #                 value
# #             ).delimited_to_camel_case.content[:-1], value[-1].upper())
        if(builtins.isinstance(key, builtins.unicode) and (
            key == 'language' or key.endswith('_language') or
            key.endswith('Language')
        )) and regularExpression.compile('[a-z]{2}_[a-z]{2}$').match(value):
            return '%s%s' % (
                String(value).delimited_to_camel_case.content[:-1],
                convert_to_unicode(value[-1].upper()))
# #
        return Object(content=value).compatible_type

    @builtins.classmethod
    def convert_for_backend(cls, key, value=Null):
        '''Converts data from client to python specific data objects.'''
        if value is Null:
            value = key
        if 'dataKeysIgnore' in cls.options and key in cls.options[
            'dataKeysIgnore'
        ]:
            return value
        try:
            return Object(content=value).get_known_type(
                description=None if key == value else key)
        except NativeError:
            return value

    @builtins.classmethod
    def extend_user_authorization(cls, user_id, session_token, location=None):
        '''
            Extends user authorization time. If successfully the user id will \
            be returned and "None" otherwise.
        '''
        result = None
        maximum_number_of_tries = 10
        number_of_tries = 1
        while(
            user_id and session_token and
            number_of_tries < maximum_number_of_tries
        ):
            user_id = builtins.int(user_id)
            try:
                session = create_database_session(bind=cls.engine)()
                '''
                    NOTE: Do not refactor "== True" to "is True" since the \
                    equal operator is overwritten by the orm.
                '''
                users = session.query(cls.model.User).filter(
                    cls.model.User.enabled == True,
                    cls.model.User.id == user_id,
                    cls.model.User.sessionToken == session_token,
                    cls.model.User.sessionExpirationDateTime > DateTime.now())
                if users.count() == 0 and cls.options[
                    'adminAuthenticatesAll'
                ] and session.query(cls.model.User).filter(
                    cls.model.User.enabled == True,
                    cls.model.User.id == 1,
                    cls.model.User.sessionToken == session_token,
                    cls.model.User.sessionExpirationDateTime > DateTime.now()
                ).count():
                    users = session.query(cls.model.User).filter(
                        cls.model.User.enabled == True,
                        cls.model.User.id == user_id)
                if users.count():
                    user = users.one()
                    user.sessionExpirationDateTime = DateTime.now(
                    ) + cls.options['session']['expirationTimeDelta']
                    __logger__.info(
                        'Authorize user with id %d for %.2f hours.', user.id, (
                            cls.options['session'][
                                'expirationTimeDelta'
                            ].total_seconds() / 60) / 60)
                    if location is not None and user.location != location:
                        user.location = location
                        cls.remove_model_cache(
                            model_name=cls.model.User.__name__, flat=True,
                            preserve_timestamp=not cls.options['session'][
                                'clearCacheOnUsersLocationChange'])
                    result = user.id
                    session.commit()
            except OperationalError as exception:
                session.close()
# # python3.5
# #                 if 'database is locked' in builtins.str(exception):
# #                     if number_of_tries >= maximum_number_of_tries:
# #                         raise
# #                     __logger__.warning(
# #                         'Database seems to be locked. Retrying to connect'
# #                         ' (%d. try of %d). %s: %s', number_of_tries,
# #                         maximum_number_of_tries,
# #                         exception.__class__.__name__,
# #                         builtins.str(exception))
                if 'database is locked' in builtins.str(exception):
                    if number_of_tries >= maximum_number_of_tries:
                        raise
                    __logger__.warning(
                        'Database seems to be locked. Retrying to connect'
                        ' (%d. try of %d). %s: %s', number_of_tries,
                        maximum_number_of_tries,
                        exception.__class__.__name__,
                        builtins.str(exception))
# #
                    number_of_tries += 1
                    sleep(1)
                    continue
                raise
            else:
                session.close()
                break
        return result

    # # # endregion

    # # endregion

    # # region protected

    @builtins.classmethod
    def _reinitialize_proxy_server(cls):
        '''
            Restarts of reloads an existing proxy server. This is needed \
            after configuration file updates for example.
        '''
        if(
            cls.options['proxyServerSystemReloadCommand'] and
            cls.proxy_port is not None
        ):
            __logger__.debug(
                'Run "%s".', cls.options['proxyServerSystemReloadCommand'])
            try:
                Platform.run(
                    command=cls.options['proxyServerSystemReloadCommand'],
                    shell=True)
            except BoostNodeSystemError as exception:
                __logger__.warning(
                    '%s: %s You may have a miss configured proxy server at '
                    'port %d or we have not enough permissions to control the '
                    'proxy server. Command was "%s".',
                    exception.__class__.__name__, builtins.str(exception),
                    cls.proxy_port,
                    cls.options['proxyServerSystemReloadCommand'])
        return cls

    @builtins.classmethod
    def _render_template(cls, file, mapping, initialize):
        '''
            Renders each template and distinguishes between backend and \
            frontend templates.
        '''
        if(
            file.name.startswith(('.', '_')) or file.is_symbolic_link() or
            file.path in cls.options['location']['templateIgnore'] or
            not initialize and
            file.path in cls.options['location']['templateOnce']
        ):
            '''Don't enter ignored locations or parse ignored files.'''
            return None
# # python3.5
# #         if(file.extension == TemplateParser.DEFAULT_FILE_EXTENSION and
# #            FileHandler(location='%s%s' % (
# #                file.directory.path, file.basename
# #            )).extension and file != cls.html_template_file):
        if(file.extension == TemplateParser.DEFAULT_FILE_EXTENSION and
           FileHandler(location='%s%s' % (
               file.directory.path, file.basename
           )).extension and not (file == cls.html_template_file)):
# #
            result, mapping = cls._render_template_helper(file, mapping)
            output_file = FileHandler(location='%s%s' % (
                file.directory.path, file.name[:-builtins.len('%s%s' % (
                    os.extsep, TemplateParser.DEFAULT_FILE_EXTENSION))]))
            output_file.content = normalize_unicode(
                cls.options['unicodeNormalisationForm'], result)
            cls.controller.post_template_file_rendering(
                output_file, file, scope=mapping)
        return cls

    @builtins.classmethod
    def _render_html_templates(cls, mapping):
        '''Renders all frontend html templates.'''
        if cls.html_template_file.is_file():
            for site in ('frontend', 'backend'):
                '''
                    NOTE: Only build and admin file if there exists an admin \
                    section in frontend options.
                '''
                if site == 'frontend' or 'admin' in cls.options['frontend']:
                    result, mapping = cls._render_template_helper(
                        cls.html_template_file, mapping,
                        force_backend=site == 'backend')
                    output_file = builtins.getattr(cls, '%s_html_file' % site)
                    output_file.content = normalize_unicode(
                        cls.options['unicodeNormalisationForm'], result)
                    cls.controller.post_template_file_rendering(
                        output_file, file=cls.html_template_file,
                        scope=mapping)
        return cls

    @builtins.classmethod
    def _render_template_helper(cls, file, mapping, force_backend=False):
        '''Renders a concrete template file.'''
        is_backend = force_backend
        '''
            Check if any parent folder has the "backend" prefix to indicate \
            frontend or template scope for current template.
        '''
        if file.name.startswith('backend') or file.directory.path == '/':
            is_backend = True
        parent_folder = file.directory
        while True:
            if parent_folder.name.startswith('backend'):
                is_backend = True
            if parent_folder == FileHandler.get_root() or is_backend:
                break
            parent_folder = parent_folder.directory
        __logger__.debug(
            'Render "%s" for %s.', file.path,
            'backend' if is_backend else 'frontend')
        '''
            NOTE: This is necessary to avoid having any modifications in \
            another template.
        '''
        mapping = deepcopy(mapping)
        mapping['options']['frontend']['admin'] = (
            is_backend and 'admin' in cls.options['frontend'])
        if mapping['options']['frontend']['admin']:
            mapping['options']['frontend'] = Dictionary(
                content=mapping['options']['frontend']
            ).update(cls.options['frontend']['admin']).content
        mapping = cls.controller.get_template_file_scope(file, scope=mapping)
        return TemplateParser(
            file, template_context_default_indent=cls.options[
                'defaultIndentLevel']
        ).render(mapping=mapping).output, mapping

    @builtins.classmethod
    def _check_dead_soft_references(cls):
        '''Searches for unneeded database entities.'''
        everything_accepted = False
        session = create_database_session(
            bind=cls.engine, expire_on_commit=False
        )()
        property_names = cls.given_command_line_arguments.\
            dead_soft_reference_check_properties
        for model_name, model in builtins.filter(
            lambda model: builtins.isinstance(
                model[1], builtins.type
            ) and builtins.issubclass(model[1], cls.model.Model),
            Module.get_defined_objects(cls.model)
        ):
            if model_name not in cls.given_command_line_arguments.\
            dead_soft_reference_check_exceptions and all(map(
                lambda property_name: hasattr(model, property_name),
                property_names
            )):
                everything_accepted = cls._check_dead_soft_references_in_model(
                    session, model_name, model, property_names,
                    everything_accepted)
                if everything_accepted is None:
                    session.close()
                    return cls
        session.close()
        return cls

    @builtins.classmethod
    def _check_dead_soft_references_in_model(
        cls, session, model_name, model, property_names, everything_accepted
    ):
        '''Searches for unneeded database entities in given model.'''
        for property in builtins.filter(
            lambda property: property.name.endswith(
                '_id'
            ) or property.name.endswith('ID'), model.__table__.columns
        ):
            referencing_model = getattr(cls.model, String(property.name[:-len(
                '_id' if property.name.endswith('_id') else 'ID'
            )]).delimited_to_camel_case.camel_case_capitalize.content, None)
            if referencing_model is not None and all(map(
                lambda property_name: hasattr(
                    referencing_model, property_name
                ), property_names
            )):
                for model_instance, reference_value in session.query(
                    model, property
                ):
                    everything_accepted = \
                    cls._check_dead_soft_references_in_model_instance(
                        session, model, model_instance, reference_value,
                        property, property_names, referencing_model,
                        everything_accepted)
                    if everything_accepted is None:
                        return everything_accepted
        return everything_accepted

    @builtins.classmethod
    def _check_dead_soft_references_in_model_instance(
        cls, session, model, model_instance, reference_value, property,
        property_names, referencing_model, everything_accepted
    ):
        '''
            Searches for unneeded database entities in given model instance \
            for given property.
        '''
        referencing_model_instances = session.query(
            referencing_model
        ).filter_by(id=reference_value)
        if referencing_model_instances.count():
            referencing_model_instance = referencing_model_instances.one()
            broken_reference = False
            for property_name in filter(lambda property_name: getattr(
                referencing_model_instance, property_name
            ) != getattr(model_instance, property_name), property_names):
                broken_reference = True
                break
            if broken_reference:
                if everything_accepted:
                    answer = True
                else:
                    try:
                        answer = CommandLine.boolean_input(
                            question='Model (%s) has a hard reference via '
                                     'attribute "%s" with value "%s" and a '
                                     'dead soft reference via attribute "%s" '
                                     'with source value "%s" and target value '
                                     '"%s". Do you want to delete this record?'
                                     ' {boolean_arguments}: ' % (
                                builtins.repr(model_instance), property.name,
                                reference_value, property_name,
                                reference_value, getattr(
                                    referencing_model_instance, property_name)
                            ), extra=('a', 'all', 'none', 'nothing'))
                    except(builtins.IOError, builtins.EOFError):
                        __logger__.info(
                            'We have lost standard input. Receiving an stop '
                            'order via standard input is impossible from now '
                            'on. Setting answer to "none".')
                        answer = 'none'
                if answer in ('none', 'nothing'):
                    return None
                if answer in ('a', 'all'):
                    answer = everything_accepted = True
                if answer:
                    session.query(model).filter_by(
                        **model_instance.dictionary
                    ).delete()
                    session.commit()
        return everything_accepted

    @builtins.classmethod
    def _check_database_file_references(cls):
        '''
            Checks if all file references saved in database records exists. \
            If a dead link was found the user will be asked for deleting \
            referenced database records.
        '''
        everything_accepted = False
        session = create_database_session(
            bind=cls.engine, expire_on_commit=False
        )()
        for model_name, model in builtins.filter(
            lambda model: builtins.isinstance(
                model[1], builtins.type
            ) and builtins.issubclass(model[1], cls.model.Model),
            Module.get_defined_objects(cls.model)
        ):
            for property in builtins.filter(
                lambda property: property.info and 'file_reference' in
                property.info, model.__table__.columns
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
                        'Check file reference "%s" for model "%s".', file.path,
                        model_name)
                    if not file:
                        everything_accepted = cls._handle_dead_file_reference(
                            session, model, model_instance, property, file,
                                everything_accepted)
                        if everything_accepted is None:
                            session.close()
                            return cls
        session.close()
        return cls

    @builtins.classmethod
    def _handle_dead_file_reference(
        cls, session, model, model_instance, property, file,
        everything_accepted
    ):
        '''Asks for deletion for given dead file reference.'''
        if everything_accepted:
            answer = True
        else:
            try:
                answer = CommandLine.boolean_input(
                    question='Model %s has a dead file reference via '
                             'attribute "%s" to "%s". Do you want to delete '
                             'this record? {boolean_arguments}: ' % (
                        builtins.repr(model_instance), property.name,
                        file.path
                    ), extra=('a', 'all', 'none', 'nothing'))
            except(builtins.IOError, builtins.EOFError):
                __logger__.info(
                    'We have lost standard input. Receiving an stop order via '
                    'standard input is impossible from now on. Setting answer '
                    'to "none".')
                answer = 'none'
        if answer in ('none', 'nothing'):
            return None
        if answer in ('a', 'all'):
            answer = everything_accepted = True
        if answer:
            session.query(model).filter_by(**model_instance.dictionary).delete(
            )
            session.commit()
        return everything_accepted

    @builtins.classmethod
    def _check_database_schema_version(cls, database_backup_file):
        '''Checke if the database schema has changed.'''
        if cls.model is None:
            return cls
        old_schemas = {}
        serialized_schema = ''
        database_schema_file = FileHandler(
            location=cls.options['location']['database']['schemaFile'])
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
# # python3.5
# #             new_schemas[model.__tablename__] = builtins.str(CreateTable(
# #                 model.__table__))
            new_schemas[model.__tablename__] = convert_to_unicode(
                CreateTable(model.__table__))
# #
            if model.__tablename__ in old_schemas:
                # TODO Schemas can have equivalent different string caused be
                # different property ordering.
                # USE: cursor.execute('PRAGMA table_info(content)'):
# # python3.5
# #                 if(old_schemas[model.__tablename__] !=
# #                    new_schemas[model.__tablename__] and False):
                if(old_schemas[model.__tablename__] !=
                   new_schemas[model.__tablename__]):
# #
                    __logger__.info('Model "%s" has changed.', model_name)
                    __logger__.debug(
                        'Old schema was "%s" and new schema is "%s".',
                        old_schemas[model.__tablename__],
                        new_schemas[model.__tablename__])
                    migration_successful = cls._migrate_model(
                        model_name, model, models, migration_successful,
                        session, old_schemas, new_schemas)
            else:
                __logger__.info('New model "%s" detected.', model_name)
                '''NOTE: sqlalchemy will create this table automatically.'''
        cls._save_database_schema(database_schema_file, session, new_schemas)
        session.close()
        if not migration_successful:
            sys.exit(1)
        return cls._save_database_backup(
            database_schema_file, serialized_schema, database_backup_file)

    @builtins.classmethod
    def _migrate_model(
        cls, model_name, model, models, migration_successful, session,
        old_schemas, new_schemas
    ):
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
# # python3.5
# #             __logger__.debug(
# #                 'Transferring record "%s".', '", "'.join(builtins.map(
# #                     lambda value: builtins.str(value), values)))
            __logger__.debug(
                'Transferring record "%s".', '", "'.join(builtins.map(
                    lambda value: convert_to_unicode(value), values)))
# #
            try:
                session.execute(temporary_table.insert(builtins.dict(
                    builtins.zip(old_columns.keys(), values))))
            except builtins.Exception as exception:
# # python3.5
# #                 __logger__.critical(
# #                     '%s: %s', exception.__class__.__name__,
# #                     builtins.str(exception))
                __logger__.critical(
                    '%s: %s', exception.__class__.__name__,
                    convert_to_unicode(exception))
# #
                migration_successful = False
        session.commit()
        if(migration_successful and
           cls.options['database']['enginePrefix'].startswith('sqlite:')):
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

    @builtins.classmethod
    def _save_database_backup(
        cls, database_schema_file, serialized_schema, database_backup_file
    ):
        '''Saves a database backup of current database state.'''
        if (
            database_schema_file.content != serialized_schema and
            database_backup_file
        ):
            now = DateTime.now()
# # python3.5
# #             timestamp = now.timestamp() + now.microsecond / 1000 ** 2
            timestamp = make_time(now.timetuple()) + \
                now.microsecond / 1000 ** 2
# #
            long_term_database_file = FileHandler(location='%s%s%d%s' % (
                database_backup_file.directory.path,
                database_backup_file.basename, timestamp,
                database_backup_file.extension_suffix))
            __logger__.info(
                'Save long term database file "%s".',
                long_term_database_file.path)
            long_term_database_file.directory.make_directories()
            database_backup_file.copy(target=long_term_database_file)
        return cls

    @builtins.classmethod
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
# # python3.5
# #         database_schema_file.content = json.dumps(
# #             new_schemas, sort_keys=True,
# #             indent=cls.options['defaultIndentLevel'])
        database_schema_file.content = json.dumps(
            new_schemas, encoding=cls.options['encoding'],
            sort_keys=True, indent=cls.options['defaultIndentLevel'])
# #
        return cls

    @builtins.classmethod
    def _append_model_informations_to_options(cls):
        '''Appends validation strings to the global options object.'''
        '''
            NOTE: If final option consolidation is activated we don't have to \
            explicitly prevent type property rendering.
        '''
        cls.options['type'] = {'__no_wrapping__': {}}
        option_target = cls.options['type']['__no_wrapping__']
        if cls.options['finalOptionConsolidation']:
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

    @builtins.classmethod
    def _determine_property_information(cls, property):
        result = copy(property.info) if property.info else {}
        result['maximumLength'] = property.type.length if builtins.hasattr(
            property.type, 'length'
        ) and builtins.isinstance(
            property.type.length, builtins.int
        ) else cls.options['database']['maximumFieldSize']
        result['required'] = not (builtins.hasattr(
            property, 'nullable'
        ) and property.nullable)
        if builtins.hasattr(
            property, 'default'
        ) and property.default is not None:
            result['required'] = False
            result['defaultValue'] = property.default.arg
            if builtins.callable(result['defaultValue']):
                if builtins.hasattr(
                    cls.model, 'determine_language_specific_default_value'
                ) and result[
                    'defaultValue'
                ] == cls.model.determine_language_specific_default_value:
                    result['defaultValue'] = Dictionary(
                        content=cls.options['model']['generic'][
                            'languageSpecific'
                        ]['default'][property.name]).convert(
                            key_wrapper=lambda key, value: cls
                            .convert_for_client(String(
                                key
                            ).delimited_to_camel_case.content)
                        ).content
                else:
                    result['defaultValue'] = cls.convert_for_client(
                        key=property.name, value=property.default.arg(
                            DefaultExecutionContext()))
            else:
                result['defaultValue'] = cls.convert_for_client(
                    key=property.name, value=result['defaultValue'])
        return result

    @builtins.classmethod
    def _merge_options(cls):
        '''Merge frontend and backend options.'''
        cls.options = Dictionary(content=cls.options).update(
            deepcopy(cls.options['both'])
        ).update(cls.options['backend']).content
        cls.options['frontend'] = Dictionary(
            content=deepcopy(cls.options['both'])
        ).update(cls.options['frontend']).content
        return cls

    @builtins.classmethod
    def _set_options(cls):
        '''Renders backend and frontend options.'''
        configuration_file = FileHandler(location=cls.CONFIGURATION_FILE_PATH)
        cls.options = json.loads(FileHandler(
            location='/%s%s' % (cls.package_name, configuration_file.path)
        ).content)
        if configuration_file.is_file():
            options = json.loads(configuration_file.content)
            return cls.extend_options(
                options=options, remove_no_wrap_indicator=options.get(
                    'backend', {}
                ).get(
                    'finalOptionConsolidation',
                    cls.options['backend']['finalOptionConsolidation']))
        return cls.consolidate_options(
            remove_no_wrap_indicator=cls.options['finalOptionConsolidation'])

    @SqlalchemyEvent.listens_for(SqlalchemyEngine, 'connect')
    def _set_database_initialisation(dbapi_connection, connection_record):
        '''Activates configured database features.'''
        if builtins.isinstance(dbapi_connection, SQLite3Connection):
            cursor = dbapi_connection.cursor()
            for command in OPTIONS['database']['initialisationCommands']:
                cursor.execute(command)
            cursor.close()

    @builtins.classmethod
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

    @builtins.classmethod
    def _initialize_model(cls):
        '''Initializes the model.'''
        if 'coreBackendNoAutomaticModelMigration' not in \
        cls.given_command_line_arguments.flags:
            database_backup_file = FileHandler(location='%sDataBackup.sql' % (
                cls.options['location']['database']['backup']))
            if cls.options['database']['enginePrefix'].startswith('sqlite:'):
                database_file = FileHandler(
                    location=cls.options['location']['database']['url'])
                database_backup_file = FileHandler(location='%s%sBackup%s' % (
                    cls.options['location']['database']['backup'],
                    database_file.basename, database_file.extension_suffix))
                database_file.directory.make_directories()
                if database_file:
                    __logger__.info(
                        'Backup database "%s" to "%s".', database_file.path,
                        database_backup_file.path)
                    database_backup_file.directory.make_directories()
                    database_file.copy(target=database_backup_file)
        root_path = cls.ROOT_PATH
        if root_path.endswith(os.sep):
            root_path = root_path[:-1]
        cls.engine = create_database_engine('%s%s%s' % (
            cls.options['database']['enginePrefix'], root_path,
            cls.options['location']['database']['url']
        ), echo=__logger__.isEnabledFor(
            'coreBackendDatabaseLogging' in \
            cls.given_command_line_arguments.flags
        ), connect_args=cls.options['database']['connectionArguments'])
        if 'coreBackendNoAutomaticModelMigration' not in \
        cls.given_command_line_arguments.flags:
            if cls.model is not None:
                cls.model.Model.metadata.create_all(cls.engine)
            cls._check_database_schema_version(database_backup_file)
        if not (
            'coreBackendNoModelMockupCreation' in \
            cls.given_command_line_arguments.flags or cls.controller is None
        ):
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
            **Dictionary(self.options['webServer']).convert(
                key_wrapper=lambda key, value: String(
                    key
                ).camel_case_to_delimited.content
            ).content)
        if builtins.callable(builtins.getattr(
            self.controller, 'initialize_frontend', False
        )):
            self.controller.initialize_frontend()
        return self.wait_for_order()

    def _web_controller(self):
        '''Handles each request to the web server.'''
        cache_file = None
        output = ''
        mime_type = 'text/html'
        cache_control_header = 'public, max-age=0'
        if '__manifest__' in self.request['get']:
            mime_type, cache_control_header, cache_file = \
                self._manifest_controller()
        elif '__model__' in self.request['get']:
            mime_type = 'application/json'
            output, mime_type, cache_control_header, cache_file = RestResponse(
                web_node=self, mime_type=mime_type,
                cache_control_header=cache_control_header
            ).output
            if not output:
                mime_type = 'text/plain'
        elif '__offline__' in self.request['get']:
            __logger__.critical(
                'Ressource "%s" couldn\'t be determined by client.',
                self.request['get']['__offline__'])
        else:
            output, mime_type, cache_control_header, cache_file = \
                self.controller.response(
                    web_node=self, mime_type=mime_type,
                    cache_control_header=cache_control_header)
        if cache_file:
            # TODO could throw an exception if cache file is deleted within the
            # next two code lines.
            self._produce_cache_file_headers(
                cache_file, mime_type, cache_control_header)
            output = cache_file.content
        else:
            self.request['handler'].send_content_type_header(
                mime_type=mime_type
            ).send_static_file_cache_header(
                cache_control_header=cache_control_header)
        if self.new_cookie:
            self.request['handler'].send_cookie(
                self.new_cookie, maximum_age_in_seconds=self.options[
                    'maximumCookieAgeInSeconds'])
        Print(normalize_unicode(
            self.options['unicodeNormalisationForm'], output
        ), end='')
        return self

    def _manifest_controller(self):
        '''Handles each manifest request.'''
        mime_type = 'text/cache-manifest'
        cache_control_header = 'no-cache'
        '''Dynamic request should be handled by frontend cache.'''
        user = None
        manifest_name = 'generic'
        if 'id' in self.request['get']:
            session = create_database_session(bind=self.engine)()
            users = session.query(self.model.User).filter(
                self.model.User.id == self.request['get']['id'])
            if users.count():
                user = users.one()
                manifest_name = user.id
        elif(self.options['session']['key']['userID'] in
           self.request['cookie'] and
           self.options['session']['key']['token'] in self.request['cookie']):
            session = create_database_session(bind=self.engine)()
            users = session.query(self.model.User).filter(
                self.model.User.id == self.request['cookie'][
                    self.options['session']['key']['userID']])
            if users.count():
                user = users.one()
                manifest_name = user.id
            session.close()
        cache_file = FileHandler(location='%s%s/%s.appcache' % (
            self.options['location']['webCache'], self.request['host'],
            manifest_name))
        # TODO only use web_cache in nginx conf if cli option is set.
        if(self.given_command_line_arguments.web_cache and
           cache_file.is_file()):
            __logger__.info(
                'Response manifest cache from "%s".', cache_file.path)
        else:
            cache_file.directory.make_directories()
            cache_file.content = self.get_manifest(user)
        return mime_type, cache_control_header, cache_file

    def _produce_cache_file_headers(
        self, cache_file, mime_type, cache_control_header
    ):
        '''Produces http headers for given server sided cache file.'''
        cache_timestamp = cache_file.timestamp
        if(mime_type != 'text/cache-manifest' and
           self.request['handler'].headers.get(
               'if-modified-since'
           ) == self.request['handler'].date_time_string(cache_timestamp)):
            __logger__.info(
                'Sent not modified header (304) for "%s".',
                cache_file.path)
            return self.request['handler'].send_content_type_header(
                response_code=304, mime_type=mime_type
            ).send_static_file_cache_header(
                timestamp=cache_timestamp,
                cache_control_header=cache_control_header)
        self.request['handler'].send_content_type_header(
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
        asset_files = builtins.set()

        def add_asset_file(file):
            '''Append each valid asset to the asset file list.'''
            if self.is_valid_web_asset(file):
                if file.is_file():
                    asset_files.add(file)
                return True
        FileHandler(
            location=self.options['location']['webAsset']
        ).iterate_directory(add_asset_file, recursive=True)
        scope = {
            'options': self.options['frontend'], 'assetFileHashs': {},
            'assetFiles': asset_files, 'htmlFile': self.frontend_html_file,
            'assetVersion': self.get_timestamps(
                self.options['location']['webAsset']
            ), 'version': '%s - %s' % (__version__, FileHandler(
                location=Module.get_name(
                    path=True, extension=True, frame=inspect.currentframe())
            ).hash), 'user': user, 'host': self.request['handler'].host,
            'offlineManifestTemplateFile': self.offline_manifest_template_file
        }
        return TemplateParser(
            self.offline_manifest_template_file,
            template_context_default_indent=self.options['defaultIndentLevel']
        ).render(mapping=self.controller.get_manifest_scope(
            scope, web_node=self, user=user
        )).output

    # # # endregion

# # python3.5
# #     def stop(self, *arguments, force_stopping=False, **keywords):
    def stop(self, *arguments, **keywords):
# #
        '''
            This method is triggered if the application should die. The web \
            server will be closed.
        '''
# # python3.5
# #         pass
        force_stopping, keywords = Dictionary(
            content=keywords
        ).pop_from_keywords(name='force_stopping', default_value=False)
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
        if self.debug and '__authentication_skip__' in self.request['get']:
            return 1
        user_id = session_token = location = None
        if self.options['authenticationMethod'] == 'header':
            user_id = self.request['handler'].headers.get(String(
                self.options['session']['key']['userID']
            ).get_camel_case_to_delimited(delimiter='-').content)
            session_token = self.request['handler'].headers.get(String(
                self.options['session']['key']['token']
            ).get_camel_case_to_delimited(delimiter='-').content)
            if self.request['type'] != 'head':
                location = self.request['handler'].headers.get(String(
                    self.options['session']['key']['location']
                ).get_camel_case_to_delimited(delimiter='-').content)
        elif self.options['authenticationMethod'] == 'cookie':
            user_id = self.request['cookie'].get(
                self.options['session']['key']['userID'])
            session_token = self.request['cookie'].get(
                self.options['session']['key']['token'])
            if self.request['type'] != 'head':
                location = self.request['cookie'].get(
                    self.options['session']['key']['location'])
        return self.extend_user_authorization(user_id, session_token, location)

    # # endregion

    # # region protected methods

    # # # region runnable implementation

    def _initialize(self):
        '''Starts the web controller if server is already running.'''

        try:

            # region handle error reports

            if __request_arguments__['externalURI'] == '/__error_report__':
                error_report_message = json.dumps(
                    __request_arguments__, skipkeys=True, ensure_ascii=False,
                    check_circular=True, allow_nan=True, indent=4,
                    separators=(',', ': '), sort_keys=True,
                    default=lambda object: '__not_serializable__')
                if not self.proxy_port:
# # python3.5
# #                     error_report_file = FileHandler(
# #                         location='%s%s.json' % (
# #                             self.options['location'][
# #                                 'reportedClientError'],
# #                             builtins.str(DateTime.now())))
                    error_report_file = FileHandler(
                        location='%s%s.json' % (
                            self.options['location'][
                                'reportedClientError'],
                            convert_to_unicode(DateTime.now())))
# #
                    while error_report_file:
                        error_report_file = FileHandler(
                            location=error_report_file.path + '-')
                    error_report_file.content = error_report_message
                if self.options['productionExceptionEMailNotification'][
                    'frontend'
                ] and not self.debug:
                    self.send_e_mail(
                        content=error_report_message,
                        configuration=Dictionary(self.options[
                            'productionExceptionEMailNotification'
                        ]).convert(key_wrapper=lambda key, value: String(
                            key
                        ).camel_case_to_delimited.content).content,
                        attachments=[], subject='Frontend-Error')
                Print(normalize_unicode(
                    self.options['unicodeNormalisationForm'],
                    self.options['errorReportAnswerHTMLContent'] %
                    'Client error successfully reported.'
                ), end='')
                return self

            # endregion

            # region properties

            self.request = __request_arguments__
            self.new_cookie = {}
            '''Normalize get and payload data.'''
            self.request['get'] = Dictionary(
                content=self.request['get']
            ).convert(value_wrapper=self.convert_for_backend).content
            self._handle_request_data()
            '''
                NOTE: Head requests should be fast and multi process save. So \
                database connection shouldn't be used for non multi process \
                save database systems.
            '''
            if self.request['type'] != 'head':
                self.authorized_user_id = self.authenticate()

            # endregion

            # region handle web controller

            '''
                Export options to global scope to make them accessible for other \
                modules like model or controller.
            '''
            try:
                self._web_controller()
            except TemplateError as exception:
                if self.debug:
# # python3.5
# #                 self.request['handler'].send_error(500, '%s: "%s"' % (
# #                     exception.__class__.__name__, builtins.str(exception)))
                    self.request['handler'].send_error(500, '%s: "%s"' % (
                        exception.__class__.__name__, convert_to_unicode(
                            exception)))
# #
                else:
                    '''NOTE: The web server will handle this.'''
                    raise

            # endregion

        except (socket.herror, socket.gaierror, socket.timeout, socket.error):
            pass
        except builtins.Exception as exception:
            if self.options['productionExceptionEMailNotification'][
                'backend'
            ] and not self.debug:
# # python3.5
# #                 message = self.send_e_mail(
# #                     content='%s:\n\n%s\n\nRequest:\n\n%s\n\nStack:\n\n%s' %
# #                     (
# #                         exception.__class__.__name__,
# #                         convert_to_unicode(exception), json.dumps(
# #                             __request_arguments__, skipkeys=True,
# #                             ensure_ascii=False, check_circular=True,
# #                             allow_nan=True, indent=4,
# #                             separators=(',', ': '), sort_keys=True,
# #                             default=lambda object: '__not_serializable__'
# #                         ), traceback.format_exc()
# #                     ), content=convert_to_unicode(exception),
# #                     configuration=Dictionary(self.options[
# #                         'productionExceptionEMailNotification'
# #                     ]).convert(key_wrapper=lambda key, value: String(
# #                         key
# #                     ).camel_case_to_delimited.content).content,
# #                     attachments=[], subject='Backend-Error (%s: %s)' % (
# #                         exception.__class__.__name__,
# #                         builtins.str(exception)))
                message = self.send_e_mail(
                    content='%s:\n\n%s\n\nRequest:\n\n%s\n\nStack:\n\n%s' %
                    (
                        exception.__class__.__name__,
                        convert_to_unicode(exception), json.dumps(
                            __request_arguments__, skipkeys=True,
                            ensure_ascii=False, check_circular=True,
                            allow_nan=True, indent=4,
                            separators=(',', ': '), sort_keys=True,
                            default=lambda object: '__not_serializable__'
                        ), convert_to_unicode(traceback.format_exc())
                    ), configuration=Dictionary(self.options[
                        'productionExceptionEMailNotification'
                    ]).convert(key_wrapper=lambda key, value: String(
                        key
                    ).camel_case_to_delimited.content).content,
                    attachments=[], subject='Backend-Error (%s)' % (
                        exception.__class__.__name__))
# #
                if builtins.isinstance(message, builtins.Exception):
# # python3.5
# #                     __logger__.warning(
# #                         '%s: %s', message.__class__.__name__,
# #                         builtins.str(message))
                    __logger__.warning(
                        '%s: %s', message.__class__.__name__,
                        convert_to_unicode(message))
# #
            '''NOTE: The web server will handle this.'''
            raise

        return self

    def _run(self):
        '''Initializes the web server.'''
        RestResponse.web_node = Controller.web_node = self.__class__
        normalized_argument_string = ' '.join(sys.argv)
        self.__class__.debug = sys.flags.debug
        if not self.debug:
            match = True
            while match:
                for name in ('-l', '--log-level'):
                    for delimiter in (' ', '='):
                        '''
                            NOTE: ".*" have to be greedy to find last \
                            occurrence which should take effect.
                        '''
                        match = regularExpression.compile('.*%s%s([a-z-]+)' % (
                            name, delimiter
                        )).match(normalized_argument_string)
                        if match:
                            self.__class__.debug = match.group(1) == 'debug'
                            '''
                                NOTE: We remove last found match to ensure \
                                that last given parameter takes effect.
                            '''
                            normalized_argument_string = \
                                normalized_argument_string[match.span()[1]:]
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
        command_line_arguments = self.options['commandLineArguments']
        if not builtins.isinstance(command_line_arguments, builtins.list):
            command_line_arguments = self.options['commandLineArguments'][
                '__no_wrapping__']
        self.__class__.given_command_line_arguments = \
            CommandLine.argument_parser(
                arguments=command_line_arguments, module_name=__name__)
        '''
            Register and wrapp method to profile if corresponding flags are \
            given.
        '''
        if(
            'coreBackendProfile' in self.given_command_line_arguments.flags or
            'coreBackendPrintProfile' in
            self.given_command_line_arguments.flags
        ):
            def profile_wrapper(function, description):
                def wrapped_function(*arguments, **keywords):
                    start = clock()
                    profiler = Profiler()
                    profiler.enable()
                    result = function(*arguments, **keywords)
                    profiler.disable()
                    if 'coreBackendPrintProfile' in \
                    self.given_command_line_arguments.flags:
                        __logger__.info(
                            'Elapsed time for running "%s": %.2f seconds',
                            function.__name__, clock() - start)
                        '''Sort by call count'''
                        profiler.print_stats(sort=0)
                        '''Sort by internal function time'''
                        profiler.print_stats(sort=1)
                        '''Sort by cumulative time'''
                        profiler.print_stats(sort=2)
                    if 'coreBackendProfile' in \
                    self.given_command_line_arguments.flags:
                        profiler.dump_stats('%s.profile' % description)
                    return result
                return wrapped_function
            for method_name, description in {
                '_prepare_application_startup': 'startUp',
                '_initialize': 'request'
            }.items():
                builtins.setattr(self.__class__, method_name, profile_wrapper(
                    builtins.getattr(self.__class__, method_name), description)
                )
        self._prepare_application_startup()
        if not self.given_command_line_arguments.reload:
            return self._start_web_server()

    # # # endregion

    def _prepare_application_startup(self):
        '''
            Prepares the application server after command line arguments are \
            parsed.
        '''
        if Controller is not None:
            self.__class__.controller = Controller()
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
        if not self.given_command_line_arguments.reload:
            self._register_authentication_handler()
        FileHandler(
            location=self.options['location']['reportedClientError']
        ).directory.make_directories()
        FileHandler(
            location=self.options['location']['proxyServerLog']
        ).directory.make_directories()
        self._initialize_templates()
        self._initialize_data_structure()
        return self

    def _handle_request_data(self):
        '''Consolidates posted data given by client.'''
        if builtins.isinstance(self.request['data'], builtins.list):
            for index, item in builtins.enumerate(self.request['data']):
                self.request['data'][index] = Dictionary(
                    content=item
                ).convert(value_wrapper=self.convert_for_backend).content
        else:
            if self.options['removeDuplicatedRequestKey']:
                for key, value in self.request['data'].items():
                    if builtins.isinstance(value, builtins.list):
                        if builtins.len(value) > 0:
                            self.request['data'][key] = value[0]
                        else:
                            self.request['data'][key] = None
            self.request['data'] = Dictionary(
                content=self.request['data']
            ).convert(value_wrapper=self.convert_for_backend).content
        return self

    def _initialize_templates(self):
        '''Determines templates files and renders them.'''
        self.__class__.frontend_html_file = FileHandler(
            location=self.options['location']['htmlFile']['frontend'])
        self.__class__.backend_html_file = FileHandler(
            location=self.options['location']['htmlFile']['backend'])
        self.__class__.html_template_file = FileHandler(
            location=self.options['location']['htmlFile']['template'])
        self.__class__.offline_manifest_template_file = FileHandler(
            location=self.options['location']['offlineManifestTemplateFile']
        )
        self.__class__.options['frontend'] = Dictionary(
            content=self.options['frontend']
        ).compatible_types.content
        if(
            'coreBackendNoTemplateRendering' not in \
            self.given_command_line_arguments.flags and
            self.options['initialTemplateRendering'] or
            self.given_command_line_arguments.reload
        ):
            __logger__.info('Render template files.')
            self.render_templates(all=True, initialize=True)
        return self

    def _register_authentication_handler(self):
        '''Registers a basic http authentication handler to webserver.'''
# # python3.5
# #         if self.controller is not None and builtins.isinstance(
# #             self.options['webServer'].get('authenticationHandler'),
# #             builtins.str
# #         ):
# #             self.options['webServer']['authenticationHandler'] = \
# #                 builtins.eval(
# #                     self.options['webServer']['authenticationHandler'], {
# #                         'controller': self.controller,
# #                         'Controller': Controller,
# #                         'RestController': RestResponse})
        if self.controller is not None and builtins.isinstance(
            self.options['webServer'].get('authenticationHandler'),
            (builtins.unicode, builtins.str)
        ):
            self.options['webServer']['authenticationHandler'] = \
                builtins.eval(
                    self.options['webServer']['authenticationHandler'], {
                        'controller': self.controller,
                        'Controller': Controller,
                        'RestController': RestResponse})
# #
        return self

    def _initialize_data_structure(self):
        '''Initializes database and file based caching layer.'''
        if self.options['location']['database'][
            'stateTypeReference'
        ] == '__memory__':
            class DateState:
                def __init__(self, name, timestamp, user_id):
                    self.timestamp = timestamp
                    self.user_id = user_id
        else:
            state_location = FileHandler(
                location=self.options['location']['database'][
                    'stateTypeReference'])
            state_location.make_directories()
            class DateState(Class):
                file = None

                def __init__(self, name, timestamp, user_id):
                    self.file = FileHandler(location='%s%s' % (
                        state_location.path, name))
                    self.file.content = user_id
                    self.file.timestamp = timestamp

                def get_timestamp(self):
                    return self.file.timestamp

                def get_user_id(self):
                    return builtins.int(self.file.content)
        class DataState:
            def __init__(self, timestamp=0, user_id=1):
                self.states = {'Data': DateState(
                    name='Data', timestamp=timestamp, user_id=user_id)}

            def __iter__(self):
# # python3.5
# #                 yield from self.states.items()
                for key, value in self.states.items():
                    yield key, value
# #

            def update(self, model_name='Data', user_id=1):
                now = DateTime.now()
# # python3.5
# #                 timestamp = now.timestamp(
# #                 ) + builtins.float(now.microsecond) / 1000 ** 2
                timestamp = make_time(now.timetuple(
                )) + now.microsecond / 1000 ** 2
# #
                if model_name == 'Data':
                    for model_name, date_state in self:
                        self.states[model_name] = DateState(
                            name=model_name, timestamp=timestamp,
                            user_id=user_id)
                else:
                    self.states[model_name] = DateState(
                        name=model_name, timestamp=timestamp, user_id=user_id)
                    self.states['Data'] = DateState(
                        name='Data', timestamp=timestamp, user_id=user_id)
        self.__class__.state = DataState()
        '''Initialize cache timestamps for all models.'''
        for model_name, model in builtins.filter(
            lambda model: builtins.isinstance(
                model[1], builtins.type
            ) and builtins.issubclass(model[1], self.model.Model),
            Module.get_defined_objects(self.model)
        ):
            self.state.update(model_name)
        self.state.update(model_name='File')
        if self.debug:
            self.clear_web_cache()
        if self.controller is not None:
            self.controller.launch()
        if self.given_command_line_arguments.dead_file_reference_check:
            self._check_database_file_references()
        # TODO default is empty here (which is right) but it should be
        # "templateName" as specified in options.json
        if self.given_command_line_arguments.\
        dead_soft_reference_check_properties:
            self._check_dead_soft_references()
        return self

    def _determine_suitable_proxy_server(self):
        '''Search for suitable proxy server.'''
        connection = HTTPConnection(
            self.given_command_line_arguments.host_name,
            self.given_command_line_arguments.proxy_ports[0])
        try:
            connection.request('HEAD', '')
        except (socket.herror, socket.gaierror, socket.timeout, socket.error):
            pass
        else:
            try:
                server_name = builtins.dict(
                    connection.getresponse().getheaders()
                ).get('server')
            except (
                socket.herror, socket.gaierror, socket.timeout, socket.error
            ):
                pass
            else:
                for pattern in self.SUPPORTED_PROXY_SERVER_NAME_PATTERN:
# # python3.5
# #                     if regularExpression.compile(pattern).fullmatch(
# #                         server_name
# #                     ):
                    if regularExpression.compile('(?:%s)$' % pattern).match(
                        server_name
                    ):
# #
                        self.__class__.port = self.__class__.proxy_port = \
                            self.given_command_line_arguments.proxy_ports[0]
                        self.__class__.options['frontend']['proxy']['port'] = \
                            self.proxy_port
                        __logger__.info(
                            'Detected proxy server "%s" at "%s" listing on '
                            'incoming requests which matches pattern "%s" on '
                            'port %d.', server_name,
                            self.given_command_line_arguments.host_name,
                            self.given_command_line_arguments.
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
