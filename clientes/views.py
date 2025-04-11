from django.shortcuts import render, redirect

def dashboard_view(request):
    if not request.session.get("user"):
        return redirect("login:login")

    return render(request, "clientes/dashboard.html", {"user": request.session["user"]})