import os
import dashscope

# 若使用新加坡地域的模型，请释放下列注释
# dashscope.base_http_api_url = "https://dashscope-intl.aliyuncs.com/api/v1"
messages = [
    {
        "role": "user", 
        "content": "请补全这个斐波那契函数，勿添加其它内容"
    },
    {
        "role": "assistant",
        "content": "def calculate_fibonacci(n):\n    if n <= 1:\n        return n\n    else:\n",
        "partial": True
    }
]
response = dashscope.Generation.call(
    # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    model='qwen3-coder-plus',
    messages=messages,
    result_format='message',  
)

# 手动拼接前缀和模型生成的内容
prefix = "def calculate_fibonacci(n):\n    if n <= 1:\n        return n\n    else:\n"
generated_code = response.output.choices[0].message.content
complete_code = prefix + generated_code

print(complete_code)