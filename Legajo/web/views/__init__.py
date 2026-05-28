# Paquete legacy de vistas.

from django.http import HttpResponse, JsonResponse

def ping(request):
    return HttpResponse("pong")