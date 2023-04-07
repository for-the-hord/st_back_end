# -*- coding: utf-8 -*-
"""
@author: user
@project: ST
@file: view.py
@time: 2023/3/30 11:30
@description: 
"""
import json
import jwt
from datetime import datetime
from collections import defaultdict

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import connection
from django.http import JsonResponse, HttpRequest
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView

from ST.models import User, Template, File
from .tools import create_uuid, return_msg, create_return_json, rows_as_dict


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

    def post(self, request: HttpRequest, *args, **kwargs):

        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            page_size = j.get('page_size')
            page_index = j.get('page_index')
            condition = j.get('condition', None)
            if len(condition) == 0:
                with connection.cursor() as cur:
                    sql = 'select count(*) as count,t.name as formwork_name from template t '
                    cur.execute(sql)
                    rows = rows_as_dict(cur)
                    count = rows[0]['count']
                    sql = f'select t.id,t.name as formwork_name,t.template,t.is_file,t.create_date,t.update_date,' \
                          f'u.name as user_name ' \
                          'from template t ' \
                          'left join user u on u.id=t.user_id ' \
                          'order by t.id limit :limite offset :offset'
                    params = {'limite': page_size, 'offset': (page_index - 1) * page_size}
                    cur.execute(sql, params)
                    rows = rows_as_dict(cur)
                    template_list = [
                        {'id': it.get('id'), 'name': it.get('formwork_name'), 'formwork': it.get('template'),
                         'user_name': it.get('user_name'), 'is_file': it.get('is_fle'),
                         'create_date': datetime.fromtimestamp(it.get('create_date')).strftime(
                             '%Y-%m-%d %H:%M:%S'),
                         'update_date': datetime.fromtimestamp(it.get('update_date')).strftime(
                             '%Y-%m-%d %H:%M:%S')} for it in
                        rows] if len(rows) != 0 else None

                    # 构造返回数据
                    response_json['data'] = {'records': template_list, 'title': None,
                                             'total': count}
            else:
                where_clause = " AND ".join([f"{key} LIKE %s" for key in condition.keys()])
                where_values = ["%" + value + "%" for value in condition.values()]
                with connection.cursor() as cur:
                    params = where_values
                    sql = f'select count(*) as count,t.name as formwork_name from template t WHERE {where_clause}'
                    cur.execute(sql, params)
                    rows = rows_as_dict(cur)
                    count = rows[0]['count']
                    sql = 'select t.id,t.name as formwork_name,t.template,t.is_file,t.equipment_name,' \
                          't.create_date,t.update_date,' \
                          'u.name as user_name ' \
                          'from template t left join user u on u.id=t.user_id ' \
                          f'where {where_clause} ' \
                          'order by t.id limit %s offset %s'
                    params = where_values + [page_size, (page_index - 1) * page_size]
                    cur.execute(sql, params)
                    rows = rows_as_dict(cur)
                    template_list = [
                        {'id': it.get('id'), 'name': it.get('formwork_name'), 'formwork': it.get('template'),
                         'equipment_name': it.get('equipment_name'),
                         'user_name': it.get('user_name'), 'is_file': it.get('is_fle'),
                         'create_date': datetime.fromtimestamp(it.get('create_date')).strftime(
                             '%Y-%m-%d %H:%M:%S'),
                         'update_date': datetime.fromtimestamp(it.get('update_date')).strftime(
                             '%Y-%m-%d %H:%M:%S')} for it in
                        rows] if len(rows) != 0 else None

                    # 构造返回数据
                    response_json['data'] = {'records': template_list, 'title': None,
                                             'total': count}

        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.params_error

        return JsonResponse(response_json)


# 获取单个模板信息
@method_decorator(csrf_exempt, name='dispatch')
class TemplateItem(DetailView):

    def post(self, request, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            with connection.cursor() as cur:
                sql = 'select t.id,t.name,t.template,t.is_file,t.equipment_name,' \
                      't.create_date as create_date,' \
                      't.update_date as update_date,' \
                      'u.name as user_name ' \
                      'from template t left join user u on u.id=t.user_id where t.id=%s'
                params = [j.get('id')]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                # 构造返回数据
                if len(rows) == 0:
                    response_json['code'], response_json['msg'] = return_msg.S100, return_msg.row_none
                else:
                    response_json['data'] = {'id': rows[0].get('id'), 'name': rows[0].get('name'),
                                             'user_name': rows[0].get('user_name'),
                                             'is_file': rows[0].get('is_file'),
                                             'formwork': rows[0].get('template'),
                                             'create_date': datetime.fromtimestamp(rows[0].get('create_date')).strftime(
                                                 '%Y-%m-%d %H:%M:%S'),
                                             'update_date': datetime.fromtimestamp(rows[0].get('update_date')).strftime(
                                                 '%Y-%m-%d %H:%M:%S')
                                             }
        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.row_none
        return JsonResponse(response_json)


# 添加一个模板列表接口
@method_decorator(csrf_exempt, name='dispatch')
class TemplateCreateView(CreateView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            name = j.get('name')
            formwork = j.get('formwork')
            is_file = j.get('is_file')
            equipment_name = j.get('equipment_name')
            id = create_uuid()
            with connection.cursor() as cur:
                create_date = datetime.now().timestamp()
                sql = 'insert into template (id,name,template,is_file,create_date,equipment_name) ' \
                      'values(%s,%s,%s,%s,%s,%s)'
                params = [id, name, json.dumps(formwork), is_file, create_date,
                          equipment_name]
                cur.execute(sql, params)
                connection.commit()
            response_json['data'] = {'id': id, 'name': name, 'formwork': formwork, 'is_file': is_file,
                                     'create_date': datetime.fromtimestamp(create_date).strftime('%Y-%m-%d %H:%M:%S'),
                                     'equipment_name': equipment_name}
        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.fail_insert
        return JsonResponse(response_json)


# 修改一个模板信息接口
@method_decorator(csrf_exempt, name='dispatch')
class TemplateUpdateView(UpdateView):
    def post(self, request, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            id = j.get('id')
            name = j.get('name')
            formwork = j.get('formwork')
            is_file = j.get('is_file')
            equipment_name = j.get('equipment_name')
            with connection.cursor() as cur:
                update_date = datetime.now().timestamp()
                sql = 'update template set name=%s,template=%s,is_file=%s,equipment_name=%s,update_date=%s ' \
                      'where id=%s)'
                params = [name, json.dumps(formwork), is_file, equipment_name, update_date, id]
                cur.execute(sql, params)
                cur.commit()
            response_json['data'] = {'id': id, 'name': name, 'formwork': formwork, 'is_file': is_file,
                                     'update_date': datetime.fromtimestamp(update_date).strftime('%Y-%m-%d %H:%M:%S'), }
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
            with connection.cursor() as cur:
                sql = 'delete from template  where id=%s'
                params = [[it] for it in ids]
                cur.executemany(sql, params)
                connection.commit()
        except self.model.DoesNotExist:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.fail_delete
        return JsonResponse(response_json)


# 登录
class login(View):

    def post(self, request: HttpRequest):
        response_json = create_return_json()
        if (get_json := json.loads(request.body)) is not None:
            account = str(get_json.get('account', None)).replace(' ', '')
            password = str(get_json.get('password', None)).replace(' ', '')
            with connection.cursor() as cur:
                sql = 'select u.id,n.id as unit_id,n.name as unit_name,u.name  ' \
                      'from user u left join unit n on u.unit_id=n.id ' \
                      'where u.account= %s and u.password=%s'
                params = [account, password]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
            if len(rows) != 0:
                user = rows[0]
                payload = {'user_id': user.get('id')}
                token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
                response_json['msg'], response_json['data'] = '登陆成功！', {'token_id': token,
                                                                        'user_name': user.get('name'),
                                                                        'user_id': user.get('id'),
                                                                        'unit_id': user.get('unit_id'),
                                                                        'unit_name': user.get('unit_name')}
            else:
                response_json['msg'], response_json['code'] = '账户或密码错误！', return_msg.S100
        return JsonResponse(response_json)


# 获取单位列表
class LoginUnitListView(View):

    def post(self, request: HttpRequest):
        response_json = create_return_json()
        with connection.cursor() as cur:
            sql = 'select n.id,n.name from  unit n '
            cur.execute(sql)
            rows = rows_as_dict(cur)
            response_json['data'] = rows
        return JsonResponse(response_json)


# 上传接口
class UploadFileView(View):
    def post(self, request, *args, **kwargs):
        response_json = create_return_json()
        file = request.FILES.get('file')
        if file:
            filename = default_storage.save(file.name, file)
            id = create_uuid()
            file = File(id=id, name=filename, path=file_path)
            file.save()
            response_json['data'] = {'id': id, 'file_name': filename}
            return JsonResponse(response_json)
        else:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.no_file
            return JsonResponse(response_json)


# 获取所有数据列表接口
@method_decorator(csrf_exempt, name='dispatch')
# @method_decorator(check_token, name='dispatch')
class DataListView(ListView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            page_size = j.get('page_size')
            page_index = j.get('page_index')
            with connection.cursor() as cur:
                sql = 'select count(*) as count from tp_data'
                cur.execute(sql)
                rows = rows_as_dict(cur)
                count = rows[0]['count']
                sql = 'select d.id,d.name,' \
                      't.name as template_name,t.template,t.is_file,' \
                      'u.name as user_name,' \
                      'n.name as unit_name ' \
                      'from tp_data d ' \
                      'left join template t on t.id=d.template_id ' \
                      'left join user u on u.id=d.user_id ' \
                      'left join unit n on n.id=d.unit_id ' \
                      'order by t.id ' \
                      'limit %s offset %s'
                params = [page_size, (page_index - 1) * page_size]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                data_list = [{'id': it.get('id'), 'name': it.get('name'), 'formwork_name': it.get('template_name'),
                              'user_name': it.get('user_name'), 'is_file': it.get('is_fle'),
                              'unit_name': it.get('unit_name')} for it in
                             rows] if len(rows) != 0 else None

                # 构造返回数据
                response_json['data'] = {'records': data_list, 'title': None,
                                         'total': count}
        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.params_error

        return JsonResponse(response_json)


# 获取单个数据信息
@method_decorator(csrf_exempt, name='dispatch')
class DataItem(DetailView):
    def post(self, request, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            with connection.cursor() as cur:
                sql = 'select d.id,d.name,d.data,d.files,d.create_date,d.update_date,' \
                      't.is_file,t.name as template_name,' \
                      'n.name as unit_name,' \
                      'u.name as user_name ' \
                      'from tp_data d ' \
                      'left join template t on d.template_id=t.id ' \
                      'left join unit n on n.id=d.unit_id ' \
                      'left join user u on u.id=d.user_id ' \
                      'where d.id=%s'
                params = [j.get('id')]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                # 构造返回数据
                if len(rows) == 0:
                    response_json['code'], response_json['msg'] = return_msg.S100, return_msg.row_none
                else:
                    response_json['data'] = {'id': rows[0].get('id'), 'name': rows[0].get('name'),
                                             'formwork_name': rows[0].get('template_name'),
                                             'is_file': rows[0].get('is_file'),
                                             'data_info': rows[0].get('data'),
                                             'files': json.loads(rows[0].get('files')),
                                             'unit_name': rows[0].get('unit_name'),
                                             'user_name': rows[0].get('user_name'),
                                             'create_date': rows[0].get('create_date'),
                                             'update_date': rows[0].get('update_date')
                                             }
        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.row_none
        return JsonResponse(response_json)


# 添加一个数据列表接口
@method_decorator(csrf_exempt, name='dispatch')
class DataCreateView(CreateView):

    def post(self, request: HttpRequest, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            name = j.get('name')
            formwork_id = j.get('formwork_id')
            data_info = j.get('data_info')
            files = j.get('files')
            id = create_uuid()
            with connection.cursor() as cur:
                sql = 'insert into tp_data (id,name,tp_id,data,files) values(%s,%s,%s,%s,%s)'
                params = [id, name, formwork_id, json.dumps(data_info), json.dumps(files)]
                cur.execute(sql, params)
                connection.commit()
            response_json['data'] = {'id': id, 'name': name, 'data_info': data_info, 'files': files}
        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.fail_insert
        return JsonResponse(response_json)


# 修改一个数据信息接口
@method_decorator(csrf_exempt, name='dispatch')
class DataUpdateView(UpdateView):

    def post(self, request, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            id = j.get('id')
            name = j.get('name')
            formwork = j.get('formwork')
            is_file = j.get('is_file')
            with connection.cursor() as cur:
                sql = 'update template set id=%s,name=%s,template=%s,is_file=%s where id=%s)'
                params = [name, json.dumps(formwork), is_file, id]
                cur.execute(sql, params)
                cur.commit()
            response_json['data'] = {'id': id, 'name': name, 'formwork': formwork, 'is_file': is_file}
        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.fail_update
        return JsonResponse(response_json)


# 删除一个或者多个数据信息接口
@method_decorator(csrf_exempt, name='dispatch')
class DataDeleteView(DeleteView):

    def post(self, request, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            ids = j.get('ids')
            with connection.cursor() as cur:
                sql = 'delete from tp_data  where id=%s'
                params = [[it] for it in ids]
                cur.executemany(sql, params)
                connection.commit()
        except self.model.DoesNotExist:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.fail_delete
        return JsonResponse(response_json)


# 获取所有数据列表接口
@method_decorator(csrf_exempt, name='dispatch')
# @method_decorator(check_token, name='dispatch')
class UnitListView(ListView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            page_size = j.get('page_size')
            page_index = j.get('page_index')
            condition = j.get('condition')
            if len(condition) == 0:
                with connection.cursor() as cur:
                    sql = 'select count(*) as count from unit'
                    cur.execute(sql)
                    rows = rows_as_dict(cur)
                    count = rows[0]['count']
                    sql = 'select n.id, n.name,' \
                          't.id as template_id,t.name as template_name ' \
                          'from unit n ' \
                          'left join unit_template ut on n.id=ut.unit_id ' \
                          'left join template t on ut.template_id=t.id ' \
                          'order by n.id ' \
                          'limit %s offset %s'
                    params = [page_size, (page_index - 1) * page_size]
                    cur.execute(sql, params)
                    rows = rows_as_dict(cur)
                    data_list = [{'id': it.get('id'), 'name': it.get('name'),
                                  'formwork_id': it.get('template_id'), 'formwork_name': it.get('template_name')
                                  } for it in
                                 rows] if len(rows) != 0 else None

            else:
                where_clause = " AND ".join([f"{key} LIKE %s" for key in condition.keys()])
                where_values = ["%" + value + "%" for value in condition.values()]
                with connection.cursor() as cur:
                    params = where_values
                    sql = f'select count(*) as count,n.name as unit_name from unit n WHERE {where_clause}'
                    cur.execute(sql, params)
                    rows = rows_as_dict(cur)
                    count = rows[0]['count']
                    sql = 'select n.id, n.name,' \
                          't.id as template_id,t.name as template_name ' \
                          'from unit n ' \
                          'left join unit_template ut on n.id=ut.unit_id ' \
                          'left join template t on ut.template_id=t.id  ' \
                          f'where {where_clause} ' \
                          'order by t.id limit %s offset %s'
                    params = where_values + [page_size, (page_index - 1) * page_size]
                    cur.execute(sql, params)
                    rows = rows_as_dict(cur)
                    data_list = [
                        {'id': it.get('id'), 'name': it.get('name'),
                         'formwork_id': it.get('template_id'), 'formwork_name': it.get('template_name')
                         } for it in
                        rows] if len(rows) != 0 else None

            # 使用 defaultdict 创建新的数据结构
            records = defaultdict(lambda: {"id": None, "name": None, "formwork_list": []})
            for record in data_list:
                # 按照 id 分组，每个分组都是一个字典
                group = records[record["id"]]
                group["id"] = record["id"]
                group["name"] = record["name"]
                # 如果 formwork_id 和 formwork_name 不为 None，则加入到 formwork_list 中
                if record["formwork_id"] is not None and record["formwork_name"] is not None:
                    group["formwork_list"].append(
                        {"formwork_id": record["formwork_id"], "formwork_name": record["formwork_name"]})

            # 将字典转换为列表
            records = list(records.values())
            # 构造返回数据
            response_json['data'] = {'records': records, 'title': None,
                                     'total': count}
        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.params_error

        return JsonResponse(response_json)


# 获取单个数据信息
@method_decorator(csrf_exempt, name='dispatch')
class UnitItem(DetailView):
    def post(self, request, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            with connection.cursor() as cur:
                sql = 'select d.id,d.name,d.data,d.files,d.create_date,d.update_date,' \
                      't.is_file,t.name as template_name,' \
                      'n.name as unit_name,' \
                      'u.name as user_name ' \
                      'from tp_data d ' \
                      'left join template t on d.template_id=t.id ' \
                      'left join unit n on n.id=d.unit_id ' \
                      'left join user u on u.id=d.user_id ' \
                      'where d.id=%s'
                params = [j.get('id')]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                # 构造返回数据
                if len(rows) == 0:
                    response_json['code'], response_json['msg'] = return_msg.S100, return_msg.row_none
                else:
                    response_json['data'] = {'id': rows[0].get('id'), 'name': rows[0].get('name'),
                                             'formwork_name': rows[0].get('template_name'),
                                             'is_file': rows[0].get('is_file'),
                                             'data_info': rows[0].get('data'),
                                             'files': json.loads(rows[0].get('files')),
                                             'unit_name': rows[0].get('unit_name'),
                                             'user_name': rows[0].get('user_name'),
                                             'create_date': rows[0].get('create_date'),
                                             'update_date': rows[0].get('update_date')
                                             }
        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.row_none
        return JsonResponse(response_json)


# 添加一个单位接口
@method_decorator(csrf_exempt, name='dispatch')
class UnitCreateView(CreateView):

    def post(self, request: HttpRequest, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            name = j.get('name')
            id = create_uuid()
            with connection.cursor() as cur:
                sql = 'insert into unit (id,name) values(%s,%s)'
                params = [id, name]
                cur.execute(sql, params)
                connection.commit()
                response_json['data'] = {'id': id}
        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.fail_insert
        return JsonResponse(response_json)


# 修改一个数据信息接口
@method_decorator(csrf_exempt, name='dispatch')
class UnitUpdateView(UpdateView):

    def post(self, request, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            name = j.get('name')
            id = j.get('id')
            template_ids = j.get('template_ids')
            with connection.cursor() as cur:
                sql = 'update unit set name=%s where id=%s'
                params = [name, id]
                cur.execute(sql, params)
                sql = 'delete from unit_template  where unit_id=%s'
                params = [id]
                cur.execute(sql, params)
                sql = 'insert into unit_template (unit_id,template_id) values (%s,%s)'
                params = [[id, it] for it in template_ids]
                cur.executemany(sql, params)
                connection.commit()

        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.fail_update
        return JsonResponse(response_json)


# 删除一个或者多个数据信息接口
@method_decorator(csrf_exempt, name='dispatch')
class UnitDeleteView(DeleteView):

    def post(self, request, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            ids = j.get('ids')
            with connection.cursor() as cur:
                sql = 'delete from unit  where id=%s'
                params = [[it] for it in ids]
                cur.executemany(sql, params)
                sql = 'delete from unit_template  where unit_id=%s'
                cur.executemany(sql, params)
                connection.commit()
        except self.model.DoesNotExist:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.fail_delete
        return JsonResponse(response_json)
