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
import inspect
import json

from boostNode.extension.native import Module, InstancePropertyInitializer, \
    Object
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
        self.model = getattr(
            self.request.model, self.request.data['get']['model'])
        '''
            A mapping to wrap reach respond to server. Can be overridden in \
            subclasses.
        '''
        self.data_wrapper = self.request.frontend_data_wrapper

            # endregion

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

    @classmethod
    def process_patch(cls, get, data):
        '''Computes the patch response object.'''
        raise Object.determine_abstract_method_exception(
            abstract_class_name=Response.__name__, class_name=cls.__name__)

    @classmethod
    def process_post(cls, get, data):
        '''Computes the post response object.'''
        raise Object.determine_abstract_method_exception(
            abstract_class_name=Response.__name__, class_name=cls.__name__)

    @classmethod
    def process_put(cls, get, data):
        '''Computes the put response object.'''
        raise Object.determine_abstract_method_exception(
            abstract_class_name=Response.__name__, class_name=cls.__name__)

    @classmethod
    def process_delete(cls, get, data):
        '''Computes the delete response object.'''
        raise Object.determine_abstract_method_exception(
            abstract_class_name=Response.__name__, class_name=cls.__name__)

    @classmethod
    def process_get(cls, data):
        '''Computes the get response object.'''
        raise Object.determine_abstract_method_exception(
            abstract_class_name=Response.__name__, class_name=cls.__name__)

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
