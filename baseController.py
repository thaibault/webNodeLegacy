#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# region header

'''Provides a simple web controller.'''

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

import inspect

from boostNode.extension.native import ClassPropertyInitializer, Module

# endregion


# region classes

class Main:

    '''Contains the main application specific business logic.'''

    @ClassPropertyInitializer(classmethod)
    def __init__(cls, main):
        '''Initializes the main application controller properties.'''

    @classmethod
    def initialize(cls):
        '''
            Initializes the main application controller (options are already \
            rendered).
        '''
        return cls.main.options

    @classmethod
    def insert_database_mockup(cls):
        '''Inserts some example data to the database.'''

    @classmethod
    def get_frontend_scope(cls, current_scope):
        '''Returns additional manifest template scope variables.'''
        return {}

    @classmethod
    def convert_for_database(cls, data):
        '''Converts given data to database compatible values.'''
        return data

    def response(self, request):
        '''Handles a non rest or static web request.'''
        return ''

    def get_manifest_scope(self, request, user):
        '''Returns additional manifest template scope variables.'''
        return {}

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
