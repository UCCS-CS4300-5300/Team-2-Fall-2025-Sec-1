from django.shortcuts import render

def index(request):
    return render(request, 'home/index.html')

def space_news(request):
    return render(request, 'space_news/nasa_news.html')