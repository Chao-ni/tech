#!/usr/bin/env python
# coding=utf-8

import os
import json
import datetime
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from aliyunsdkcore.auth.credentials import AccessKeyCredential
from dotenv import load_dotenv
from response_handle import process_oss_contents

load_dotenv()

def create_common_request(domain, version, protocolType, method, uri):
    request = CommonRequest()
    request.set_accept_format('json')
    request.set_domain(domain)
    request.set_version(version)
    request.set_protocol_type(protocolType)
    request.set_method(method)
    request.set_uri_pattern(uri)
    request.add_header('Content-Type', 'application/json')
    return request


def init_parameters(url):
    body = dict()
    body['AppKey'] = ''

    # 基本请求参数
    input = dict()
    input['SourceLanguage'] = 'cn'
    input['TaskKey'] = 'task' + datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    input['FileUrl'] = url
    body['Input'] = input

    # AI相关参数，按需设置即可
    parameters = dict()

    parameters['AutoChaptersEnabled'] = True

    # 摘要控制相关 ： 可选，包括： 全文摘要、发言人总结摘要、问答摘要(问答回顾)
    parameters['SummarizationEnabled'] = True
    summarization = dict()
    summarization['Types'] = ['Paragraph', 'Conversational', 'QuestionsAnswering', 'MindMap']
    parameters['Summarization'] = summarization


    body['Parameters'] = parameters
    return body


def poll_tingwu_task(url, interval=10):
    """带自动结果解析的任务轮询函数"""
    import time
    start = time.time()

    # 初始化阿里云客户端
    credentials = AccessKeyCredential(
        os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'],
        os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET']
    )
    client = AcsClient(region_id='cn-beijing', credential=credentials)

    # 创建分析任务
    create_request = create_common_request(
        'tingwu.cn-beijing.aliyuncs.com',
        '2023-09-30',
        'https',
        'PUT',
        '/openapi/tingwu/v2/tasks'
    )
    create_request.add_query_param('type', 'offline')
    create_request.set_content(json.dumps(init_parameters(url)).encode('utf-8'))

    # 获取任务ID
    create_response = json.loads(client.do_action_with_exception(create_request))
    task_id = create_response['Data']['TaskId']
    print(f"📡 任务已创建 | ID: {task_id}")

    # 轮询状态
    while True:
        # 构建状态查询请求
        status_request = create_common_request(
            'tingwu.cn-beijing.aliyuncs.com',
            '2023-09-30',
            'https',
            'GET',
            f'/openapi/tingwu/v2/tasks/{task_id}'
        )

        # 获取最新状态
        status_response = json.loads(client.do_action_with_exception(status_request))
        task_status = status_response['Data']['TaskStatus']

        # 状态处理
        if task_status == 'COMPLETED':
            print(f"✅ 任务完成 | 总耗时: {time.time() - start:.1f}s")
            oss_links = status_response['Data']['Result']
            return process_oss_contents(oss_links)  # 关键集成点

        elif task_status == 'FAILED':
            print(f"❌ 任务失败 | 错误信息: {status_response.get('Message', '未知错误')}")
            return {'error': status_response}

        elif task_status == 'ONGOING':  # ONGOING及其他状态
            print(f"⏳ 任务处理中 | 已耗时: {time.time() - start:.1f}s")
            time.sleep(interval)
        else:
            print(f"❌ 任务无效")
            return {'error': status_response}

















