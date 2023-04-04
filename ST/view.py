# -*- coding: utf-8 -*-
"""
@author: user
@project: ST
@file: view.py
@time: 2023/3/30 11:30
@description: 
"""
from django.views import View
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpRequest
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.core.files.storage import default_storage

import json, jwt

from ST.models import User, Template,File
from .tools import create_uuid, return_msg, create_return_json


def check_token(view_func):
    def wrapped(request, *args, **kwargs):
        # 获取前端传过来的token
        response_json = create_return_json()
        token = request.headers.get('AUTHORIZATION', '').split(' ')
        if len(token) > 1:
            token = token[1]
        else:
            return JsonResponse({'error': 'Token error'}, status=401)
        try:
            # 解码token
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])

            # 根据payload中的user_id进行用户认证
            user_id = payload['user_id']
            user = User.objects.get(id=user_id)

            # 将user添加到请求中，方便视图函数中使用
            request.user = user

            return view_func(request, *args, **kwargs)

        except jwt.ExpiredSignatureError:
            # token过期
            response_json['code'], response_json['msg'] = return_msg.S401, return_msg.token_expired
            return JsonResponse(response_json, status=401)

        except jwt.InvalidSignatureError:
            # token无效
            response_json['code'], response_json['msg'] = return_msg.S401, return_msg.token_invalid
            return JsonResponse(response_json, status=401)

        except User.DoesNotExist:
            # 用户不存在
            response_json['code'], response_json['msg'] = return_msg.S401, return_msg.no_user
            return JsonResponse(response_json, status=401)

    return wrapped


# 获取所有模板列表接口
@method_decorator(csrf_exempt, name='dispatch')
# @method_decorator(check_token, name='dispatch')
class TemplateListView(ListView):
    model = Template

    def post(self, request: HttpRequest, *args, **kwargs):

        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            # 获取分页参数
            page_size = j.get('page_size')
            page_index = j.get('page_index')
            # 创建分页器
            queryset = Template.objects.all().values('id', 'name', 'template', 'user__name').order_by('id')
            paginator = Paginator(queryset, page_size)

            # 获取指定页的商品
            page = paginator.get_page(page_index)
            template_list = [{'id': it.get('id'), 'name': it.get('name'), 'formwork': it.get('template'),
                              'user_name': it.get('user__name')} for it in
                             page] if page is not None else None

            # 构造返回数据
            response_json['data'] = {'records': template_list, 'title': None,
                                     'total': paginator.count}
        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.params_error

        return JsonResponse(response_json)


# 获取单个模板信息
@method_decorator(csrf_exempt, name='dispatch')
class TemplateItem(DetailView):
    model = Template

    def post(self, request, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            template = get_object_or_404(self.model, id=j.get('id'))

            # 构造返回数据
            response_json['data'] = {'id': template.id, 'name': template.name, 'formwork': template.template}
        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.row_none
        return JsonResponse(response_json)


# 添加一个模板列表接口
@method_decorator(csrf_exempt, name='dispatch')
class TemplateCreateView(CreateView):
    model = Template

    def post(self, request: HttpRequest, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            name = j.get('name')
            formwork = j.get('formwork')
            file_id =j.get('file_id')
            id = create_uuid()
            template = self.model(name=name, template=formwork, id=id,file_id=file_id)
            template.save()
            response_json['data'] = {'id': template.id, 'name': template.name, 'formwork': template.template}
        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.fail_insert
        return JsonResponse(response_json)


# 修改一个模板信息接口
@method_decorator(csrf_exempt, name='dispatch')
class TemplateUpdateView(UpdateView):
    model = Template

    def post(self, request, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            template = get_object_or_404(self.model, id=j.get('id'))
            name = j.get('name')
            tp = j.get('formwork')
            template.name = name
            template.template = tp
            template.save()
            response_json['data'] = {'id': template.id, 'name': template.name, 'formwork': template.template}
        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.fail_update
        return JsonResponse(response_json)


# 删除一个或者多个模板信息接口
@method_decorator(csrf_exempt, name='dispatch')
class TemplateDeleteView(DeleteView):
    model = Template

    def post(self, request, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            ids = j.get('ids')
            re = self.model.objects.filter(id__in=ids).delete()
        except self.model.DoesNotExist:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.fail_delete
        return JsonResponse(response_json)


# 模板视图
class TemplateView(View):
    def get(self, request):
        view = TemplateListView.as_view()
        return view(request)

    def post(self, request):
        view = TemplateCreateView.as_view()
        return view(request)

    def put(self, request, pk):
        view = TemplateUpdateView.as_view()
        return view(request, pk=pk)

    def delete(self, request, pk):
        view = TemplateDeleteView.as_view()
        return view(request, pk=pk)


# 登录
class login(View):

    def post(self, request: HttpRequest):
        response_json = create_return_json()
        if (get_json := json.loads(request.body)) is not None:
            account = str(get_json.get('account', None)).replace(' ', '')
            password = str(get_json.get('password', None)).replace(' ', '')
            user = User.objects.filter(account=account, password=password)
            if user.exists():
                payload = {'user_id': user[0].id}
                token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
                response_json['msg'], response_json['data'] = '登陆成功！', {'token_id': token, 'user_name': user[0].name,
                                                                        'user_id': user[0].id}
            else:
                response_json['msg'], response_json['code'] = '账户或密码错误！', return_msg.S100
        return JsonResponse(response_json)


# 上传接口
class UploadFileView(View):
    def post(self, request, *args, **kwargs):
        response_json = create_return_json()
        file = request.FILES.get('file')
        if file:
            filename = default_storage.save(file.name, file)
            id = create_uuid()
            file = File(id=id,name=filename, path=file_path)
            file.save()
            response_json['data'] = {'id': id, 'file_name': filename}
            return JsonResponse(response_json)
        else:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.no_file
            return JsonResponse(response_json)



