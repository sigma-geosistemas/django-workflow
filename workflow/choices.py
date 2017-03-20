# coding: utf-8
from django.utils.translation import ugettext_lazy as _
INNER_STATE_IDLE = 'idle'
INNER_STATE_RUNNING = 'running'

INNER_STATE_CHOICES = ((INNER_STATE_IDLE, _('Idle')),
                       (INNER_STATE_RUNNING, _('Running')), )
