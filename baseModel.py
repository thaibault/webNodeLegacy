#!/usr/bin/env python3.4
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
from sqlalchemy.types import Boolean, DateTime, String

from boostNode.extension.native import Module
from boostNode.extension.native import Model as BaseModel
from boostNode.extension.native import AuthenticationModel as \
    BaseAuthenticationModel
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
        if(column.default.arg is globals()[inspect.stack()[0][3]] and
           context.current_parameters[column.name] is None):
# # python2.7
# # 
# #              return OPTIONS['model']['generic']['language_specific']['default'][
# #                 column.name
# #             ][language].decode(OPTIONS['encoding'])

             return OPTIONS['model']['generic']['language_specific'][
                'default'
            ][column.name][language]
# #

# endregion


# region classes

class ApplicationMetaModel(MetaModel, DeclarativeMeta):

    '''Class that invokes for each model class generation.'''

    def __new__(
        cls, class_name, base_classes, class_scope, *arguments, **keywords
    ):
        '''
            Triggers if a new instance is created. Sets a property validator \
            and sqlalchemy's getter and setter methods.
        '''
        '''
            Use sqlalchemy's validation decorator to validate each model \
            modification.
        '''
        class_scope['__validate_property__'] = validates(
            *class_scope.keys()
        )(lambda *arguments: BaseModel.validate_property(
            *arguments,
            information_determiner=lambda model_instance, name: getattr(
                model_instance.__class__, name
            ).info))
        '''Set magic getter and setter.'''
        for concrete_base_class in base_classes:
            '''NOTE: "mro" means method resolution order.'''
            class_hierarchy = concrete_base_class.mro()
            class_hierarchy.reverse()
            for base_class in class_hierarchy:
                '''
                    Defines a sqlalchemy setter or getter methods for each \
                    defined method with specified function name pattern.
                '''
                for property_name, value in base_class.__dict__.items():
                    if(callable(value) and
                       property_name[3:] not in class_scope):
                        if property_name.startswith('get_'):
                            if isinstance(value, FunctionDecorator):
                                value = value.__func__
                            class_scope[property_name[4:]] = hybrid_property(
                                value)
                            if('set_' + property_name[4:] in
                               base_class.__dict__):
                                class_scope['set_' + property_name[4:]] = \
                                    class_scope[property_name[4:]].setter(
                                        base_class.__dict__[
                                            'set_' + property_name[4:]])
        '''Take this method name via introspection.'''
        return getattr(
            super(ApplicationMetaModel, cls), inspect.stack()[0][3]
        )(cls, class_name, base_classes, class_scope, *arguments, **keywords)


class UpdateTriggerModel(object):

    '''
        Provides a property to register each write access on corresponding \
        table.
    '''

    creation_date_time = Column(
        DateTime, nullable=False, default=DateTimeNative.now)
    last_update_date_time = Column(
        DateTime, nullable=False, default=DateTimeNative.now,
        onupdate=DateTimeNative.now)


class AuthenticationModel(BaseAuthenticationModel):

    '''
        Provides columns for saving authentication tokens and password \
        properties.
    '''

    register_date_time = Column(
        DateTime, default=DateTimeNative.now, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    session_token = Column(
        String(
            2 * OPTIONS['model']['authentication']['session_token']['length']),
        unique=True, default=None)
    application_session_token = Column(
        String(
            2 * OPTIONS['model']['authentication']['session_token']['length']),
        unique=True, default=None)
    session_expiration_date_time = Column(
        DateTime, default=DateTimeNative.now, nullable=False)
    password_salt = Column(
        String(2 * OPTIONS['model']['authentication']['password']['salt'][
            'length']
        ), nullable=False)
    password_hash = Column(String(
        160 + 2 * OPTIONS['model']['authentication']['password']['salt'][
            'length'
        ] + len(OPTIONS['model']['authentication']['password']['pepper'])
    ), nullable=False)
    _password_information = OPTIONS['model']['authentication']['password']

Model = ModelFactory(cls=BaseModel, metaclass=ApplicationMetaModel)

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
