# coding: utf-8
import rest_framework_filters
from .models import (StateMachine,
                     Action,
                     AvailableTask,
                     TransitionLog,)


class ActionFilter(rest_framework_filters.FilterSet):

    class Meta:
        model = Action
        fields = {
            'id': ['exact', 'in'],
            'name': ['icontains']
        }


class AvailableTaskFilter(rest_framework_filters.FilterSet):

    class Meta:
        model = AvailableTask
        fields = {
            'id': ['exact', 'in'],
            'name': ['icontains']
        }


class StateMachineFilter(rest_framework_filters.FilterSet):

    class Meta:
        model = StateMachine
        fields = {
            'id': ['exact'],
            'name': ['icontains']
        }


class TransitionLogFilter(rest_framework_filters.FilterSet):

    class Meta:

        model = TransitionLog
        fields = {
            'controller': ['exact']
        }
