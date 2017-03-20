# coding: utf-8
import logging
from django.dispatch import receiver
from .signals import (after_state_change,
                      initialize_state_machine, )


logger = logging.getLogger(__name__)


@receiver(initialize_state_machine)
def initialize_state_controller(sender, **kwargs):
    from .models import StateController
    controlled = kwargs.get('controlled')
    state_machine = kwargs.get('state_machine')
    initial_state = kwargs.get('initial_state')
    try:
        c = StateController.objects.create(content_object=controlled,
                                           machine=state_machine,
                                           current_state=initial_state)
    except Exception as ex:
        logger.error(u'Criação de StateController falhou.\n{0}'.format(ex.message))
        return

    after_state_change.send_robust(sender,
                                   controlled=controlled,
                                   controller=c,
                                   previous=None,
                                   current=initial_state)


@receiver(after_state_change)
def log_on_state_change(sender, **kwargs):
    from .models import TransitionLog
    controller = kwargs.get('controller')
    from_state = kwargs.get('previous', None)
    to_state = kwargs.get('current', None)
    TransitionLog.objects.create(controller=controller,
                                 from_state=from_state,
                                 to_state=to_state)


@receiver(after_state_change)
def create_state_data_on_state_change(sender, **kwargs):
    from .models import StateControllerData
    controller = kwargs.get('controller')
    state = kwargs.get('current')
    previous = kwargs.get('previous')
    try:
        data = StateControllerData.objects.filter(controller=controller,
                                                  state=previous).latest('date_created')
        data = data.data
        StateControllerData.objects.create(controller=controller,
                                           state=state,
                                           data=data)
    except:
        StateControllerData.objects.create(controller=controller,
                                           state=state)
