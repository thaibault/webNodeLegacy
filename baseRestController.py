#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# region header

'''Provides a generic Response object for any web based web application.'''

__author__ = 'Torben Sickert'
__copyright__ = 'see module docstring'
__credits__ = 'Torben Sickert',
__license__ = 'see module docstring'
__maintainer__ = 'Torben Sickert'
__maintainer_email__ = 't.sickert@gmail.com'
__status__ = 'stable'
__version__ = '1.0'

# # python3.4 from base64 import b64encode as base64encode
pass
from copy import copy
from datetime import datetime as DateTime
import inspect
import json
import os
import re

from sqlalchemy.exc import SQLAlchemyError

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
               'get', 'put', 'post', 'patch', 'delete')):
            self.request.data['request_type'] = self.request.data['get'][
                '__method__']
            del self.request.data['get']['__method__']
        if hasattr(self.request.model, self.request.data['get']['__model__']):
            self.model = getattr(
                self.request.model, self.request.data['get']['__model__'])
        else:
            method_name = '%s_%s_model' % (
                self.request.data['request_type'],
                self.request.data['get']['__model__'].lower())
            if hasattr(self, method_name):
                self.model = getattr(self, method_name)
            elif hasattr(self.request.controller, method_name):
                self.method_in_rest_controller = False
                self.model = getattr(self.request.controller, method_name)
        '''
            A mapping to wrap each respond to client. Can be overridden in \
            subclasses.
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
        if self.model is None:
            self.request.data['handler'].send_response(
                510, 'Requested model "%s" doesn\'t exist.' %
                self.request.data['get']['__model__'])
            result = {
                'statuscode': 510, 'message': 'Not Extended', 'data': {},
                'description': 'Requested model "%s" doesn\'t exist.' %
                self.request.data['get']['__model__']}
        else:
            if not self.model.__name__.endswith('_file_model'):
                if isinstance(self.request.data['data'], list):
                    for index, item in enumerate(self.request.data['data']):
                        self.request.data['data'][index] = \
                            self.request.controller.convert_for_database(item)
                else:
                    self.request.data['data'] = \
                        self.request.controller.convert_for_database(
                            self.request.data['data'])
            if hasattr(self.model, '__table__'):
                method = getattr(
                    self, 'process_%s' % self.request.data['request_type'])
                try:
                    if self.request.data['request_type'] == 'get':
                        result = method(data=self.request.data['get'])
                    else:
                        result = method(
                            get=self.request.data['get'],
                            data=self.request.data['data'])
                except (SQLAlchemyError, ValueError) as exception:
                    self.request.session.rollback()
                    self.request.data['handler'].send_response(
                        400, '%s: "%s"' % (
                            exception.__class__.__name__, str(exception)))
                    result = {
                        'statuscode': 400, 'message': 'Bad Request',
                        'data': {},
                        'description': '%s: %s' % (
                            exception.__class__.__name__, str(exception))}
            elif self.request.data['request_type'] == 'get':
                if self.method_in_rest_controller:
                    result = self.model(data=self.request.data['get'])
                else:
                    result = self.model(
                        data=self.request.data['get'], rest_controller=self)
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
                result = {
                    'statuscode': 401, 'message': 'Unauthorized', 'data': {},
                    'description': 'The request is not authorized.'}
            elif not isinstance(result, dict) or result.get(
                'statuscode'
            ) is None:
                result = {
                    'statuscode': 200, 'message': 'OK', 'data': result,
                    'description': 'The request was successfully proceeded.'}
        return json.dumps(result)

        # endregion

        # region request type

    def process_patch(self, get, data):
        '''Computes the patch response object.'''
        self.request.session.query(self.model).filter_by(**get).update(
            self.model(**data).get_dictionary(prefix_filter=''))
        self.request.session.commit()
        return{}

    def process_post(self, get, data):
        '''Computes the post response object.'''
        if self.request.model.User is self.model:
            if 'has_password' in data:
                value = data['has_password']
                del data['has_password']
                for model in self.request.session.query(
                    self.model
                ).filter_by(**data):
                    if model.has_password(value):
                        '''
                            Save session token in database with expiration \
                            time.
                        '''
# # python3.4
# #                         model.session_token = base64encode(os.urandom(
# #                             self.request.options['model'][
# #                                 'authentication'
# #                             ]['session_token']['length']
# #                         )).decode('utf8').strip()
                        model.session_token = os.urandom(
                            self.request.options['model'][
                                'authentication'
                            ]['session_token']['length']
                        ).encode('base_64').strip()
# #
                        model.session_expiration_date_time = DateTime.now(
                        ) + self.request.options['session'][
                            'expiration_interval']
                        '''
                            NOTE: Model data has to be rendered before \
                            session is committed, to avoid temporary lose \
                            data.
                        '''
                        result = model.get_dictionary(**self.data_wrapper)
                        self.request.session.commit()
                        return result
            elif(self.request.authorized_user is not None and
                 data.get('id') == self.request.authorized_user.id):
                return self.request.authorized_user.get_dictionary(
                    **self.data_wrapper)

    def process_put(self, get, data):
        '''Computes the put response object.'''
        if isinstance(data, list):
            for item in data:
                '''
                    Determine additional primary key parts of the data object.
                '''
                new_get = copy(get)
                for primary_key in self.model.__mapper__.primary_key:
                    if(primary_key.name not in get and
                       primary_key.name in item):
                        new_get[primary_key.name] = item[primary_key.name]
                if new_get and self.request.session.query(
                    self.model
                ).filter_by(**new_get).count():
                    self.request.session.query(self.model).filter_by(
                        **new_get
                    ).update(self.model(**item).get_dictionary(
                        prefix_filter=''))
                else:
                    new_get.update(item)
                    self.request.session.add(self.model(**new_get))
        elif get and self.request.session.query(self.model).filter_by(
            **get
        ).count():
            self.request.session.query(self.model).filter_by(**get).update(
                self.model(**data).get_dictionary(prefix_filter=''))
        else:
            get.update(data)
            self.request.session.add(self.model(**get))
        self.request.session.commit()
        return{}

    def process_delete(self, get, data):
        '''Computes the delete response object.'''
        if isinstance(data, list):
            for item in data:
                '''
                    Determine additional primary key parts of the data object.
                '''
                new_get = copy(get)
                for primary_key in self.model.__mapper__.primary_key:
                    if(primary_key.name not in get and
                       primary_key.name in item):
                        new_get[primary_key.name] = item[primary_key.name]
                if new_get and self.request.session.query(
                    self.model
                ).filter_by(**new_get).count():
                    self.request.session.query(self.model).filter_by(
                        **new_get
                    ).delete()
        elif get and self.request.session.query(self.model).filter_by(
            **get
        ).count():
            self.request.session.query(self.model).filter_by(
                **get
            ).delete()
        self.request.session.commit()
        return{}

    def process_get(self, data):
        '''Computes the get response object.'''
        if data:
            return [model.get_dictionary(
                **self.data_wrapper
            ) for model in self.request.session.query(self.model).filter_by(
                **data)]
        return[model.get_dictionary(
            **self.data_wrapper
        ) for model in self.request.session.query(self.model)]

        # endregion

    def delete_file_model(self, get, data):
        '''Removes given file.'''
        file = FileHandler(location=get['path'])
        if file:
            return{} if file.remove_file() else None
        self.request.data['handler'].send_response(
            510, 'Requested file "%s" doesn\'t exist.' % get['path'])
        return{
            'statuscode': 510, 'message': 'Not Extended', 'data': {},
            'description': 'Requested file "%s" doesn\'t exist.' % get['path']}

    def get_available_model(self, data):
        '''Returns all defined models.'''
        return list(map(lambda model: model[0], Module.get_defined_objects(
            self.model)))

    def get_file_model(self, data):
        '''Returns all files in given location.'''
        result = []
        for file in FileHandler(
            location=data['location'] if 'location' in data else '/'
        ):
            ignored = False
            for pattern in self.request.options['ignore_web_asset_pattern']:
                if re.compile(pattern).match(file.name):
                    ignored = True
                    break
            if ignored:
                continue
            file_attributes = {}
            for attribute_name in self.request.options[
                'exportable_file_attributes'
            ]:
                file_attributes[String(
                    attribute_name
                ).delimited_to_camel_case().content] = getattr(
                    file, attribute_name)
            result.append(file_attributes)
        return result

    def put_file_model(self, get, data):
        '''Saves given files.'''
        for items in data.values():
            for item in items:
                FileHandler(
                    self.request.options['location']['media'] + item['name']
                ).set_content(content=item['content'], mode='w+b')
        return{}

    def put_copy_model(self, get, data):
        '''Copies give model references.'''
        keys = copy(get)
        del keys['source']
        keys = Dictionary(keys).convert(
            key_wrapper=lambda key, value: '%s_%s' % (
                get['source'].lower(), key)
        ).content
        data = Dictionary(data).convert(
            key_wrapper=lambda key, value: '%s_%s' % (
                get['source'].lower(), key)
        ).content
        for model_name, model in Module.get_defined_objects(
            self.request.model
        ):
            if model_name != get['source']:
                column_names = list(map(
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
                        brings a little performance.
                    '''
                    property_names = tuple(map(
                        lambda column: column.name, model.__table__.columns))
                    for record in self.request.session.query(
                        model
                    ).filter_by(**keys):
                        self.model = model
                        self.process_put(
                            get={}, data=record.get_dictionary(
                                value_wrapper=lambda key, value:
                                data[key] if key in data else value,
                                property_names=property_names))
                        self.request.session.commit()
        return{}

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
