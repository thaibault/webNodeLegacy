#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# region header

'''Provides a generic Response object for any web based web application.'''

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
from base64 import b64encode as base64_encode
from copy import copy
from datetime import datetime as DateTime
import inspect
import json
import os
import re
import shutil
import time

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker as create_database_session

# # python3.4 pass
from boostNode import ENCODING, convert_to_unicode
from boostNode.extension.file import Handler as FileHandler
from boostNode.extension.native import Dictionary, Module, \
    InstancePropertyInitializer, String
from boostNode.paradigm.objectOrientation import Class

# endregion


# region classes

class Response(Class):

    '''Handles rest api requests.'''

    # region public methods

    # # region special

    @InstancePropertyInitializer
    def __init__(self, request):
        '''Retrieves request meta data.'''

        # # region properties

        '''Saves current selected model.'''
        self.model = None
        self.method_in_rest_controller = True
        if('__method__' in self.request.data['get'] and
           self.request.data['get']['__method__'] in (
               'get', 'put', 'post', 'patch', 'delete', 'head', 'jsonp')):
            self.request.data['request_type'] = self.request.data['get'][
                '__method__']
            del self.request.data['get']['__method__']
        self.json_padding = ''
        for jsonp_get_parameter_indicator in \
        self.request.options['jsonp_get_parameter_indicator']:
            if jsonp_get_parameter_indicator in self.request.data['get']:
                self.json_padding = self.request.data['get'][
                    jsonp_get_parameter_indicator]
                del self.request.data['get'][jsonp_get_parameter_indicator]
        if self.request.data['request_type'] != 'head':
            if self.request.data['get'][
                '__model__'
            ] != self.request.model.Model.__name__ and builtins.hasattr(
                self.request.model, self.request.data['get']['__model__']
            ):
                model = builtins.getattr(
                    self.request.model, self.request.data['get']['__model__'])
                if builtins.issubclass(model, self.request.model.Model):
                    self.model = model
            if self.model is None:
# # python3.4
# #                 method_name = '%s_%s_model' % (
# #                     self.request.data['request_type'], String(
# #                         self.request.data['get']['__model__']
# #                     ).get_camel_case_to_delimited().content)
                method_name = '%s_%s_model' % (
                    self.request.data['request_type'], builtins.unicode(
                        String(
                            self.request.data['get']['__model__']
                        ).get_camel_case_to_delimited().content,
                    ENCODING))
# #
                if builtins.hasattr(self, method_name):
                    self.model = builtins.getattr(self, method_name)
                elif builtins.hasattr(self.request.controller, method_name):
                    self.method_in_rest_controller = False
                    self.model = builtins.getattr(
                        self.request.controller, method_name)
            '''
                A mapping to wrap each respond to client. Can be overridden \
                in subclasses.
            '''
            self.data_wrapper = self.request.frontend_data_wrapper

        # # endregion

        if self.model is not None:
            del self.request.data['get']['__model__']

        # endregion

        # region getter

    @Class.pseudo_property
    def get_output(self):
        '''Computes the json response object.'''
        result = None
        if self.request.data['request_type'] != 'head':
            if self.model is None:
                self.request.data['handler'].send_response(
                    510, 'Requested model "%s" doesn\'t exist.' %
                    self.request.data['get']['__model__'])
            else:
                self.session = create_database_session(
                    bind=self.request.engine, expire_on_commit=False,
                    autoflush=False
                )()
                if not self.model.__name__.endswith('_file_model'):
                    for dataType in ('get', 'data'):
                        if builtins.isinstance(
                            self.request.data[dataType], builtins.list
                        ):
                            for index, item in builtins.enumerate(
                                self.request.data[dataType]
                            ):
                                self.request.data[dataType][index] = \
                                    self.request.controller\
                                    .convert_for_database(item)
                        else:
                            self.request.data[dataType] = \
                                self.request.controller.convert_for_database(
                                    self.request.data[dataType])
                if builtins.hasattr(self.model, '__table__'):
                    method = builtins.getattr(
                        self, 'process_%s' % self.request.data['request_type'])
                    try:
                        if self.request.data['request_type'] == 'get':
                            result = method(data=self.request.data['get'])
                        else:
                            result = method(
                                get=self.request.data['get'],
                                data=self.request.data['data'])
                    except (SQLAlchemyError, builtins.ValueError) as exception:
                        self.session.rollback()
                        self.request.data['handler'].send_response(
                            400 if builtins.isinstance(
                                exception, builtins.ValueError
                            ) else 409, '%s: "%s"' % (
                                exception.__class__.__name__,
                                convert_to_unicode(exception)))
                        result = {}
                        if self.request.debug:
                            raise
                elif self.request.data['request_type'] == 'get':
                    if self.method_in_rest_controller:
                        result = self.model(data=self.request.data['get'])
                    else:
                        result = self.model(
                            data=self.request.data['get'],
                            rest_controller=self)
                elif self.method_in_rest_controller:
                    result = self.model(
                        get=self.request.data['get'],
                        data=self.request.data['data'])
                else:
                    result = self.model(
                        get=self.request.data['get'],
                        data=self.request.data['data'], rest_controller=self)
                if result is None:
                    self.request.data['handler'].send_response(401)
                    result = {}
                self.session.commit()
                self.session.close()
        self.request.data['handler'].send_response(200)
# # python3.4
# #         self.request.data['handler'].send_header(
# #             String(self.request.options[
# #                 'last_data_write_date_time_header_name'
# #             ]).get_camel_case_to_delimited(delimiter='-').sub(
# #                 '-([a-z])', lambda match: '-%s' % match.group(1).upper()
# #             ).get_camel_case_capitalize().content, builtins.str(
# #                 self.request.rest_data_timestamp_reference_file.timestamp))
        self.request.data['handler'].send_header(
            builtins.unicode(String(self.request.options[
                'last_data_write_date_time_header_name'
            ]).get_camel_case_to_delimited(delimiter='-').sub(
                '-([a-z])', lambda match: '-%s' % match.group(1).upper()
            ).get_camel_case_capitalize().content, ENCODING),
            convert_to_unicode(
                self.request.rest_data_timestamp_reference_file.timestamp))
# #
        if result is not None:
            if self.json_padding:
                return '%s(%s);' % (self.json_padding, result)
            return self.request.options['rest_response_template'] % json.dumps(
                result)
        return ''

        # endregion

        # region request type

    def process_patch(self, get, data):
        '''Computes the patch response object.'''
# # python3.4
# #         self.session.query(self.model).filter_by(
# #             **get
# #         ).update(self.model(**data).get_dictionary(prefix_filter=''))
        self.session.query(self.model).filter_by(
            **get
        ).update(self.model(**data).get_dictionary(prefix_filter=''))
# #
        self.request.rest_data_timestamp_reference_file.set_timestamp()
        return{}

    def process_post(self, get, data):
        '''Computes the post response object.'''
        if self.request.model.User is self.model:
            if 'has_password' in data:
                value = data['has_password']
                del data['has_password']
                users = self.session.query(self.model).filter_by(
                    **data)
                if users.count():
                    user = users.one()
                    if user.enabled and user.has_password(value):
                        '''
                            Save session token in database with expiration \
                            time.
                        '''
# # python3.4
# #                         user.session_token = base64_encode(os.urandom(
# #                             self.request.options['model'][
# #                                 'authentication'
# #                             ]['session_token']['length']
# #                         )).decode().strip()
                        session_token = base64_encode(os.urandom(
                            self.request.options['model'][
                                'authentication'
                            ]['session_token']['length']
                        )).strip()
                        if self.request.options[
                            'database_engine_prefix'
                        ].startswith('sqlite:'):
                            session_token = convert_to_unicode(
                                session_token,
                                self.request.options['encoding'])
                        user.session_token = session_token
# #
                        user.session_expiration_date_time = DateTime.now(
                        ) + self.request.options['session'][
                            'expiration_interval']
                        '''
                            NOTE: Model data has to be rendered before \
                            session is committed, to avoid temporary lose \
                            data.
                        '''
                        result = user.get_dictionary(**self.data_wrapper)
                        return result
            elif(self.request.authorized_user is not None and
                 data.get('id') == self.request.authorized_user.id):
                return self.request.authorized_user.get_dictionary(
                    **self.data_wrapper)

    def process_put(self, get, data):
        '''Computes the put response object.'''
        if builtins.isinstance(data, builtins.list):
            for item in data:
                '''
                    Determine additional primary key parts of the data object.
                '''
                new_get = copy(get)
                for primary_key in self.model.__mapper__.primary_key:
                    if(primary_key.name not in get and
                       primary_key.name in item):
                        new_get[primary_key.name] = item[primary_key.name]
                if new_get and self.session.query(
                    self.model
                ).filter_by(**new_get).count():
                    self.session.query(self.model).filter_by(
                        **new_get
                    ).update(self.model(**item).get_dictionary(
                        prefix_filter=''))
                else:
                    new_get.update(item)
                    self.session.add(self.model(**new_get))
        else:
            result = self.session.query(self.model).filter_by(**get)
            if get and result.count():
                result.update(self.model(**data).get_dictionary(
                    prefix_filter=''))
            else:
                get.update(data)
                self.session.add(self.model(**get))
        self.request.rest_data_timestamp_reference_file.set_timestamp()
        return{}

    def process_delete(self, get, data):
        '''Computes the delete response object.'''
        if builtins.isinstance(data, builtins.list):
            for item in data:
                '''
                    Determine additional primary key parts of the data object.
                '''
                new_get = copy(get)
                for primary_key in self.model.__mapper__.primary_key:
                    if(primary_key.name not in get and
                       primary_key.name in item):
                        new_get[primary_key.name] = item[primary_key.name]
                if new_get and self.session.query(
                    self.model
                ).filter_by(**new_get).count():
                    self.session.query(self.model).filter_by(
                        **new_get
                    ).delete()
                    self.request\
                        .rest_data_timestamp_reference_file.set_timestamp()
        elif get and self.session.query(self.model).filter_by(
            **get
        ).count():
            self.session.query(self.model).filter_by(
                **get
            ).delete()
            self.request.rest_data_timestamp_reference_file.set_timestamp()
        return{}

    def process_get(self, data):
        '''Computes the get response object.'''
        if data:
            return[model.get_dictionary(
                **self.data_wrapper
            ) for model in self.session.query(self.model).filter_by(
                **data)]
        return[model.get_dictionary(
            **self.data_wrapper
        ) for model in self.session.query(self.model)]

        # endregion

        # region special request types

    def delete_file_model(self, get, data):
        '''Removes given file.'''
        file = FileHandler(location=get['path'])
        if file.is_file():
            if file.remove_file():
                self.request.rest_data_timestamp_reference_file.set_timestamp()
            else:
                return None
        return{}

    def get_system_model(self, data):
        '''Returns all defined models.'''
        return{
            'freeSpaceInByte': FileHandler(location='/').free_space,
            'usedSpaceInByte': FileHandler(location='/').disk_used_space}

    def get_available_model(self, data):
        '''Returns all defined models.'''
        return builtins.list(builtins.map(
            lambda model: model[0], Module.get_defined_objects(self.model)))

    def get_file_model(self, data):
        '''Returns all files in given location.'''
        result = []
        for file in FileHandler(
            location=data['location'] if 'location' in data else '/'
        ):
            ignored = False
            for pattern in self.request.options['ignore_web_asset_pattern']:
# # python3.4                 if re.compile(pattern).fullmatch(file.name):
                if re.compile('(?:%s)$' % pattern).match(file.name):
                    ignored = True
                    break
            if ignored:
                continue
            file_attributes = {}
            skip = False
            for attribute_name in self.request.options[
                'exportable_file_attributes'
            ]:
# # python3.4
# #                 attribute_name_camel_case = String(
# #                     attribute_name
# #                 ).get_delimited_to_camel_case().content
                attribute_name_camel_case = builtins.unicode(
                    String(attribute_name).get_delimited_to_camel_case(
                    ).content, ENCODING)
# #
                if attribute_name_camel_case not in data or builtins.getattr(
                    file, attribute_name
                ) == data[attribute_name_camel_case]:
                    file_attributes[attribute_name_camel_case] =\
                        builtins.getattr(file, attribute_name)
                else:
                    skip = True
                    break
            if skip:
                continue
            result.append(file_attributes)
        return result

    def put_file_model(self, get, data):
        '''Saves given files.'''
        for items in data.values():
            for item in items:
                if builtins.hasattr(
                    item, 'file'
                ) and item.filename and item.done != -1:
                    shutil.copyfileobj(item.file, builtins.open(FileHandler(
                        self.request.options['location']['medium'] +
                        item.filename
                    )._path, 'wb'))
                    self.request\
                        .rest_data_timestamp_reference_file.set_timestamp()
        return{}

    def put_copy_model(self, get, data):
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
            key_wrapper=lambda key, value: '%s_%s' % (
                get['source'].lower(), key)
        ).content
        for model_name, model in Module.get_defined_objects(
            self.request.model
        ):
            if builtins.isinstance(
                model, builtins.type
            ) and builtins.issubclass(model, self.request.model.Model):
                column_names = builtins.list(builtins.map(
                    lambda property: property.name, model.__table__.columns))
                is_referenced = True
                for key_name in keys:
                    if key_name not in column_names:
                        is_referenced = False
                        break
                if is_referenced:
                    '''
                        NOTE: Property names have to be determined once. \
                        Because sometimes the result is empty due to an \
                        internal caching bug. Additionally this workaround \
                        brings a little performance improvement.
                    '''
                    property_names = []
                    for column in model.__table__.columns:
                        '''Remove unique identifiers for record copies.'''
                        if column.name != 'id':
                            property_names.append(column.name)
                    self.session.commit()
                    for record in self.session.query(
                        model
                    ).filter_by(**keys):
                        self.session.add(model(
                            **record.get_dictionary(
                                value_wrapper=lambda key, value:
                                    data[key] if key in data else value,
                                    property_names=property_names)))
                    self.request\
                        .rest_data_timestamp_reference_file.set_timestamp()
        return{}

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

# region vim modline

# vim: set tabstop=4 shiftwidth=4 expandtab:
# vim: foldmethod=marker foldmarker=region,endregion:

# endregion
