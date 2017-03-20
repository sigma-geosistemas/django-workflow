# coding: utf-8
import django.dispatch

initialize_state_machine = django.dispatch.Signal(providing_args=['controlled', 'state_machine', 'initial_state'])
before_state_change = django.dispatch.Signal(providing_args=['controlled', 'controller', 'current', 'next'])
after_state_change = django.dispatch.Signal(providing_args=['controlled', 'controller', 'previous', 'current'])
