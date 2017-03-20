# coding: utf-8
import json
from django.contrib.auth.models import Permission
from rest_framework.serializers import ValidationError
from .models import (StateController,
                     Action,
                     State,
                     Transition,
                     AvailableTask,
                     TransitionTask,)


class FSMUpdater(object):

    '''Updates the FSM underlying data
    based on a JSON representation'''

    def update(self, instance, data):
        raise NotImplementedError


class GoFSMUpdater(FSMUpdater):

    # issues #69
    # def validate_controlled(self, instance, data):

    #     if not instance.representation:
    #         return True

    #     old_representation = json.loads(instance.representation)
    #     new_representation = json.loads(data['representation'])

    #     old_nodes = set([node['text'] for node in old_representation['nodeDataArray']])
    #     new_nodes = set([node['text'] for node in new_representation['nodeDataArray']])

    #     stale = old_nodes - new_nodes
    #     if StateController.objects.filter(machine=instance,
    #                                       current_state__code__in=stale).count() > 0:
    #         raise ValidationError('You cannot change the FSM because there are controlled objects in a removed stated.')

    #     return True

    def update_status(self, fsm, old, new):
        '''this method updates the representation
        of a fsm when the state name is changed'''
        representation = json.loads(fsm.representation)
        for node in representation['nodeDataArray']:
            if node['text'] == old:
                node['text'] = new

        fsm.representation = json.dumps(representation)
        fsm.save()

    def update(self, instance, data):
        if 'representation' not in data:
            return None

        instance.transitions.all().delete()
        representation = json.loads(data['representation'])
        states = {s['key']: s['text'] for s in representation['nodeDataArray']}

        for rep_transition in representation['linkDataArray']:
            from_node = rep_transition['from']
            to_node = rep_transition['to']

            try:
                from_state = State.objects.get(code=states[from_node])
            except:
                from_state = State.objects.create(code=states[from_node])
            try:
                to_state = State.objects.get(code=states[to_node])
            except:
                to_state = State.objects.create(code=states[to_node])

            transition = Transition.objects.create(name=rep_transition['text'],
                                                   machine=instance,
                                                   from_state=from_state,
                                                   to_state=to_state)
            if 'tasks' in rep_transition:
                tasks = [AvailableTask.objects.get(pk=int(t)) for t in rep_transition['tasks']]
                for task in tasks:
                    TransitionTask.objects.create(transition=transition,
                                                  task=task)

            if 'permissions' in rep_transition:
                permissions = [Permission.objects.get(pk=int(p))
                               for p in rep_transition['permissions']]
                for permission in permissions:
                    transition.permissions.add(permission)

        for state_rep in representation['nodeDataArray']:
            state_type = state_rep.get('type', 'common')
            state = State.objects.get(code=state_rep['text'])
            state.actions.clear()
            for action_id in state_rep.get('actions', list()):
                try:
                    action = Action.objects.get(id=action_id)
                    state.actions.add(action)
                except Action.DoesNotExist:
                    pass
            if state_type == 'initial':
                instance.initial_state = state
                instance.save()

        if not instance.initial_state:
            raise ValidationError(u'You need to define an initial state for this FSM.')

        return instance
