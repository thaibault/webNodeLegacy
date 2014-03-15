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

# endregion


# region classes

class Main:

    '''Contains the main application specific business logic.'''

    def __init__(self, web_handler):
        '''Initializes the main application controller.'''
        self.web_handler = web_handler

    @classmethod
    def insert_database_mockups(cls):
        '''Inserts some example data to the database.'''

    def response(self):
        '''Handles a non rest or static web request.'''

# endregion
