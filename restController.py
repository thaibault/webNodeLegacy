#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# region header

'''Provides a generic Response object for any web based web application.'''

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
from base64 import b64encode as base64_encode
from copy import copy
from datetime import datetime as DateTime
import inspect
import json
import os
import shutil
import time

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker as create_database_session
from sqlalchemy.orm import load_only as select_database_records

# # python3.5 pass
from boostNode import convert_to_string, convert_to_unicode
from boostNode.extension.file import Handler as FileHandler
from boostNode.extension.native import Object, Iterable, Dictionary, Module, \
    InstancePropertyInitializer
from boostNode.extension.native import String
from boostNode.paradigm.objectOrientation import Class
from boostNode.runnable.template import Parser as TemplateParser

# endregion

# region decorator functions

def cachable(function):
    '''Sets the cache indicator to given rest api function.'''
    function.__cachable_via_rest_api__ = True
    return function

# endregion


# region classes

class Response(Class):

    '''Handles rest api requests.'''

    # region static methods

    # # region public

    @classmethod
    @cachable
    def get_file_model(cls, data):
        '''Returns all files in given location.'''
        result = []
        requested_file = FileHandler(
            location=data['location'] if 'location' in data else '/')
        if requested_file.is_directory():
            def list_directory(directory):
                '''List given directory in a flat list.'''
                for file in directory:
                    if data.get('recursive') and file.is_directory():
                        list_directory(directory=file)
                    else:
                        file_attributes = cls._generate_file_attributes(
                            file, requested_file, directory,
                            filter_criteria=data,
                            content=data.get('content', False),
                            convert_escape_sequences_to_html=data.get(
                                'convert_escape_sequences_to_html', False
                            ), offset=data.get('offset', 0),
                            limit=data.get('limit', -1),
                            whence=data.get('whence', 0))
                        if file_attributes:
                            result.append(file_attributes)
            list_directory(directory=requested_file)
        elif requested_file.is_file():
            file_attributes = cls._generate_file_attributes(
                file=requested_file, content=data.get('content', False),
                convert_escape_sequences_to_html=data.get(
                    'convert_escape_sequences_to_html', False
                ), offset=data.get('offset', 0), limit=data.get('limit', -1),
                whence=data.get('whence', 0))
            if file_attributes:
                result.append(file_attributes)
        return result

    # # endregion

    # # region protected

    @classmethod
    def _generate_file_attributes(
        cls, file, requested_file=None, directory=None, filter_criteria={},
        content=False, convert_escape_sequences_to_html=False, offset=0,
        limit=-1, whence=0
    ):
        '''
            Generates transferable file attributes for given file if it \
            matches given filter criteria.
        '''
        ignored = False
        if Iterable(
            cls.web_node.options['web_asset_pattern_ignore']
        ).is_in_pattern(value=file.name):
            ignored = True
        if ignored:
            return True
        file_attributes = {}
        skip = False
        attributes = FileHandler.EXPORTABLE_ATTRIBUTES + (
            ('content',) if content else ())
        if file.is_file():
            attributes += FileHandler.EXPORTABLE_FILE_ATTRIBUTES
        for name in attributes:
            if name == 'hash':
                if file.is_file():
                    value = file.get_hash(algorithm=cls.web_node.options[
                        'file_hash_algorithm'])
                    name = cls.web_node.options['file_hash_algorithm']
                else:
                    continue
            elif name == 'content':
                if file.is_file():
                    value = file.get_content(
                        offset=offset, limit=limit, whence=whence)
                else:
                    continue
            else:
                value = builtins.getattr(file, name)
                if name == 'encoding':
                    value = value.replace('_', '-')
            name_camel_case = String(name).delimited_to_camel_case.content
            if(name_camel_case not in filter_criteria or
               value == filter_criteria[name_camel_case]):
                file_attributes[name_camel_case] = value
            else:
                skip = True
                break
        if skip:
            return False
        if None not in (requested_file, directory):
            file_attributes['recursiveBasenamePath'] = \
            directory.path[builtins.len(requested_file.path):] + file.basename
        if content and convert_escape_sequences_to_html:
            file_attributes['content'] = String(
                file_attributes['content']
            ).escape_sequences_to_html.content
        return file_attributes

    # #  endregion

    # endregion

    # region public methods

    # # region special

    @InstancePropertyInitializer
    def __init__(self, web_node, mime_type, cache_control_header):
        '''Retrieves request meta data.'''
        '''Saves current selected model.'''
        self.model = None
        self.cache_key = None
        self.method_in_rest_controller = True
        if('__method__' in self.web_node.request['get'] and
           self.web_node.request['get']['__method__'] in (
               'get', 'put', 'post', 'patch', 'delete', 'head', 'jsonp')):
            self.web_node.request['type'] = self.web_node.request['get'][
                '__method__']
            del self.web_node.request['get']['__method__']
        self.allow_cache = True
        if '__cache__' in self.web_node.request['get']:
            self.allow_cache = self.web_node.request['get']['__cache__']
            del self.web_node.request['get']['__cache__']
        self.json_padding = ''
        for jsonp_get_parameter_indicator in \
        self.web_node.options['jsonp_get_parameter_indicator']:
            if jsonp_get_parameter_indicator in self.web_node.request['get']:
                self.json_padding = self.web_node.request['get'][
                    jsonp_get_parameter_indicator]
                del self.web_node.request['get'][jsonp_get_parameter_indicator]
        if self.web_node.request['type'] != 'head':
            self._determine_model()
            '''
                Converter keywords to wrap each respond to client. Can be \
                overridden in subclasses.
            '''
# # python3.5
# #             self.data_wrapper = {
# #                 'key_wrapper': lambda key, value:
# #                     self.web_node.convert_for_client(String(
# #                         key
# #                     ).delimited_to_camel_case.content if \
# #                         builtins.isinstance(
# #                             key, builtins.str
# #                         ) else key),
# #                 'value_wrapper': self.web_node.convert_for_client}
            self.data_wrapper = {
                'key_wrapper': lambda key, value:
                    self.web_node.convert_for_client(String(
                        key
                    ).delimited_to_camel_case.content if \
                        builtins.isinstance(key, (
                            builtins.unicode, builtins.str
                        )) else key),
                'value_wrapper': self.web_node.convert_for_client}
# #
        if self.model is not None:
            del self.web_node.request['get']['__model__']

        # endregion

    # # region helper

    def finalize_database_session(
        self, session, model_name='Data', flat=False
    ):
        '''
            Commits all changes on given database session, sets last database \
            change timestamp, handles errors and closes connection.
        '''
        try:
            session.commit()
        except(SQLAlchemyError, builtins.ValueError) as exception:
            self.handle_database_exception(exception, session)
        session.close()
        if model_name:
            self.web_node.remove_model_cache(
                model_name, flat, user_id=self.web_node.authorized_user_id)
        return self

    def handle_database_exception(self, exception, session):
        '''
            Deals with unexpected database behavior. NOTE: We can't raise \
            this exception because frontend need it as validation message.
        '''
        session.rollback()
# # python3.5
# #         self.web_node.request['handler'].send_response(
# #             400 if builtins.isinstance(
# #                 exception, builtins.ValueError
# #             ) else 409, '%s: "%s"' % (
# #                 exception.__class__.__name__, builtins.str(exception)))
        self.web_node.request['handler'].send_response(
            400 if builtins.isinstance(
                exception, builtins.ValueError
            ) else 409, '%s: "%s"' % (
                exception.__class__.__name__,
                convert_to_unicode(exception)))
# #
        return self

    def process_output(self, output, cache_file=None):
        '''
            Validates given output and handles padded response and generic \
            caching.
        '''
        if output is None:
            if self.json_padding:
                output = '%s({});' % self.json_padding
            else:
                output = self.web_node.options['rest_response_template'] % '{}'
        else:
            output = json.dumps(
                output, skipkeys=True, ensure_ascii=False, check_circular=True,
                allow_nan=True, separators=(',', ':'), sort_keys=True,
                default=lambda object: '__not_serializable__')
            if self.json_padding:
                output = '%s(%s);' % (self.json_padding, output)
            else:
                output = self.web_node.options['rest_response_template'] % \
                    output
            if(self.web_node.given_command_line_arguments.web_cache and not (
                self.model is None or cache_file is None
            ) and self.web_node.request['type'] == 'get'):
                cache_file.directory.make_directories()
                cache_file.content = output
        return output, self.mime_type, self.cache_control_header, cache_file

    # # endregion

    # # region getter

    @Class.pseudo_property
    def get_output(self):
        '''Computes the json response object.'''
        cache_file = None
        if(self.web_node.given_command_line_arguments.web_cache and
           self.allow_cache and self.web_node.request['type'] == 'get' and
           self.cache_key is not None):
            cache_file = FileHandler(location='%s/%d-%s.json' % (
                self.web_node.options['location']['web_cache'],
                0 if self.web_node.authorized_user_id is None or \
                not self.web_node.request['handler'].headers.get(
                    'Admin', False
                ) or not self.web_node.options['model'].get(
                    self.model.__name__[0].lower() + self.model.__name__[1:],
                    {}
                ).get('__needs_authentication__', False) else 1,
                self.web_node.request['external_uri'].replace(os.sep, '')
            ))
        result = None
        if cache_file:
            __logger__.info(
                'Response rest api cache from "%s".', cache_file.path)
        else:
            if self.web_node.request['type'] != 'head':
                if self.model is None:
                    self.web_node.request['handler'].send_response(
                        510, 'Requested model request isn\'t valid or model '
                        '"%s" doesn\'t exist.' %
                            self.web_node.request['get']['__model__'])
                else:
                    result = self._handle_data_exchange()
            self.web_node.request['handler'].send_response(200)
            for model_name, date_state in self.web_node.state:
                key = String(self.web_node.options[
                    'last_data_write_header_name'
                ]).get_camel_case_to_delimited(delimiter='-').substitute(
                    '-([a-z])',
                    lambda match: '-%s' % match.group(1).upper()
                ).camel_case_capitalize.content.replace('Data', model_name)
                self.web_node.request['handler'].send_header(key, '%d-%d' % (
                    date_state.timestamp, date_state.user_id))
        return self.process_output(output=result, cache_file=cache_file)

    # # endregion

    # # region request type

    def process_patch(self, get, data, flat):
        '''Computes the patch response object.'''
        get = self._filter_special_keys(get)
        data = self._filter_special_keys(data)
        session = create_database_session(bind=self.web_node.engine)()
        try:
            updated_models = session.query(self.model).filter_by(**get)
            updated_models.update(self.model(**data).get_dictionary(
                prefix_filter=()))
        except(SQLAlchemyError, builtins.ValueError) as exception:
            self.handle_database_exception(exception, session)
            updated_models = None
        self.finalize_database_session(
            session, model_name=self.model.__name__, flat=flat)
        return self._determine_primary_keys(models=updated_models)

    def process_post(self, get, data, flat):
        '''Computes the post response object.'''
        if self.web_node.model.User is self.model:
            get = self._filter_special_keys(get)
            data = self._filter_special_keys(data)
            result = None
            if 'has_password' in data:
                value = data['has_password']
                del data['has_password']
                session = create_database_session(bind=self.web_node.engine)()
                try:
                    users = session.query(self.model).filter_by(**data)
                except(SQLAlchemyError, builtins.ValueError) as exception:
                    self.handle_database_exception(exception, session)
                user = users.one() if users.count() else None
                if user is not None and user.enabled and user.has_password(
                    value
                ):
                    '''Save session token in database with expiration time.'''
# # python3.5
# #                     user.session_token = base64_encode(os.urandom(
# #                         self.web_node.options['model']['authentication'][
# #                             'session_token'
# #                         ]['length']
# #                     )).decode().strip()
                    user.session_token = convert_to_unicode(base64_encode(
                        os.urandom(self.web_node.options['model'][
                            'authentication'
                        ]['session_token']['length'])
                    ).strip())
# #
                    user.session_expiration_date_time = DateTime.now(
                    ) + self.web_node.options['session'][
                        'expiration_time_delta']
                    '''
                        NOTE: Model data has to be rendered before session is \
                        committed, to avoid temporary lose data.
                    '''
                    result = user.get_dictionary(
                        prefix_filter=('password',), **self.data_wrapper)
                    self.finalize_database_session(
                        session, model_name=self.model.__name__, flat=flat)
            elif(self.web_node.authorized_user_id is not None and data.get(
                'id'
            ) == self.web_node.authorized_user_id):
                session = create_database_session(bind=self.web_node.engine)()
                try:
                    users = session.query(self.model).filter_by(
                        id=self.web_node.authorized_user_id)
                except(SQLAlchemyError, builtins.ValueError) as exception:
                    self.handle_database_exception(exception, session)
                if users.count():
                    result = users.one().get_dictionary(
                        prefix_filter=('password',), **self.data_wrapper)
                session.close()
            return result

    def process_put(self, get, data, flat):
        '''Computes the put response object.'''
        session = create_database_session(
            bind=self.web_node.engine, expire_on_commit=False
        )()
        get = self._filter_special_keys(get)
        if builtins.isinstance(data, builtins.list):
            result = []
            for item in data:
                '''
                    Determine additional primary key parts of the data object.
                '''
                new_get = copy(get)
                for primary_key in builtins.filter(
                    lambda key: key.name not in get and key.name in item,
                    self.model.__mapper__.primary_key
                ):
                    new_get[primary_key.name] = item[primary_key.name]
                try:
                    updated_models = session.query(self.model).filter_by(
                        **new_get)
                except(SQLAlchemyError, builtins.ValueError) as exception:
                    self.handle_database_exception(exception, session)
                    updated_models = None
                else:
                    if new_get and updated_models.count():
                        try:
                            updated_models.update(self.model(
                                **item
                            ).get_dictionary(prefix_filter=()))
                        except(
                            SQLAlchemyError, builtins.ValueError
                        ) as exception:
                            self.handle_database_exception(exception, session)
                    else:
                        new_get.update(item)
                        new_model = self.model(**new_get)
                        try:
                            session.add(new_model)
                            '''
                                NOTE: "finalize_database_session()" commits \
                                our changes but we have to commit immediately \
                                to get a unique primary key.
                            '''
                            session.commit()
                        except(
                            SQLAlchemyError, builtins.ValueError
                        ) as exception:
                            self.handle_database_exception(exception, session)
                        updated_models = [new_model]
                result += self._determine_primary_keys(models=updated_models)
        else:
            data = self._filter_special_keys(data)
            try:
                updated_models = session.query(self.model).filter_by(**get)
            except(SQLAlchemyError, builtins.ValueError) as exception:
                self.handle_database_exception(exception, session)
                updated_models = None
            else:
                if get and updated_models.count():
                    try:
                        updated_models.update(self.model(
                            **data
                        ).get_dictionary(prefix_filter=()))
                    except(SQLAlchemyError, builtins.ValueError) as exception:
                        self.handle_database_exception(exception, session)
                else:
                    get.update(data)
                    new_model = self.model(**get)
                    try:
                        session.add(new_model)
                        '''
                            NOTE: "finalize_database_session()" commits our \
                            changes but we have to commit immediately to get \
                            a unique primary key.
                        '''
                        session.commit()
                    except(SQLAlchemyError, builtins.ValueError) as exception:
                        self.handle_database_exception(exception, session)
                    else:
                        updated_models = [new_model]
            result = self._determine_primary_keys(models=updated_models)
        self.finalize_database_session(
            session, model_name=self.model.__name__, flat=flat)
        return result

    def process_delete(self, get, data, flat):
        '''Computes the delete response object.'''
        session = create_database_session(bind=self.web_node.engine)()
        result = []
        modified = False
        get = self._filter_special_keys(get)
        if builtins.isinstance(data, builtins.list):
            result, modified = self._delete_list(session, get, data)
        elif get and session.query(self.model).filter_by(**get).count():
            data = self._filter_special_keys(data)
            try:
                updated_models = session.query(self.model).filter_by(**get)
            except(SQLAlchemyError, builtins.ValueError) as exception:
                self.handle_database_exception(exception, session)
            else:
                if get and updated_models.count():
                    result += self._determine_primary_keys(
                        models=updated_models)
                    updated_models.delete()
                    modified = True
        if modified:
            self.finalize_database_session(
                session, model_name=self.model.__name__, flat=flat)
        else:
            session.close()
        return result

    def process_get(self, data):
        '''Computes the get response object.'''
        authenticated, prefix_filter = \
            self._determine_authentication_parameter()
        if not authenticated:
            return
        return self._evaluate_get(data, prefix_filter)

    # # endregion

    # # region special request types

    def get_system_model(self, data):
        '''Returns all defined models.'''
        return {
            'freeSpaceInByte': FileHandler(location='/').free_space,
            'usedSpaceInByte': FileHandler(location='/').disk_used_space}

    @cachable
    def get_available_model(self, data):
        '''Returns all defined models.'''
        return builtins.list(builtins.map(
            lambda model: model[0], Module.get_defined_objects(self.model)))

    @cachable
    def delete_file_model(self, get, data, flat):
        '''Removes given file.'''
        file = FileHandler(location=get['path'])
        if file.is_file():
            if file.remove_file():
                self.web_node.remove_model_cache(
                    model_name='File', flat=flat,
                    user_id=self.web_node.authorized_user_id)
                return [{'path': file.path}]
            return None
        return []

    @cachable
    def put_file_model(self, get, data, flat):
        '''Saves given files.'''
        modified = False
        result = []
        for items in data.values():
            for item in items:
                if builtins.hasattr(
                    item, 'file'
                ) and item.filename and item.done != -1:
                    new_file = FileHandler(
                        self.web_node.options['location']['medium'] +
                        convert_to_unicode(item.filename))
                    result.append({'path': new_file.path})
                    shutil.copyfileobj(item.file, builtins.open(
                        convert_to_string(new_file._path), 'wb'))
                    modified = True
        if modified:
            self.web_node.remove_model_cache(
                model_name='File', flat=flat,
                user_id=self.web_node.authorized_user_id)
        return result

    def put_copy_model(self, get, data, flat):
        '''Copies give model references.'''
        keys = copy(get)
        del keys['source']
        keys = Dictionary(keys).convert(
            key_wrapper=lambda key, value: '%s_%s' % (
                get['source'].lower(), key)
        ).content
        '''
            Prepare a pattern for newly created linked records with \
            corresponding linked attribute names and values.
        '''
        data = Dictionary(data).convert(
            key_wrapper=lambda key, value: '%s_%s' % (get['source'].lower(
            ), key)
        ).content
        session = create_database_session(
            bind=self.web_node.engine, expire_on_commit=False
        )()
        modified = False
        for model_name, model in builtins.filter(
            lambda model: inspect.isclass(model[1]) and builtins.issubclass(
                model[1], self.web_node.model.Model
            ), Module.get_defined_objects(self.web_node.model)
        ):
            column_names = builtins.list(builtins.map(
                lambda property: property.name, model.__table__.columns))
            is_referenced = True
            for key_name in builtins.filter(
                lambda key_name: key_name not in column_names, keys
            ):
                is_referenced = False
                break
            if is_referenced:
                '''
                    NOTE: Property names have to be determined once. Because \
                    sometimes the result is empty due to an internal caching \
                    bug. Additionally this workaround brings a little \
                    performance improvement.
                '''
                property_names = []
                '''Filter unique identifiers for record copies.'''
                for column in builtins.filter(
                    lambda column: column.name != 'id', model.__table__.columns
                ):
                    property_names.append(column.name)
                for record in session.query(model).filter_by(**keys):
                    session.add(model(**record.get_dictionary(
                        value_wrapper=lambda key, value:
                            data[key] if key in data else value,
                            property_names=property_names)))
                    modified = True
                    session.commit()
        if modified:
            self.finalize_database_session(session, flat=flat)
        else:
            session.close()
        return {}

    # # endregion

    # endregion

    # region protected methods

    def _filter_special_keys(self, get):
        '''Filers special keys from given get dictionary.'''
        return builtins.dict(builtins.filter(
            lambda item: not item[0].startswith('_'), get.items()))

    def _delete_list(self, session, get, data):
        '''Deletes a list of items determined by given request informations.'''
        result = []
        modified = False
        for item in data:
            '''Determine additional primary key parts of the data object.'''
            new_get = copy(get)
            for primary_key in builtins.filter(
                lambda key: key.name not in get and key.name in item,
                self.model.__mapper__.primary_key
            ):
                new_get[primary_key.name] = item[primary_key.name]
            try:
                updated_models = session.query(self.model).filter_by(**new_get)
            except(SQLAlchemyError, builtins.ValueError) as exception:
                self.handle_database_exception(exception, session)
            else:
                if new_get and updated_models.count():
                    result += self._determine_primary_keys(
                        models=updated_models)
                    try:
                        updated_models.delete()
                    except(SQLAlchemyError, builtins.ValueError) as exception:
                        self.handle_database_exception(exception, session)
                        result = result[:-1]
                    else:
                        modified = True
        return result, modified

    def _evaluate_get(self, data, prefix_filter=()):
        '''Evaluates a get from database request.'''
        session = create_database_session(bind=self.web_node.engine)()
        if data:
            if '__select__' in data:
                result = self._evaluate_select(data, prefix_filter, session)
            else:
                try:
                    result = builtins.list([model.get_dictionary(
                        prefix_filter=prefix_filter, **self.data_wrapper
                    ) for model in session.query(self.model).filter_by(
                        **self._filter_special_keys(data))])
                except(SQLAlchemyError, builtins.ValueError) as exception:
                    self.handle_database_exception(exception, session)
                    result = None
        else:
            try:
                result = builtins.list([model.get_dictionary(
                    prefix_filter=prefix_filter, **self.data_wrapper
                ) for model in session.query(self.model)])
            except(SQLAlchemyError, builtins.ValueError) as exception:
                self.handle_database_exception(exception, session)
                result = None
        session.close()
        return result

    def _evaluate_select(self, data, prefix_filter, session):
        '''Evaluates a reading data request with included select expression.'''
        select = [self.model.__mapper__.primary_key[0].name]
        for property_name in builtins.filter(
            lambda name: name, data.pop('__select__').split(',')
        ):
            property_name = String(
                property_name
            ).camel_case_to_delimited.content
            filtered = False
            for prefix in builtins.filter(
                lambda prefix: property_name.startswith(prefix), prefix_filter
            ):
                filtered = True
                break
            if not filtered:
                select.append(property_name)
        try:
            return builtins.list([model.get_dictionary(
                prefix_filter=prefix_filter, **self.data_wrapper
            ) for model in session.query(self.model).options(
                select_database_records(*select))])
        except(SQLAlchemyError, builtins.ValueError) as exception:
            self.handle_database_exception(exception, session)

    def _determine_primary_keys(self, models):
        '''
            Determines a list of dictionaries which only contains primary \
            keys.
        '''
        result = []
        if models:
            for model in models:
                keys = {}
                for primary_key in self.model.__mapper__.primary_key:
                    keys[String(
                        primary_key.name
                    ).delimited_to_camel_case.content] = builtins.getattr(
                        model, primary_key.name)
                result.append(keys)
        return result

    def _determine_authentication_parameter(self):
        '''
            Determines which data can be retrieved with given authentication \
            level. Returns a tuple. First element tells if request should be \
            rejected and second argument gives a needed data prefix filter.
        '''
        default_prefix_filter = 'password', 'session', 'login', 'user'
        if self.web_node.authorized_user_id is None:
            if(
                self.web_node.request['type'] != 'post' and
                inspect.isclass(self.model) and
                builtins.issubclass(self.model, self.web_node.model.Model) and
                builtins.issubclass(
                    self.model, self.web_node.model.AuthenticationModel)
            ):
                return False, default_prefix_filter
            return True, default_prefix_filter
        if inspect.isclass(self.model) and builtins.issubclass(
            self.model, self.web_node.model.Model
        ) and builtins.issubclass(
            self.model, self.web_node.model.AuthenticationModel
        ):
            return True, default_prefix_filter[:1]
        return True, ()

    def _handle_data_exchange(self):
        '''
            Handles each get and data requests and performs needed actions on \
            database.
        '''
        result = None
        if self._determine_authentication_parameter()[0]:
            flat = self.web_node.request['get'].get('__flat__', False)
            if builtins.hasattr(self.model, '__table__'):
                method = builtins.getattr(
                    self, 'process_%s' % self.web_node.request['type'])
                if self.web_node.request['type'] == 'get':
                    result = method(data=self.web_node.request['get'])
                else:
                    result = method(
                        get=self.web_node.request['get'],
                        data=self.web_node.request['data'], flat=flat)
            elif self.web_node.request['type'] == 'get':
                if self.method_in_rest_controller:
                    result = self.model(data=self.web_node.request['get'])
                else:
                    result = self.model(
                        data=self.web_node.request['get'],
                        rest_controller=self)
            elif self.method_in_rest_controller:
                result = self.model(
                    get=self.web_node.request['get'],
                    data=self.web_node.request['data'], flat=flat)
            else:
                result = self.model(
                    get=self.web_node.request['get'],
                    data=self.web_node.request['data'], rest_controller=self,
                    flat=flat)
        if result is None:
            self.web_node.request['handler'].send_response(401)
        return result

    def _determine_model(self):
        '''Determines requested model from client.'''
        if self.web_node.request['get']['__model__'] not in (
            self.web_node.model.Model.__name__, 'Model'
        ) and builtins.hasattr(
            self.web_node.model, self.web_node.request['get']['__model__']
        ):
            model = builtins.getattr(
                self.web_node.model, self.web_node.request['get']['__model__'])
            if builtins.issubclass(model, self.web_node.model.Model):
                self.cache_key = self.web_node.request['get']['__model__']
                self.model = model
        if self.model is None:
            method_name = '%s_%s_model' % (
                self.web_node.request['type'], String(
                    self.web_node.request['get']['__model__']
                ).camel_case_to_delimited.content)
            if builtins.hasattr(self, method_name):
                self.model = builtins.getattr(self, method_name)
            elif builtins.hasattr(self.web_node.controller, method_name):
                self.method_in_rest_controller = False
                self.model = builtins.getattr(
                    self.web_node.controller, method_name)
            if builtins.hasattr(self.model, '__cachable_via_rest_api__'):
                self.cache_key = self.web_node.request['get']['__model__']
        return self

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

# region vim modline

# vim: set tabstop=4 shiftwidth=4 expandtab:
# vim: foldmethod=marker foldmarker=region,endregion:

# endregion
