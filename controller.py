#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-

# region header

'''Provides a simple web controller.'''

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
import inspect

from boostNode.extension.native import Module
# # python2.7 from boostNode.extension.native import Dictionary
pass

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
    def stop(cls, *arguments, **keywords):
        '''Is called if application is shutting down.'''
        return cls

    @classmethod
    def initialize(cls):
        '''
            Initializes the main application controller (options are already \
            rendered but can be manipulates by returning a modified version).
        '''
        return cls.main.options

    @classmethod
    def initialize_model(cls):
        '''Inserts some needed initialisation records to the database.'''
        return cls

    @classmethod
    def initialize_model_mockup(cls):
        '''Inserts some example data to the database.'''
        return cls

    @classmethod
    def launch(cls):
        '''
            This method is triggered if everything has finished and \
            application service can be launched.
        '''
        return cls

    @classmethod
    def get_template_scope(cls, current_scope):
        '''Returns manipulated main index html template scope variables.'''
        return current_scope

        # endregion

    def response(
        self, request, output, mime_type, cache_control_header, cache_file
    ):
        '''Handles a non rest or static web request.'''
        return output, mime_type, cache_control_header, cache_file

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
