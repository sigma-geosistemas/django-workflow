# coding: utf-8


def create_actions(apps=None, schema_editor=None):

    from .models import Action
    Action.objects.create(name='Upload')
    Action.objects.create(name='SampleParams')
    Action.objects.create(name='Review')
    Action.objects.create(name='Download')
