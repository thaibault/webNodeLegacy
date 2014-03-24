#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# region header

'''Provides a simple web controller.'''

## python3.3 pass
from __future__ import print_function

__author__ = 'Torben Sickert'
__copyright__ = 'see module docstring'
__credits__ = 'Torben Sickert',
__license__ = 'see module docstring'
__maintainer__ = 'Torben Sickert'
__maintainer_email__ = 't.sickert@gmail.com'
__status__ = 'stable'
__version__ = '1.0'

from boostNode.extension.native import ClassPropertyInitializer

# endregion


# region classes

class Main:

    '''Contains the main application specific business logic.'''

    @ClassPropertyInitializer(classmethod)
    def __init__(cls, main):
        '''Initializes the main application controller properties.'''

    def initialize(cls):
        '''
            Initializes the main application controller (options are already
            rendered).
        '''

    @classmethod
    def insert_database_mockup(cls):
        '''Inserts some example data to the database.'''

    @classmethod
    def get_frontend_scope(cls):
        '''Returns additional manifest template scope variables.'''
        return {}

    def response(self, request):
        '''Handles a non rest or static web request.'''
        return ''

    def get_manifest_scope(self, request, user):
        '''Returns additional manifest template scope variables.'''
        return {}

# endregion
