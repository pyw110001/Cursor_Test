import gradio as gr
import base64
import hashlib
import hmac
import json
import os
import time
import requests
import urllib.parse

lfasr_host = 'https://raasr.xfyun.cn/v2/api'
api_upload = '/upload'
api_get_result = '/getResult'

# 请替换为您的 appid 和 secret_key
APPID = "718a66e3"
SECRET_KEY = "772614c18b6e7d1e1142dfded09a4014"

class RequestApi(object):
    def __init__(self, appid, secret_key, upload_file_path):
        self.appid = appid
        self.secret_key = secret_key
        self.upload_file_path = upload_file_path
        self.ts = str(int(time.time()))
        self.signa = self.get_signa()

    def get_signa(self):
        appid = self.appid
        secret_key = self.secret_key
        m2 = hashlib.md5()
        m2.update((appid + self.ts).encode('utf-8'))
        md5 = m2.hexdigest()
        md5 = bytes(md5, encoding='utf-8')
        signa = hmac.new(secret_key.encode('utf-8'), md5, hashlib.sha1).digest()
        signa = base64.b64encode(signa)
        signa = str(signa, 'utf-8')
        return signa

    def upload(self):
        upload_file_path = self.upload_file_path
        file_len = os.path.getsize(upload_file_path)
        file_name = os.path.basename(upload_file_path)

        param_dict = {}
        param_dict['appId'] = self.appid
        param_dict['signa'] = self.signa
        param_dict['ts'] = self.ts
        param_dict["fileSize"] = file_len
        param_dict["fileName"] = file_name
        param_dict["duration"] = "200"
        print("upload参数：", param_dict)
        data = open(upload_file_path, 'rb').read(file_len)

        response = requests.post(url=lfasr_host + api_upload + "?" + urllib.parse.urlencode(param_dict),
                                 headers={"Content-type": "application/json"}, data=data)
        print("upload_url:", response.request.url)
        result = json.loads(response.text)
        print("upload resp:", result)
        return result

    def get_result(self):
        uploadresp = self.upload()
        print(uploadresp)
        orderId = uploadresp['content']['orderId']
        param_dict = {}
        param_dict['appId'] = self.appid
        param_dict['signa'] = self.signa
        param_dict['ts'] = self.ts
        param_dict['orderId'] = orderId
        param_dict['resultType'] = "transfer,predict"
        print("")
        print("查询部分：")
        print("get result参数：", param_dict)
        status = 3
        # 建议使用回调的方式查询结果，查询接口有请求频率限制
        while status == 3:
            response = requests.post(url=lfasr_host + api_get_result + "?" + urllib.parse.urlencode(param_dict),
                                     headers={"Content-type": "application/json"})
            result = json.loads(response.text)
            status = result['content']['orderInfo']['status']
            print("status=", status)
            if status == 4:
                break
            time.sleep(5)
        return result

def transcribe_audio(audio_file, progress=gr.Progress()):
    log_messages = []
    
    def log(message):
        print(message)
        log_messages.append(message)
    
    log(f"开始处理音频文件: {audio_file}")
    
    api = RequestApi(appid=APPID, secret_key=SECRET_KEY, upload_file_path=audio_file)
    
    progress(0.2, desc="上传音频文件...")
    result = api.get_result()
    
    if result['code'] != '000000':
        error_msg = f"错误: {result['descInfo']}"
        log(error_msg)
        return error_msg, "\n".join(log_messages)
    
    progress(1.0, desc="转写完成!")
    log("转写完成")
    
    # 提取并格式化转写文本
    total_text = ''
    for ele in json.loads(result['content']["orderResult"])['lattice']:
        sentence = ''
        for char_dicts in json.loads(ele['json_1best'])['st']['rt'][0]['ws']:
            sentence += char_dicts['cw'][0]['w']
        total_text += sentence + ' '
    
    return total_text, "\n".join(log_messages)

# 创建Gradio界面
iface = gr.Interface(
    fn=transcribe_audio,
    inputs=gr.Audio(type="filepath", label="上传音频文件", sources=["upload", "microphone"]),
    outputs=[
        gr.Textbox(label="转写结果"),
        gr.Textbox(label="日志", lines=10)
    ],
    title="语音转写",
    description="上传音频文件(mp3/wav/m4a等格式),获取转写文本"
)

if __name__ == "__main__":
    iface.launch()
