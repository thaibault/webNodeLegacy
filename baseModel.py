#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# region header

'''Provides the orm models for the application.'''

__author__ = 'Torben Sickert'
__copyright__ = 'see module docstring'
__credits__ = 'Torben Sickert',
__license__ = 'see module docstring'
__maintainer__ = 'Torben Sickert'
__maintainer_email__ = 't.sickert@gmail.com'
__status__ = 'stable'
__version__ = '1.0'

from datetime import datetime as DateTimeNative
import inspect

from sqlalchemy.ext.declarative import declarative_base as ModelFactory
from sqlalchemy.ext.declarative.api import DeclarativeMeta
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates
from sqlalchemy.schema import Column
from sqlalchemy.types import String, Integer, DateTime, Boolean

from boostNode.extension.native import Module
from boostNode.extension.native import AuthenticationModel
from boostNode.extension.native import Model as BaseModel
from boostNode.extension.type import Model as MetaModel
from boostNode.paradigm.aspectOrientation import FunctionDecorator

from webNode import OPTIONS

# endregion


# region functions

def determine_language_specific_default_value(context):
    '''
        Determines a language specific default value depending on given \
        context.
    '''
    language = OPTIONS['default_language']
    if('language' in context.current_parameters and
       context.current_parameters['language'] is not None):
        language = context.current_parameters['language']
    for column in context.prefetch_cols:
        '''
            Take this method type by another instance of this class via \
            introspection.
        '''
        if(column.default.arg is
           globals()[inspect.stack()[0][3]] and
           context.current_parameters[column.name] is None):
## python3.3
##             return OPTIONS['default_language_specific_values'][
##                 column.name][language]
            return OPTIONS['default_language_specific_values'][
                column.name
            ][language].decode(OPTIONS['encoding'])
##

# endregion


# region classes

class ApplicationMetaModel(DeclarativeMeta, MetaModel):

    '''Class that invokes for each model class generation.'''

    def __new__(
        cls, class_name, base_classes, class_scope, *arguments, **keywords
    ):
        '''
            Triggers if a new instance is created. Sets a property validator \
            and sqlalchemy's getter and setter methods.
        '''
        class_scope['__validate_property__'] = validates(
            *class_scope.keys()
        )(lambda *arguments: BaseModel.validate_property(
            *arguments, info_determiner=lambda model_instance, name: getattr(
                model_instance.__class__, name
            ).info))
        '''Set magic getter and setter.'''
        for base_class in base_classes:
            for property_name, value in base_class.__dict__.items():
                if callable(value) and property_name[3:] not in class_scope:
                    if property_name.startswith('get_'):
                        if isinstance(value, FunctionDecorator):
                            value = value.__func__
                        class_scope[property_name[4:]] = hybrid_property(value)
                        if 'set_' + property_name[4:] in base_class.__dict__:
                            class_scope['set_' + property_name[4:]] = \
                                class_scope[property_name[4:]].setter(
                                    base_class.__dict__[
                                        'set_' + property_name[4:]])
        '''Take this method name via introspection.'''
        return getattr(
            super(ApplicationMetaModel, cls), inspect.stack()[0][3]
        )(cls, class_name, base_classes, class_scope, *arguments, **keywords)

Model = ModelFactory(cls=BaseModel, metaclass=ApplicationMetaModel)


class BaseUser(AuthenticationModel):

    '''Saves all registered users.'''

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    register_date_time = Column(DateTime, default=DateTimeNative.now)
    enabled = Column(Boolean, default=True)

    session_token = Column(
        String(2 * OPTIONS['session_token_length']), default=None)
    application_session_token = Column(
        String(2 * OPTIONS['session_token_length']), default=None)
    session_expiration_date_time = Column(DateTime, default=DateTimeNative.now)

    _password_salt_length = OPTIONS['password_salt_length']
    _password_pepper = OPTIONS['password_pepper']
    _password_info = OPTIONS['password_info']
    password_salt = Column(String(2 * OPTIONS['password_salt_length']))
    password_hash = Column(String(
        160 + 2 * OPTIONS['password_salt_length'] + len(
            OPTIONS['password_pepper'])))

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
Module.default(
    name=__name__, frame=inspect.currentframe(), default_caller=False)

# endregion

# region vim modline

# vim: set tabstop=4 shiftwidth=4 expandtab:
# vim: foldmethod=marker foldmarker=region,endregion:

# endregion