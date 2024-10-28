# CPU_Gym_Reserve

## 项目目录结构
```
project/
├── app.py               # Flask 应用程序的入口
├── models.py            # 数据库模型和初始化
├── utils.py             # 工具函数，如异步请求等
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── orders.html
│   └── result.html
├── static/
│   └── css/
│       └── style.css
├── data/
│   ├── orders.db        # 订单数据库
│   └── reservations.db  # 用户提交的预约数据库
├── logs/
│   └── app.log          # 日志文件
```

## 项目介绍

本程序用于新版CPU体育馆预约API程序,基于FLASK开发,实现网页端申请提交及订单查询功能

### 项目特色

1. 基于正则表达式,自动提取提取 yyp_pass,构建请求数据

2. 基于FAKER模块,实现姓名及电话号码随机生成

3. 在一堆预约订单中,找出预约成功的订单及订单详情,引入SQLite数据库,存储订单数据,实现网页端筛选显示.

4. orders.html页面筛选显示功能,用户填写完表单,点击"提交预约"之后,把提交的订单详情保存到一个新的数据库

   

