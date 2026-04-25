from django.shortcuts import render, redirect


def index_gateway(request):
    return redirect('/welcome')


def admin_site(request):
    return render(request, 'admin_dashboard.html')


def lbas_site(request):
    return render(request, 'LBAS.html')


def landing_site(request):
    return render(request, 'Library_web_landing_page.html')


def welcome_site(request):
    return render(request, 'Welcome_main.html')


def creators_site(request):
    return render(request, 'Creators.html')


def user_tablet_site(request):
    return render(request, 'user_tablet.html')
