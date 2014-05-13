#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# region header

'''Provides a simple web controller.'''

__author__ = 'Torben Sickert'
__copyright__ = 'see module docstring'
__credits__ = 'Torben Sickert',
__license__ = 'see module docstring'
__maintainer__ = 'Torben Sickert'
__maintainer_email__ = 't.sickert@gmail.com'
__status__ = 'stable'
__version__ = '1.0'

import inspect

from boostNode.extension.native import Dictionary, Module

# endregion


# region classes

class Main(object):

    '''Contains the main application specific business logic.'''

    # region public method

    # # region static

    # # # region special

    @classmethod
    def __init__(cls, main):
        '''Initializes the main application controller properties.'''
        cls.main = main

    # # # endregion

    @classmethod
    def initialize(cls):
        '''
            Initializes the main application controller (options are already \
            rendered but can be manipulates by returning a modified version).
        '''
        return cls.main.options

    @classmethod
    def insert_needed_database_record(cls):
        '''Inserts some needed initialisation records to the database.'''
        return cls

    @classmethod
    def insert_database_mockup(cls):
        '''Inserts some example data to the database.'''
        return cls

    @classmethod
    def get_frontend_scope(cls, current_scope):
        '''Returns manipulated main index html template scope variables.'''
        return current_scope

    @classmethod
    def convert_for_database(cls, data):
        '''Converts given data to database compatible values.'''
# # python3.4 # #         if cls.main.options['database_engine_prefix'].startswith(

# #             'sqlite:'
# #         ):
# #             return Dictionary(data).convert(
# #                 value_wrapper=lambda key, value: unicode(
# #                     value, cls.main.options['encoding']
# #                 ) if isinstance(value, str) else value
# #             ).content
        return data

        # endregion

    def response(self, request, output, mime_type, cache_control, cache_file):
        '''Handles a non rest or static web request.'''
        return''

    def get_manifest_scope(self, request, user):
        '''Returns additional manifest template scope variables.'''
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
