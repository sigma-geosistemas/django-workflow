# coding: utf-8
from django.utils.translation import ugettext_lazy as _
from rest_framework.response import Response
from rest_framework import status


INVALID_REQUEST = Response({'status': _('Invalid Request')},
                           status=status.HTTP_400_BAD_REQUEST)
