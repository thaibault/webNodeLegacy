#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# region header

'''Provides a generic Response object for any web based web application.'''

## python3.4 pass
from __future__ import print_function

__author__ = 'Torben Sickert'
__copyright__ = 'see module docstring'
__credits__ = 'Torben Sickert',
__license__ = 'see module docstring'
__maintainer__ = 'Torben Sickert'
__maintainer_email__ = 't.sickert@gmail.com'
__status__ = 'stable'
__version__ = '1.0'

## python3.4 from base64 import b64encode as base64encode
pass
from copy import copy
from datetime import datetime as DateTime
import inspect
import json
import os

from boostNode.extension.native import Module, InstancePropertyInitializer
from boostNode.paradigm.objectOrientation import Class

# endregion


# region classes

class Response(Class):

    '''Handles rest api requests.'''

    # region public methods

        # region special

    @InstancePropertyInitializer
    def __init__(self, request):
        '''Retrieves request meta data.'''

            # region properties

        '''Saves current selected model.'''
        self.model = None
        if hasattr(self.request.model, self.request.data['get']['model']):
            self.model = getattr(
                self.request.model, self.request.data['get']['model'])
        else:
            method_name = '%s_%s_model' % (
                self.request.data['request_type'],
                self.request.data['get']['model'].lower())
            if hasattr(self.request.controller, method_name):
                self.model = getattr(self.request.controller, method_name)
        '''
            A mapping to wrap reach respond to server. Can be overridden in \
            subclasses.
        '''
        self.data_wrapper = self.request.frontend_data_wrapper

            # endregion

        if self.model is not None:
            del self.request.data['get']['model']

        # endregion

        # region getter

    @Class.pseudo_property
    def get_output(self):
        '''Computes the json response object.'''
        if self.model is None:
            self.request.data['handler'].send_response(510)
            return{
                'statuscode': 510, 'message': 'Not Extended', 'data': {},
                'description': 'Requested model "%s" doesn\'t exist.' %
                self.request.data['get']['model']}
        else:
            if isinstance(self.request.data['data'], list):
                for index, item in enumerate(self.request.data['data']):
                    self.request.data['data'][index] = \
                        self.request.controller.convert_for_database(item)
            else:
                self.request.data['data'] = \
                    self.request.controller.convert_for_database(
                        self.request.data['data'])
            if not hasattr(self.model, '__table__'):
                result = self.model(
                    get=self.request.data['get'], data=self.request.data['data'],
                    request=self.request)
            else:
                method = getattr(
                    self, 'process_%s' % self.request.data['request_type'])
                if self.request.data['request_type'] == 'get':
                    result = method(data=self.request.data['get'])
                else:
                    result = method(
                        get=self.request.data['get'],
                        data=self.request.data['data'])
            if result is None:
                self.request.data['handler'].send_response(401)
                result = {
                    'statuscode': 401, 'message': 'Unauthorized', 'data': {},
                    'description': 'The request is not authorized.'}
            elif not isinstance(result, dict) or result.get('statuscode') is None:
                result = {
                    'statuscode': 200, 'message': 'OK', 'data': result,
                    'description': 'The request was successfully proceeded.'}
        return json.dumps(result)

        # endregion

        # region request type

    def process_patch(self, get, data):
        '''Computes the patch response object.'''
        if self.request.authorized_user is not None:
            self.request.session.query(self.model).filter_by(**get).update(
                data)
            return {}

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
## python3.4
##                         model.session_token = base64encode(os.urandom(
##                             self.request.options['model'][
##                                 'authentication'
##                             ]['session_token']['length']
##                         )).decode('utf8').strip()
                        model.session_token = os.urandom(
                            self.request.options['model']['authentication'][
                                'session_token'
                            ]['length']
                        ).encode('base_64').strip()
##
                        model.session_expiration_date_time = DateTime.now(
                        ) + self.request.options['session'][
                            'expiration_interval']
                        return model.get_dictionary(**self.data_wrapper)
            elif(self.request.authorized_user is not None and
                 data.get('id') == self.request.authorized_user.id):
                return self.request.authorized_user.get_dictionary(
                    **self.data_wrapper)

    def process_put(self, get, data):
        '''Computes the put response object.'''
        if self.request.authorized_user is not None:
            if isinstance(data, list):
                for item in data:
                    # Determine additional primary key parts of the data
                    # object.
                    new_get = copy(get)
                    for primary_key in self.model.__mapper__.primary_key:
                        if not primary_key.name in get:
                            new_get[primary_key.name] = item[primary_key.name]
                    if self.request.session.query(self.model).filter_by(
                        **new_get
                    ).count():
                        self.request.session.query(self.model).filter_by(
                            **new_get
                        ).update(item)
                    else:
                        new_get.update(item)
                        self.request.session.add(self.model(**new_get))
            elif self.request.session.query(self.model).filter_by(
                **get
            ).count():
                self.request.session.query(self.model).filter_by(**get).update(
                    data)
            else:
                get.update(data)
                self.request.session.add(self.model(**data))
            return {}

    def process_delete(self, get, data):
        '''Computes the delete response object.'''
        if self.request.authorized_user is not None:
            if isinstance(data, list):
                for item in data:
                    # Determine additional primary key parts of the data
                    # object.
                    get.update(data)
                    if self.request.session.query(self.model).filter_by(
                        **get
                    ).count():
                        self.request.session.query(self.model).filter_by(
                            **get
                        ).delete()
            elif self.request.session.query(self.model).filter_by(
                **get
            ).count():
                self.request.session.query(self.model).filter_by(
                    **get
                ).delete()
            return {}

    def process_get(self, data):
        '''Computes the get response object.'''
        if data:
            return [model.get_dictionary(
                **self.data_wrapper
            ) for model in self.request.session.query(self.model).filter_by(
                **data)]
        return [model.get_dictionary(
            **self.data_wrapper
        ) for model in self.request.session.query(self.model)]

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
