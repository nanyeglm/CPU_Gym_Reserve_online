# CPU_Gym_Reserve

## 项目目录结构
```
project/
├── app.py
├── config.py
├── requirements.txt
├── run.py
├── logs/
│   └── app.log
├── data/
│   ├── app.db
├── yourapplication/
│   ├── __init__.py
│   ├── models.py
│   ├── views.py
│   ├── utils.py
│   ├── forms.py
│   └── templates/
│       ├── base.html
│       ├── index.html
│       ├── orders.html
│       └── result.html
│   └── static/
│       └── css/
│           └── style.cs
```

## 项目介绍

本程序用于新版CPU体育馆预约API程序,基于FLASK开发,实现网页端申请提交及订单查询功能

### 项目特色

1. 基于正则表达式,自动提取提取 yyp_pass,构建请求数据

2. 基于FAKER模块,实现姓名及电话号码随机生成

3. 在一堆预约订单中,找出预约成功的订单及订单详情,引入SQLite数据库,存储订单数据,实现网页端筛选显示.

4. orders.html页面筛选显示功能,用户填写完表单,点击"提交预约"之后,把提交的订单详情保存到一个新的数据库

### 运行项目

1. 安装依赖包
```
Flask
Flask-WTF
Flask-SQLAlchemy
Flask-Migrate
aiohttp
Faker
beautifulsoup4
WTForms
```
2. 运行主程序```run.py```,```config.py```中的参数可自定义
3. 访问```127.0.0.1:18888```,可自行定义端口
4. 填写表单,提交预约
5. 点击```查看订单```可查看系统中当前存在预约成功的订单