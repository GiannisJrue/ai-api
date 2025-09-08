from flask import Flask, request, jsonify
from flask_cors import CORS
from celery import Celery
import time
from translations import trs

app = Flask(__name__)
app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379/0',  # Redis作为消息代理
    CELERY_RESULT_BACKEND='redis://localhost:6379/0'  # Redis作为结果后端
)
CORS(app)

def make_celery(app):
    """
    初始化celery
    :param app: Flask实例
    :return: celery实例
    """
    celery = Celery(
        app.import_name,  # 使用Flask应用的名称
        backend=app.config['CELERY_RESULT_BACKEND'],  # 结果后端
        broker=app.config['CELERY_BROKER_URL']  # 消息代理
    )
    # 更新Celery配置，使用Flask应用的配置
    celery.conf.update(app.config)
    return celery

celery = make_celery(app)

#
FUNCTIONS = [
    {
        "id": 1,
        "name": "中译英",
        "endpoint": "/api/translate/zh_to_en",  # 同步接口
        "async_endpoint": "/api/async/translate/zh_to_en"  # 异步接口
    },
    {
        "id": 2,
        "name": "英译中",
        "endpoint": "/api/translate/en_to_zh",
        "async_endpoint": "/api/async/translate/en_to_zh"
    },
    {
        "id": 3,
        "name": "文本总结",
        "endpoint": "/api/summarize",
        "async_endpoint": "/api/async/summarize"
    }
]

@app.route("/api/functions", methods=['GET'])
def get_functions():
    """
    获取所有功能列表接口
    :return: json，包含所有的功能列表
    """
    return jsonify({
        "code":200,
        "message":"success",
        "data":FUNCTIONS
    })

@app.route('/api/translate/zh_to_en', methods=['POST'])
def trans_zh_to_en():
    """
    中译英同步接口
    :return: json和状态码
    """
    try:
        data = request.get_json()
        text = data.get('text', '')
        # 输入是否为空，空就返回400
        if not text:
            return jsonify({
                "code": 400,
                "message": "请输入要进行翻译的中文",
                "data": None
            }), 400

        # 调用大模型进行翻译
        result = trs.translate_en_to_zh(text)

        return jsonify({
            "code": 200,
            "message": "翻译成功",
            "data": {
                "original": text,  # 原文
                "translated": result  # 翻译结果
            }
        })
    except Exception as e:
        return jsonify({
            "code": 500,  # 状态码500表示服务器错误
            "message": f"服务器出错,{e}",
            "data": None
        }), 500

@app.route('/api/translate/en_to_zh', methods=['POST'])
def trans_en_to_zh():
    """
    英译中同步接口
    :return: json和状态码
    """
    try:
        data = request.get_json()
        text = data.get('text', '')

        if not text:
            return jsonify({
                "code": 400,
                "message": "请输入要进行翻译的英文",
                "data": None
            }), 400

        result = trs.translate_en_to_zh(text)

        return jsonify({
            "code": 200,
            "message": "翻译成功",
            "data": {
                "original": text,
                "translated": result
            }
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"服务器出错,{e}",
            "data": None
        }), 500

@app.route('/api/summarize', methods=['POST'])
def summarize():
    """
    文本总结同步接口
    :return: json和状态码
    """
    try:
        data = request.get_json()
        text = text = data.get('text', '')
        if not text:
            return jsonify({
                "code": 400,
                "message": "请输入要总结的文本",
                "data": None
            }), 400


        result = trs.summarize(text)

        return jsonify({
            "code": 200,
            "message": "总结成功",
            "data": {
                "original": text,
                "summarized": result
            }
        })

    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"服务器出错,{e}",
            "data": None
        }), 500

# 下面都是异步接口
@app.route('/api/async/translate/zh_to_en', methods=['POST'])
def async_zh_to_en_translation():
    return create_async_task('zh_to_en', request)

@app.route('/api/async/translate/en_to_zh', methods=['POST'])
def async_en_to_zh_translation():
    return create_async_task('en_to_zh', request)

@app.route('/api/async/summarize', methods=['POST'])
def async_summarize():
    return create_async_task('summarize', request)

@app.route('/api/task/<task_id>', methods=['GET'])
def get_task_result(task_id):
    """
    获取任务执行结果
    :param task_id: celery任务id
    :return: json，包含状态码结果
    """
    try:
        # 通过任务ID获取Celery任务结果
        task_result = celery.AsyncResult(task_id)

        # 根据任务状态返回不同的信息
        if task_result.state == 'PENDING':
            response = {
                "status": "pending",
                "result": None
            }
        elif task_result.state == 'PROCESSING':
            response = {
                "status": "processing",
                "result": None
            }
        elif task_result.state == 'SUCCESS':
            response = {
                "status": "completed",
                "result": task_result.result  # 任务结果
            }
        else:
            response = {
                "status": "failed",
                "result": None,
                "error": str(task_result.info) if task_result.info else "未知错误"
            }

        return jsonify({
            "code": 200,
            "message": "成功",
            "data": response
        })
    except Exception:
        return jsonify({
            "code": 500,
            "message": "获取任务结果失败",
            "data": None
        }), 500

def create_async_task(task_type, request):
    """
    创建异步任务
    :param task_type: 任务的类型
    :param request: 请求对象
    :return: json和状态码
    """
    try:
        data = request.get_json()
        text = data.get('text', '')

        if not text:
            return jsonify({
                "code": 400,
                "message": "请输入文本",
                "data": None
            }), 400

        # 根据任务类型启动不同的Celery任务
        if task_type == 'zh_to_en':
            task = trans_zh_to_en_async.delay(text)
        elif task_type == 'en_to_zh':
            task = trans_en_to_zh_async.delay(text)
        elif task_type == 'summarize':
            task = summarize_async.delay(text)
        else:
            return jsonify({
                "code": 400,
                "message": "未知任务类型",
                "data": None
            }), 400

        # 返回任务信息，包含任务ID供客户端轮询
        return jsonify({
            "code": 200,
            "message": "任务已提交",
            "data": {
                "task_id": task.id,  # Celery生成的任务ID
                "status": "pending",  # 初始状态
                "result_url": f"/api/task/{task.id}"  # 结果查询地址
            }
        })
    except Exception:
        return jsonify({
            "code": 500,
            "message": "服务暂时不可用",
            "data": None
        }), 500

# 以下都为异步任务
@celery.task(bind=True)  # bind=True允许访问任务实例
def trans_zh_to_en_async(self, text):
    # 更新任务状态
    self.update_state(state='PROCESSING')
    # 模拟处理时间
    time.sleep(2)
    return trans_zh_to_en(text)


@celery.task(bind=True)
def trans_en_to_zh_async(self, text):
    self.update_state(state='PROCESSING')
    time.sleep(2)
    return trans_en_to_zh(text)


@celery.task(bind=True)
def summarize_async(self, text):
    self.update_state(state='PROCESSING')
    time.sleep(3)  # 总结任务需要更多时间
    return summarize(text)

# 自定义错误
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "code": 404,
        "message": "接口不存在！",
        "data": None
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "code": 500,
        "message": "服务器出错！",
        "data": None
    }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
