"""ST URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from .view import login, UploadFileView, TemplateListView, TemplateCreateView, TemplateDeleteView, TemplateUpdateView, \
    TemplateItem, DataListView, DataCreateView, DataUpdateView, DataDeleteView, DataItem, \
    UnitListView, UnitItem, UnitCreateView, UnitUpdateView, UnitDeleteView, LoginUnitListView,UnitSearchView,TemplateSearchView,\
    EquipmentSearchView
urlpatterns = [
    path('api/getUnitLogin/', LoginUnitListView.as_view()),
    path('api/login', login.as_view()),
    path('api/getFormwork', TemplateListView.as_view()),
    path('api/getFormworkItem', TemplateItem.as_view()),
    path('api/addFormwork', TemplateCreateView.as_view()),
    path('api/delFormwork', TemplateDeleteView.as_view()),
    path('api/putFormworkItem', TemplateUpdateView.as_view()),

    path('api/getDataInfo', DataListView.as_view()),
    path('api/getDataInfoItem', DataItem.as_view()),
    path('api/addDataInfo', DataCreateView.as_view()),
    path('api/delDataInfo', DataDeleteView.as_view()),
    path('api/putDataInfoItem', DataUpdateView.as_view()),
    path('api/getUnitSearch', UnitSearchView.as_view()),
    path('api/getTemplateSearch', TemplateSearchView.as_view()),
    path('api/getEquipmentSearch', EquipmentSearchView.as_view()),

    path('api/file/upload', UploadFileView.as_view()),
    path('api/getUnit', UnitListView.as_view()),
    path('api/getUnitItem', UnitItem.as_view()),
    path('api/addUnit', UnitCreateView.as_view()),
    path('api/delUnit', UnitDeleteView.as_view()),
    path('api/putUnitItem', UnitUpdateView.as_view()),
]
