# -*- coding: utf-8 -*-
"""
@author: user
@project: ST
@file: tools
@time: 2023/4/3 8:42
@description: 
"""
import uuid


class MSG:
    S200 = 200  # 成功返回
    S100 = 100  # 失败返回
    S401 = 401  # 验证失败
    succ = '操作成功'
    inner_error = '内部错误，请联系管理员！'
    params_error = '参数错误！'
    row_none = '暂无数据！'
    conflict = '数据冲突'
    token_invalid = '无效的token值'
    token_expired ='token已过期'
    no_user = '用户不存在'
    exist = '已存在该名称的代码！'
    exist_some = '存在相同指标'
    unaccess = '无权限访问'
    timeout = '验证码已过期！'
    verify_failure = '验证码错误！'
    no_file = '无该文件！'
    exist_doing = '有未完成转学申请，请勿重复申请'
    exist_score = '已存在该同学的成绩！'
    exist_records = '已存在该同学当前方案的选课记录！'
    no_access = '无权限修改他人的考试方案'
    password_error = '输入密码错误！'
    not_in_time = '未到选课时间'
    upload_error = '导入失败！'
    none_update = '无效的更新！'
    no_delete = '无法删除已使用方案'
    no_modify_scheme = '选课方案已被使用！'
    fail_insert = '写入数据失败！'
    fail_update = '更新数据失败！'
    fail_delete = '删除数据失败！'


def create_uuid():
    """
    创建一个uuid
    Returns:
        uuid:32位字符串
    """
    return str(uuid.uuid1()).replace('-', '')


return_msg = MSG()


def create_return_json():
    """
    创建一个返回json
    Returns:

    """
    # return json
    return {
        'code': return_msg.S200,
        'msg': return_msg.succ,
        'data': None
    }
def rows_as_dict(cursor):
    """
    查询结果集转字典
    Args:
        cursor:

    Returns:

    """
    col_names = [i[0].lower() for i in cursor.description]
    return [dict(zip(col_names, row)) for row in cursor]
