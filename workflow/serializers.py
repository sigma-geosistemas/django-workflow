# coding: utf-8
from django.db.models import Q
from django.db import transaction
from rest_framework import serializers
from rest_framework.reverse import reverse
from .fsm import GoFSMUpdater
from .models import (StateMachine,
                     State,
                     Action,
                     Transition,
                     TransitionLog,
                     AvailableTask,
                     TransitionTask,
                     StateController)


class LinkSerializer(serializers.ModelSerializer):

    links = serializers.SerializerMethodField()

    def get_links(self, obj):
        raise NotImplementedError


class AvailableTaskSerializer(LinkSerializer):

    def get_links(self, obj):
        return {
            'self': reverse('availabletask-detail',
                            kwargs={'pk': obj.pk})
        }

    class Meta:
        model = AvailableTask
        fields = '__all__'


class StateMachineSerializer(LinkSerializer):

    def get_links(self, obj):
        return {
            'self': reverse('statemachine-detail',
                            kwargs={'pk': obj.pk})
        }

    def update_fsm_graph(self, instance, validated_data):
        gojs = GoFSMUpdater()
        return gojs.update(instance, validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = super(StateMachineSerializer, self).update(instance, validated_data)
        return self.update_fsm_graph(instance, validated_data)

    class Meta:
        model = StateMachine
        fields = '__all__'


class ActionSerializer(LinkSerializer):

    def get_links(self, obj):
        return {
            'self': reverse('action-detail',
                            kwargs={'pk': obj.pk})
        }

    class Meta:
        model = Action
        fields = ('id', 'name', )


class StateSerializer(LinkSerializer):

    text_actions = serializers.SerializerMethodField(read_only=True)

    def update_fsm_representation(self, fsm, old, new):
        gojs = GoFSMUpdater()
        gojs.update_status(fsm, old, new)

    @transaction.atomic
    def update(self, instance, validated_data):
        old_state = instance.code
        new_state = validated_data.get('code', None)
        instance = super(StateSerializer, self).update(instance,
                                                       validated_data)

        if new_state and old_state != new_state:
            state_machines = StateMachine.objects \
                                .filter(Q(transitions__from_state=instance) |
                                        Q(transitions__to_state=instance)).distinct()
            for fsm in state_machines:
                self.update_fsm_representation(fsm,
                                               old_state,
                                               new_state)

        return instance

    def get_text_actions(self, obj):

        action_serializer = ActionSerializer(obj.actions.all(), many=True)
        return action_serializer.data

    def get_links(self, obj):
        return {
            'self': reverse('state-detail',
                            kwargs={'pk': obj.pk})
        }

    class Meta:
        model = State
        fields = ('id',
                  'date_created',
                  'date_updated',
                  'code',
                  'description',
                  'actions',
                  'text_actions')


class TransitionSerializer(LinkSerializer):

    from_state = StateSerializer()

    to_state = StateSerializer()

    def get_links(self, obj):
        return {
            'self': reverse('transition-detail',
                            kwargs={'pk': obj.pk})
        }

    class Meta:
        model = Transition
        fields = '__all__'


class TransitionTaskSerializer(LinkSerializer):

    def get_links(self, obj):
        return {
            'self': reverse('transitiontask-detail',
                            kwargs={'pk': obj.pk})
        }

    class Meta:
        model = TransitionTask
        fields = '__all__'


class StateControllerSerializer(LinkSerializer):

    machine = StateMachineSerializer(many=False, read_only=True)

    current_state = StateSerializer(many=False, read_only=True)

    transitions = TransitionSerializer(source='next',
                                       many=True,
                                       read_only=True)

    def get_links(self, obj):
        return {}

    class Meta:
        model = StateController
        fields = ('id',
                  'machine',
                  'current_state',
                  'inner_state',
                  'task_id',
                  'transitions', )


class TransitionLogSerializer(LinkSerializer):

    from_state = StateSerializer(many=False, read_only=True)

    to_state = StateSerializer(many=False, read_only=True)

    def get_links(self, obj):
        request = self.context['request']
        return {
            'self': reverse('transitionlog-detail',
                            kwargs={'pk': obj.pk},
                            request=request)
        }

    class Meta:

        model = TransitionLog
        fields = '__all__'


class StateControllerSerializerMixIn(LinkSerializer):

    def get_links(self, obj):
        return {}

    state_machine = serializers.IntegerField(write_only=True,
                                             required=False)

    controller = StateControllerSerializer(many=False,
                                           read_only=True)
