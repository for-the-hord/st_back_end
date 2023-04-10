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
            condition = j.get('condition', {})
            limit_clause = '' if page_size == 0 and page_index == 0 else 'limit %s offset %s'
            where_clause = '' if len(condition) == 0 else 'where ' + " AND ".join(
                [f"{key} LIKE %s" for key in condition.keys()])
            where_values = ["%" + value + "%" for value in condition.values()]
            with connection.cursor() as cur:
                params = where_values
                sql = f'select count(*) as count,t.name as formwork_name from template t {where_clause}'
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                count = rows[0]['count']
                sql = 'select t.id,t.name as formwork_name,t.is_file,' \
                      't.create_date,t.update_date,' \
                      'u.name as user_name ' \
                      'from template t left join user u on u.id=t.user_id ' \
                      f'{where_clause} ' \
                      f'order by t.id {limit_clause}'
                params = where_values + [page_size, (page_index - 1) * page_size] \
                    if limit_clause != '' else where_values
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
            template_list = [
                {'id': it.get('id'), 'name': it.get('formwork_name'),
                 'user_name': it.get('user_name'), 'is_file': it.get('is_fle'),
                 'create_date': datetime.fromtimestamp(it.get('create_date')).strftime(
                     '%Y-%m-%d %H:%M:%S'),
                 'update_date': datetime.fromtimestamp(0 if (re := it.get('update_date')) is None else re).strftime(
                     '%Y-%m-%d %H:%M:%S')} for it in rows]

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
                      'u.name as user_name,' \
                      'te.equipment_id,' \
                      'te.equipment_name ' \
                      'from template t ' \
                      'left join user u on u.id=t.user_id ' \
                      'left join tp_equipment te on t.id = te.template_id ' \
                      'where t.id=%s'
                params = [j.get('id')]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                # 构造返回数据
                if len(rows) == 0:
                    response_json['code'], response_json['msg'] = return_msg.S100, return_msg.row_none
                else:
                    template = [{'id': it.get('id'),
                                 'name': it.get('name'),
                                 'user_name': it.get('user_name'),
                                 'is_file': it.get('is_file'),
                                 'formwork': it.get('template'),
                                 'equipment_id': it.get('equipment_id'),
                                 'equipment_name': it.get('equipment_name'),
                                 'create_date': datetime.fromtimestamp(it.get('create_date')).strftime(
                                     '%Y-%m-%d %H:%M:%S'),
                                 'update_date': datetime.fromtimestamp(it.get('update_date')).strftime(
                                     '%Y-%m-%d %H:%M:%S')
                                 } for it in rows]
                    # 使用 defaultdict 创建新的数据结构
                    records = defaultdict(lambda: {'id': None,
                                                   'name': None,
                                                   'user_name': None,
                                                   'is_file': None,
                                                   'formwork': None,
                                                   'create_date': 0,
                                                   'update_date': 0,
                                                   "equipment_list": []})
                    for record in template:
                        # 按照 id 分组，每个分组都是一个字典
                        group = records[record["id"]]
                        group["id"] = record["id"]
                        group["name"] = record["name"]
                        group["user_name"] = record["user_name"]
                        group["is_file"] = record["is_file"]
                        group["create_date"] = record["create_date"]
                        group["update_date"] = record["update_date"]
                        # 如果 formwork_id 和 formwork_name 不为 None，则加入到 formwork_list 中
                        if record["equipment_id"] is not None and record["equipment_name"] is not None:
                            group["equipment_list"].append(
                                {"equipment_id": record["equipment_id"], "equipment_name": record["equipment_name"]})

                    # 将字典转换为列表
                    records = list(records.values())
                    response_json['data'] = records
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
                sql = 'insert into template (id,name,template,is_file,create_date,update_date) ' \
                      'values(%s,%s,%s,%s,%s,%s)'
                params = [id, name, json.dumps(formwork), is_file, create_date, create_date, ]
                cur.execute(sql, params)
                params = [[id, create_uuid(), it] for it in equipment_name]
                sql = 'insert into tp_equipment (template_id,equipment_id,equipment_name) values (%s,%s,%s)'
                cur.executemany(sql, params)
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
                sql = 'update template set name=%s,template=%s,is_file=%s,update_date=%s ' \
                      'where id=%s'
                params = [name, json.dumps(formwork), is_file, update_date, id]
                cur.execute(sql, params)
                sql = 'delete from tp_equipment where template_id=%s'
                params = [id]
                cur.execute(sql, params)
                params = [[id, create_uuid(), it] for it in equipment_name]
                sql = 'insert into tp_equipment (template_id,equipment_id, equipment_name) values (%s,%s,%s)'
                cur.executemany(sql, params)
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
                sql = 'delete from unit_template where template_id=%s'
                params = [[it] for it in ids]
                cur.executemany(sql, params)
                sql = 'delete from tp_equipment where template_id=%s'
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
                sql = 'select u.id,n.id as unit_id,n.name as unit_name,u.name ,s.sys_title ' \
                      'from user u left join unit n on u.unit_id=n.id ' \
                      'left join sys_info s on 1=1 ' \
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
                                                                        'unit_name': user.get('unit_name'),
                                                                        'sys_title': user.get('sys_title')}
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
            file = File(id=id, name=filename, path='./')
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
            condition = j.get('condition')  # {'unit_id':[],'formwork_id','equipment_id':[],'data_info':''}
            params = []

            def dict_to_query_str(d: dict):
                def convert_key(orginal):
                    if orginal == 'unit_id':
                        k = 'd.unit_id'
                    elif orginal == 'formwork_id':
                        k = 'd.template_id'
                    elif orginal == 'equipment_id':
                        k = 'equipment_id'
                    else:
                        k = None
                    return k

                conditions = []
                for key, value in d.items():
                    if k := convert_key(key):
                        if key == 'data_info':
                            if value:
                                conditions.append("data_info like  %s ")
                                params.append(value)
                        else:
                            if value:  # 如果数组不为空
                                conditions.append(f"{k} IN ({','.join(['%s' for i in range(len(value))])})")
                                params.extend(value)
                return ' and '.join(conditions)
            where_sql = dict_to_query_str(condition)
            where_clause = '' if where_sql =='' else 'where ' + dict_to_query_str(condition)
            with connection.cursor() as cur:
                sql = 'select count(*) as count from tp_data'
                cur.execute(sql)
                rows = rows_as_dict(cur)
                count = rows[0]['count']
                sql = 'select d.id,d.name,d.data as data_info,d.unit_id as unit_id,' \
                      't.id as template_id,t.name as template_name,t.template,t.is_file,' \
                      'u.name as user_name,' \
                      'n.name as unit_name,' \
                      'te.equipment_id ' \
                      'from tp_data d ' \
                      'left join template t on t.id=d.template_id ' \
                      'left join user u on u.id=d.user_id ' \
                      'left join unit n on n.id=d.unit_id ' \
                      'left join tp_equipment te on t.id = te.template_id ' \
                      f'{where_clause} ' \
                      'order by t.id ' \
                      'limit %s offset %s'
                params += [page_size, (page_index - 1) * page_size]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                data_list = [{'id': it.get('id'), 'name': it.get('name'), 'formwork_name': it.get('template_name'),
                              'user_name': it.get('user_name'), 'is_file': it.get('is_fle'),
                              'unit_name': it.get('unit_name')} for it in
                             rows]

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
                sql = 'insert into tp_data (id,name,template_id,data,files) values(%s,%s,%s,%s,%s)'
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
                sql = 'update template set id=%s,name=%s,template=%s,is_file=%s where id=%s'
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


# 拉取单位列表（同登录）
@method_decorator(csrf_exempt, name='dispatch')
class UnitSearchView(DeleteView):

    def post(self, request, *args, **kwargs):
        response_json = create_return_json()

        with connection.cursor() as cur:
            sql = 'select distinct n.id,n.name ' \
                  'from  unit n '
            cur.execute(sql)
            rows = rows_as_dict(cur)
            response_json['data'] = rows
        return JsonResponse(response_json)


# 通过单位获取模板
@method_decorator(csrf_exempt, name='dispatch')
class TemplateSearchView(DeleteView):

    def post(self, request, *args, **kwargs):
        response_json = create_return_json()
        try:
            with connection.cursor() as cur:
                sql = 'select distinct t.id as id,t.name ' \
                      'from template t '
                cur.execute(sql)
                rows = rows_as_dict(cur)
                response_json['data'] = rows
        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.row_none
        return JsonResponse(response_json)


# 获取装备列表
@method_decorator(csrf_exempt, name='dispatch')
class EquipmentSearchView(DeleteView):

    def post(self, request, *args, **kwargs):
        response_json = create_return_json()
        try:
            with connection.cursor() as cur:
                sql = 'select distinct te.equipment_id as id,' \
                      'te.equipment_name as name ' \
                      'from  tp_equipment te '
                cur.execute(sql)
                rows = rows_as_dict(cur)
                response_json['data'] = rows
        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.row_none
        return JsonResponse(response_json)


# 获取所有单位列表接口
@method_decorator(csrf_exempt, name='dispatch')
# @method_decorator(check_token, name='dispatch')
class UnitListView(ListView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            page_size = j.get('page_size')
            page_index = j.get('page_index')
            condition = j.get('condition', {})
            where_clause = '' if len(condition) == 0 else 'where ' + " AND ".join(
                [f"{key} LIKE %s" for key in condition.keys()])
            where_values = ["%" + value + "%" for value in condition.values()]

            with connection.cursor() as cur:
                params = where_values
                sql = f'select count(*) as count,n.name as unit_name from unit n {where_clause}'
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                count = rows[0]['count']
                sql = 'select n.id, n.unit_name,' \
                      't.id as template_id,t.name as template_name ' \
                      f'from (select id,name as unit_name from unit {where_clause} order by id limit %s offset %s) n ' \
                      'left join unit_template ut on n.id=ut.unit_id ' \
                      'left join template t on ut.template_id=t.id '
                params = where_values + [page_size, (page_index - 1) * page_size]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                data_list = [
                    {'id': it.get('id'), 'name': it.get('unit_name'),
                     'formwork_id': it.get('template_id'), 'formwork_name': it.get('template_name')
                     } for it in rows]

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


# 获取单个单位信息
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
            template_ids = j.get('template_ids')
            with connection.cursor() as cur:
                sql = 'insert into unit (id,name) values(%s,%s)'
                params = [id, name]
                cur.execute(sql, params)
                sql = 'insert into unit_template (unit_id,template_id) values (%s,%s)'
                params = [[id, it] for it in template_ids]
                cur.executemany(sql, params)
                connection.commit()
                response_json['data'] = {'id': id}
        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.fail_insert
        return JsonResponse(response_json)


# 修改一个单位接口
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


# 删除一个或者多个单位接口
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


# 修改系统名称接口
@method_decorator(csrf_exempt, name='dispatch')
class SysInfoUpdateView(UpdateView):

    def post(self, request, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            name = j.get('sys_title')
            with connection.cursor() as cur:
                sql = 'update sys_info set sys_title=%s'
                params = [name]
                cur.execute(sql, params)
                connection.commit()
        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.fail_update
        return JsonResponse(response_json)


# 添加一个管理员用户
@method_decorator(csrf_exempt, name='dispatch')
class UserCreateView(CreateView):

    def post(self, request: HttpRequest, *args, **kwargs):
        response_json = create_return_json()
        try:
            j = json.loads(request.body)
            name = j.get('name')
            account = j.get('account')
            password = '123456'
            id = create_uuid()

            with connection.cursor() as cur:
                sql = 'insert into user (id, name, password, unit_id, account) values(%s,%s,%s,%s,%s)'
                params = [id, name, password, None, account]
                cur.execute(sql, params)
                connection.commit()
                response_json['data'] = {'password': '123456'}
        except Exception as e:
            response_json['code'], response_json['msg'] = return_msg.S100, return_msg.fail_insert
        return JsonResponse(response_json)
