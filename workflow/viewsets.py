# coding: utf-8
from copy import deepcopy
import celery
from rest_framework import viewsets
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from common.viewsets import DefaultViewSetMixIn
from .choices import INNER_STATE_RUNNING
from .rest.responses import INVALID_REQUEST
from .filters import (StateMachineFilter,
                      ActionFilter,
                      TransitionLogFilter,
                      AvailableTaskFilter,)
from .models import (StateMachine,
                     State,
                     Action,
                     Transition,
                     TransitionLog,
                     AvailableTask,
                     TransitionTask, )
from .serializers import (StateMachineSerializer,
                          StateSerializer,
                          ActionSerializer,
                          AvailableTaskSerializer,
                          TransitionSerializer,
                          TransitionLogSerializer,
                          TransitionTaskSerializer, )


class CeleryInspectViewSet(DefaultViewSetMixIn,
                           viewsets.ViewSet):

    permission_classes = (IsAuthenticated, )
    inspect = celery.current_app.control.inspect()

    @list_route(methods=["get"])
    def ping(self, request):
        result = self.inspect.ping()
        return Response(result, status=status.HTTP_200_OK)

    @list_route(methods=["get"])
    def registered(self, request):
        result = self.inspect.registered()
        return Response(result, status=status.HTTP_200_OK)

    @list_route(methods=["get"])
    def active(self, request):
        result = self.inspect.active()
        new_result = []
        for k, v in result.items():
            new_result.extend(v)
        return Response(new_result, status=status.HTTP_200_OK)

    @list_route(methods=["get"])
    def scheduled(self, request):
        result = self.inspect.scheduled()
        return Response(result, status=status.HTTP_200_OK)


class ActionViewSet(DefaultViewSetMixIn,
                    viewsets.ModelViewSet):

    queryset = Action.objects.all()
    serializer_class = ActionSerializer
    filter_class = ActionFilter
    search_fields = ('id', 'name', )


class AvailableTaskViewSet(DefaultViewSetMixIn,
                           viewsets.ModelViewSet):

    queryset = AvailableTask.objects.all()
    serializer_class = AvailableTaskSerializer
    filter_class = AvailableTaskFilter
    search_fields = ('id', 'name', )


class StateMachineViewSet(DefaultViewSetMixIn,
                          viewsets.ModelViewSet):

    queryset = StateMachine.objects.all()
    serializer_class = StateMachineSerializer
    filter_class = StateMachineFilter
    search_fields = ('id', 'name', )


class StateViewSet(DefaultViewSetMixIn,
                   viewsets.ModelViewSet):

    queryset = State.objects.all()
    serializer_class = StateSerializer


class TransitionViewSet(DefaultViewSetMixIn,
                        viewsets.ModelViewSet):

    queryset = Transition.objects.all()
    serializer_class = TransitionSerializer


class TaskViewSet(DefaultViewSetMixIn,
                  viewsets.ModelViewSet):

    queryset = TransitionTask.objects.all()
    serializer_class = TransitionTaskSerializer


class TransitionLogViewSet(DefaultViewSetMixIn,
                           viewsets.ModelViewSet):

    queryset = TransitionLog.objects.all()
    serializer_class = TransitionLogSerializer
    filter_class = TransitionLogFilter
    search_fields = ('controller', )


class StateControllerViewSetMixIn(object):

    @detail_route(methods=['get', 'put'])
    def data(self, request, pk=None):
        self.controlled = self.get_object()
        if request.method == 'GET':
            data = self.controlled.current_data
            return Response(data.data, status=status.HTTP_200_OK)
        else:
            try:
                current_data = self.controlled.current_data
                current_data.data = request.data
                original = current_data.data
                copied = deepcopy(original)
                copied.update(request.data)
                current_data.data = copied
                current_data.save()
                return Response(request.data, status=status.HTTP_200_OK)
            except:
                return Response({'message': 'Fail on saving data.'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @detail_route(methods=['post'])
    def change(self, request, pk=None):
        controlled = self.get_object()
        controller = controlled.controller
        if not controller:
            return INVALID_REQUEST

        if controller.inner_state == INNER_STATE_RUNNING:
            return Response({'status': 'FSM already running for this project.'},
                            status=status.HTTP_400_BAD_REQUEST)

        state_id = request.data.get('state_id', None)
        if not state_id:
            return INVALID_REQUEST
        try:
            state = State.objects.get(pk=state_id)
        except:
            return Response({'status': 'State does not exist'},
                            status=status.HTTP_400_BAD_REQUEST)
        available = controlled.next_for_user(request.user)
        if int(state_id) not in [s.to_state.id for s in available]:
            return Response({'status': 'Invalid transition'},
                            status=status.HTTP_400_BAD_REQUEST)

        task = controller.change_to(state)

        return Response({
            'status': 'State change requested',
            'task': task.id
        })
