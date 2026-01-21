from django.shortcuts import render

def error_403_view(request, exception=None):
    return render(request, "core/403.html", status=403)
